import base64
import json

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import Response, StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..auth import get_current_user, resolve_api_token
from ..database import get_db
from ..models import ImageTask, ModelPrice, Token, User, utcnow
from ..services.access import consume, group_models, plan_consume, resolve_group
from ..services.llm import fake_embedding, generate_chat_text, generate_image_png, parse_size, stream_chat_text
from ..services.gateway import configured, request_bytes, request_json, stream_request

router = APIRouter()


class ChatBody(BaseModel):
    model: str
    messages: list[dict]
    stream: bool = False
    max_tokens: int | None = None
    temperature: float | None = None
    group: str = ""
    token_id: int | None = None


class ImageBody(BaseModel):
    model: str = "gpt-image-2"
    prompt: str
    n: int = 1
    size: str = "1024x1024"
    quality: str = "1k"
    token_id: int | None = None


def _model(db: Session, name: str) -> ModelPrice:
    model = db.query(ModelPrice).filter(ModelPrice.model_name == name).first()
    if not model:
        raise HTTPException(status_code=400, detail=f"模型 {name} 不存在")
    return model


def _user_token(db: Session, user: User, token_id: int | None) -> Token | None:
    if not token_id:
        return None
    token = db.query(Token).filter(Token.id == token_id, Token.user_id == user.id).first()
    if not token or token.status != 1:
        raise HTTPException(status_code=400, detail="所选密钥不可用")
    if token.expired_time not in (-1, 0) and token.expired_time < utcnow():
        raise HTTPException(status_code=403, detail="This token has expired")
    return token


def _assert_image_token(user: User, token: Token, model: ModelPrice) -> None:
    groups = [g for g in (model.enable_groups or "").split(",") if g]
    group = token.group or user.group or "default"
    if groups and group not in groups:
        raise HTTPException(status_code=400, detail=f"密钥分组「{group}」无法调用 {model.model_name}，请使用对应生图分组密钥")


def _pick_image_token(db: Session, user: User, model: ModelPrice, token_id: int | None) -> Token:
    if token_id:
        token = _user_token(db, user, token_id)
        if not token:
            raise HTTPException(status_code=400, detail="请选择生图密钥")
        _assert_image_token(user, token, model)
        return token
    groups = [g for g in (model.enable_groups or "").split(",") if g]
    tokens = db.query(Token).filter(Token.user_id == user.id, Token.status == 1).all()
    for t in tokens:
        g = t.group or user.group
        if g in groups:
            return t
    raise HTTPException(status_code=400, detail="当前账号没有对应生图分组的密钥，请先在控制台创建")


async def _chat_core(db: Session, user: User, token: Token | None, body: ChatBody, ip: str):
    model = _model(db, body.model)
    prompt_tokens = max(8, sum(len(str(m.get("content") or "")) // 4 for m in body.messages))
    plan_consume(
        db,
        user=user,
        token=token,
        model=model,
        prompt_tokens=prompt_tokens,
        completion_tokens=max(32, min(body.max_tokens or 256, 512)),
        ip=ip,
        group=body.group,
    )
    group_name = resolve_group(token, user, body.group)
    if configured(db, group_name, body.model):
        upstream = await request_json(db, group_name, body.model, "/chat/completions", {"model": body.model, "messages": body.messages, "stream": False, "temperature": body.temperature, "max_tokens": body.max_tokens})
        text = str(upstream.get("choices", [{}])[0].get("message", {}).get("content") or upstream.get("output_text") or "")
        if not text:
            raise HTTPException(status_code=502, detail="上游未返回有效文本")
    else:
        text = await generate_chat_text(body.model, body.messages)
    completion_tokens = max(8, len(text) // 4)
    quota, request_id = consume(
        db,
        user=user,
        token=token,
        model=model,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        stream=body.stream,
        ip=ip,
        group=body.group,
        path="/v1/chat/completions",
    )
    return text, prompt_tokens, completion_tokens, request_id, quota


@router.post("/v1/chat/completions")
async def chat_completions(body: ChatBody, request: Request, db: Session = Depends(get_db)):
    token, user = _api_pair(request, db)
    ip = request.client.host if request.client else ""
    group = resolve_group(token, user, body.group)
    if body.stream and configured(db, group, body.model):
        # Billing is committed before streaming so abandoned connections cannot bypass quota.
        model = _model(db, body.model)
        prompt_tokens = max(8, sum(len(str(m.get("content") or "")) // 4 for m in body.messages))
        plan_consume(db, user=user, token=token, model=model, prompt_tokens=prompt_tokens, completion_tokens=max(32, min(body.max_tokens or 256, 512)), ip=ip, group=body.group)
        async def passthrough():
            try:
                async for chunk in stream_request(db, group, body.model, "/chat/completions", body.model_dump(exclude_none=True)):
                    yield chunk
            finally:
                consume(db, user=user, token=token, model=model, prompt_tokens=prompt_tokens, completion_tokens=0, stream=True, ip=ip, group=body.group, path="/v1/chat/completions")
        return StreamingResponse(passthrough(), media_type="text/event-stream")
    text, p, c, rid, _quota = await _chat_core(db, user, token, body, ip)
    created = utcnow()
    if body.stream:

        async def event_stream():
            async for chunk in stream_chat_text(text):
                payload = {
                    "id": f"chatcmpl-{rid}",
                    "object": "chat.completion.chunk",
                    "created": created,
                    "model": body.model,
                    "choices": [{"index": 0, "delta": {"content": chunk}, "finish_reason": None}],
                }
                yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
            done = {
                "id": f"chatcmpl-{rid}",
                "object": "chat.completion.chunk",
                "created": created,
                "model": body.model,
                "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}],
                "usage": {"prompt_tokens": p, "completion_tokens": c, "total_tokens": p + c},
            }
            yield f"data: {json.dumps(done, ensure_ascii=False)}\n\n"
            yield "data: [DONE]\n\n"

        return StreamingResponse(event_stream(), media_type="text/event-stream")
    return {
        "id": f"chatcmpl-{rid}",
        "object": "chat.completion",
        "created": created,
        "model": body.model,
        "choices": [{"index": 0, "message": {"role": "assistant", "content": text}, "finish_reason": "stop"}],
        "usage": {"prompt_tokens": p, "completion_tokens": c, "total_tokens": p + c},
    }


@router.post("/api/playground/chat")
async def playground_chat(body: ChatBody, request: Request, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    ip = request.client.host if request.client else ""
    token = _user_token(db, user, body.token_id)
    text, p, c, rid, quota = await _chat_core(db, user, token, body, ip)
    if body.stream:

        async def event_stream():
            async for chunk in stream_chat_text(text):
                yield f"data: {json.dumps({'content': chunk}, ensure_ascii=False)}\n\n"
            yield f"data: {json.dumps({'done': True, 'request_id': rid, 'quota': quota})}\n\n"

        return StreamingResponse(event_stream(), media_type="text/event-stream")
    return {"success": True, "data": {"content": text, "prompt_tokens": p, "completion_tokens": c, "request_id": rid, "quota": quota}}


@router.get("/v1/models")
def list_models(request: Request, db: Session = Depends(get_db)):
    token, user = _api_pair(request, db)
    group = resolve_group(token, user)
    models = group_models(db, group)
    if token and token.models:
        allow = {x.strip() for x in token.models.split(",") if x.strip()}
        models = [m for m in models if m.model_name in allow]
    return {
        "object": "list",
        "data": [{"id": m.model_name, "object": "model", "owned_by": m.vendor, "created": utcnow()} for m in models],
    }


@router.post("/v1/images/generations")
async def images(body: ImageBody, request: Request, db: Session = Depends(get_db)):
    token, user = _api_pair(request, db)
    model = db.query(ModelPrice).filter(ModelPrice.model_name == body.model).first()
    if not model:
        model = _model(db, "gpt-image-2")
    _assert_image_token(user, token, model)
    group = resolve_group(token, user)
    if configured(db, group, body.model):
        prompt_tokens = max(8, len(body.prompt) // 4)
        n = max(1, min(body.n, 4))
        plan_consume(db, user=user, token=token, model=model, prompt_tokens=prompt_tokens, completion_tokens=0, ip=request.client.host if request.client else "", n=n)
        upstream = await request_json(db, group, body.model, "/images/generations", body.model_dump(exclude_none=True))
        consume(db, user=user, token=token, model=model, prompt_tokens=prompt_tokens, completion_tokens=0, stream=False, ip=request.client.host if request.client else "", n=n, path="/v1/images/generations")
        return upstream
    w, h = parse_size(body.size, body.quality if body.quality in ("1k", "2k", "4k") else "1k")
    n = max(1, min(body.n, 4))
    plan_consume(
        db,
        user=user,
        token=token,
        model=model,
        prompt_tokens=max(8, len(body.prompt) // 4),
        completion_tokens=0,
        ip=request.client.host if request.client else "",
        n=n,
    )
    out = []
    for _ in range(n):
        png = generate_image_png(body.prompt, w, h)
        b64 = base64.b64encode(png).decode()
        out.append({"b64_json": b64})
        db.add(ImageTask(user_id=user.id, prompt=body.prompt, size=f"{w}x{h}", quality=body.quality, n=1, image_b64=b64))
    consume(
        db,
        user=user,
        token=token,
        model=model,
        prompt_tokens=max(8, len(body.prompt) // 4),
        completion_tokens=0,
        stream=False,
        ip=request.client.host if request.client else "",
        n=n,
        path="/v1/images/generations",
    )
    return {"created": utcnow(), "data": out}


@router.post("/api/image/generate")
async def image_generate(body: ImageBody, request: Request, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    model = _model(db, body.model)
    token = _pick_image_token(db, user, model, body.token_id)
    w, h = parse_size(body.size, body.quality)
    n = max(1, min(body.n, 4))
    plan_consume(
        db,
        user=user,
        token=token,
        model=model,
        prompt_tokens=max(8, len(body.prompt) // 4),
        completion_tokens=0,
        ip=request.client.host if request.client else "",
        n=n,
    )
    images = []
    for _ in range(n):
        png = generate_image_png(body.prompt, w, h)
        b64 = base64.b64encode(png).decode()
        task = ImageTask(user_id=user.id, prompt=body.prompt, size=f"{w}x{h}", quality=body.quality, n=1, image_b64=b64)
        db.add(task)
        images.append(task)
    consume(
        db,
        user=user,
        token=token,
        model=model,
        prompt_tokens=max(8, len(body.prompt) // 4),
        completion_tokens=0,
        stream=False,
        ip=request.client.host if request.client else "",
        n=n,
        path="/api/image/generate",
    )
    payload = [{"id": t.id, "b64": t.image_b64, "prompt": body.prompt, "size": f"{w}x{h}"} for t in images]
    first = payload[0]
    return {"success": True, "data": {**first, "n": n, "images": payload}}


@router.get("/api/image/tasks")
def image_tasks(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    tasks = db.query(ImageTask).filter(ImageTask.user_id == user.id).order_by(ImageTask.id.desc()).limit(40).all()
    return {
        "success": True,
        "data": [{"id": t.id, "prompt": t.prompt, "size": t.size, "quality": t.quality, "b64": t.image_b64, "created_at": t.created_at} for t in tasks],
    }


class EmbedBody(BaseModel):
    model: str = "text-embedding-3-small"
    input: str | list[str]


def _api_pair(request: Request, db: Session):
    header = request.headers.get("authorization") or request.headers.get("x-api-key")
    return resolve_api_token(header, db)


@router.post("/v1/embeddings")
def embeddings(body: EmbedBody, request: Request, db: Session = Depends(get_db)):
    token, user = _api_pair(request, db)
    texts = body.input if isinstance(body.input, list) else [body.input]
    prompt_tokens = max(8, sum(len(t) // 4 for t in texts))
    model = _model(db, body.model)
    consume(
        db,
        user=user,
        token=token,
        model=model,
        prompt_tokens=prompt_tokens,
        completion_tokens=0,
        stream=False,
        ip=request.client.host if request.client else "",
        path="/v1/embeddings",
    )
    group = resolve_group(token, user)
    if configured(db, group, body.model):
        # Keep accounting in this gateway, but return the provider's real vectors.
        upstream = __import__("asyncio").run(request_json(db, group, body.model, "/embeddings", {"model": body.model, "input": texts}))
        return upstream
    return {
        "object": "list",
        "data": [{"object": "embedding", "index": i, "embedding": fake_embedding(t)} for i, t in enumerate(texts)],
        "model": body.model,
        "usage": {"prompt_tokens": prompt_tokens, "total_tokens": prompt_tokens},
    }


@router.post("/v1/responses")
@router.post("/v1/responses/compact")
async def responses(request: Request, db: Session = Depends(get_db)):
    payload = await request.json()
    model = payload.get("model") or "gpt-5.4-mini"
    messages = payload.get("input") or payload.get("messages") or []
    if isinstance(messages, str):
        messages = [{"role": "user", "content": messages}]
    elif messages and isinstance(messages[0], dict) and "content" in messages[0] and "role" not in messages[0]:
        messages = [{"role": "user", "content": str(m.get("content"))} for m in messages]
    token, user = _api_pair(request, db)
    body = ChatBody(model=model, messages=messages, stream=bool(payload.get("stream")))
    text, p, c, rid, _quota = await _chat_core(
        db, user, token, body, request.client.host if request.client else ""
    )
    response_id = f"resp_{rid}"
    created_at = utcnow()
    if body.stream:
        async def event_stream():
            created = {"type": "response.created", "response": {"id": response_id, "object": "response", "status": "in_progress", "model": model}}
            yield f"event: response.created\ndata: {json.dumps(created, ensure_ascii=False)}\n\n"
            sequence = 0
            async for chunk in stream_chat_text(text):
                event = {"type": "response.output_text.delta", "item_id": f"msg_{rid}", "output_index": 0, "content_index": 0, "delta": chunk, "sequence_number": sequence}
                sequence += 1
                yield f"event: response.output_text.delta\ndata: {json.dumps(event, ensure_ascii=False)}\n\n"
            completed = {"type": "response.completed", "response": _responses_payload(response_id, model, text, p, c, created_at), "sequence_number": sequence}
            yield f"event: response.completed\ndata: {json.dumps(completed, ensure_ascii=False)}\n\n"
        return StreamingResponse(event_stream(), media_type="text/event-stream")
    return _responses_payload(response_id, model, text, p, c, created_at)


def _responses_payload(response_id: str, model: str, text: str, prompt_tokens: int, completion_tokens: int, created_at: int) -> dict:
    return {
        "id": response_id,
        "object": "response",
        "created_at": created_at,
        "status": "completed",
        "model": model,
        "output": [{"id": response_id.replace("resp_", "msg_", 1), "type": "message", "status": "completed", "role": "assistant", "content": [{"type": "output_text", "text": text, "annotations": []}]}],
        "output_text": text,
        "usage": {"input_tokens": prompt_tokens, "output_tokens": completion_tokens, "total_tokens": prompt_tokens + completion_tokens},
    }


@router.post("/v1/messages")
async def anthropic_messages(request: Request, db: Session = Depends(get_db)):
    token, user = _api_pair(request, db)
    payload = await request.json()
    messages = payload.get("messages") or []
    if payload.get("system"):
        messages = [{"role": "system", "content": payload["system"]}] + list(messages)
    body = ChatBody(
        model=payload.get("model") or "claude-sonnet-4-6",
        messages=messages,
        stream=bool(payload.get("stream")),
        max_tokens=payload.get("max_tokens"),
    )
    text, p, c, rid, _quota = await _chat_core(db, user, token, body, request.client.host if request.client else "")
    if body.stream:
        async def event_stream():
            start = {"type": "message_start", "message": {"id": f"msg_{rid}", "type": "message", "role": "assistant", "content": [], "model": body.model, "stop_reason": None, "usage": {"input_tokens": p, "output_tokens": 0}}}
            yield f"event: message_start\ndata: {json.dumps(start, ensure_ascii=False)}\n\n"
            yield 'event: content_block_start\ndata: {"type":"content_block_start","index":0,"content_block":{"type":"text","text":""}}\n\n'
            async for chunk in stream_chat_text(text):
                event = {"type": "content_block_delta", "index": 0, "delta": {"type": "text_delta", "text": chunk}}
                yield f"event: content_block_delta\ndata: {json.dumps(event, ensure_ascii=False)}\n\n"
            yield 'event: content_block_stop\ndata: {"type":"content_block_stop","index":0}\n\n'
            delta = {"type": "message_delta", "delta": {"stop_reason": "end_turn", "stop_sequence": None}, "usage": {"output_tokens": c}}
            yield f"event: message_delta\ndata: {json.dumps(delta, ensure_ascii=False)}\n\n"
            yield 'event: message_stop\ndata: {"type":"message_stop"}\n\n'
        return StreamingResponse(event_stream(), media_type="text/event-stream")
    return {
        "id": f"msg_{rid}",
        "type": "message",
        "role": "assistant",
        "content": [{"type": "text", "text": text}],
        "model": body.model,
        "stop_reason": "end_turn",
        "usage": {"input_tokens": p, "output_tokens": c},
    }


@router.post("/v1/images/edits")
@router.post("/v1/images/variations")
async def images_extra(request: Request, db: Session = Depends(get_db)):
    form = await request.form()
    prompt = str(form.get("prompt") or "variation")
    model_name = str(form.get("model") or "gpt-image-2")
    size = str(form.get("size") or "1024x1024")
    n = int(form.get("n") or 1)
    body = ImageBody(model=model_name, prompt=prompt, n=n, size=size)
    return await images(body, request, db)


@router.post("/v1/audio/speech")
async def audio_speech(request: Request, db: Session = Depends(get_db)):
    token, user = _api_pair(request, db)
    payload = await request.json()
    model = _model(db, payload.get("model") or "tts-1")
    text = str(payload.get("input") or "")
    group = resolve_group(token, user)
    if configured(db, group, model.model_name):
        content, content_type = await request_bytes(db, group, model.model_name, "/audio/speech", payload)
        return Response(content=content, media_type=content_type)
    consume(
        db,
        user=user,
        token=token,
        model=model,
        prompt_tokens=max(8, len(text) // 4),
        completion_tokens=0,
        stream=False,
        ip=request.client.host if request.client else "",
        path="/v1/audio/speech",
    )
    return Response(content=b"ID3" + text.encode("utf-8")[:800], media_type="audio/mpeg")


@router.post("/v1/audio/transcriptions")
@router.post("/v1/audio/translations")
async def audio_text(request: Request, db: Session = Depends(get_db)):
    token, user = _api_pair(request, db)
    form = await request.form()
    model = _model(db, str(form.get("model") or "whisper-1"))
    group = resolve_group(token, user)
    if configured(db, group, model.model_name):
        # Multipart forwarding is intentionally handled separately from JSON routes.
        upload = form.get("file")
        files = {"file": (getattr(upload, "filename", "audio.bin"), await upload.read(), getattr(upload, "content_type", "application/octet-stream"))} if upload else {}
        data = {k: str(v) for k, v in form.multi_items() if k != "file"}
        rows = __import__("app.services.gateway", fromlist=["candidates"]).candidates(db, group, model.model_name)
        if rows:
            import httpx
            async with httpx.AsyncClient(timeout=90) as client:
                response = await client.post(f"{rows[0].base_url.rstrip('/')}{request.url.path}", headers={"Authorization": f"Bearer {rows[0].api_key}"}, data=data, files=files)
                response.raise_for_status()
                return response.json()
    consume(
        db,
        user=user,
        token=token,
        model=model,
        prompt_tokens=16,
        completion_tokens=8,
        stream=False,
        ip=request.client.host if request.client else "",
        path=request.url.path,
    )
    return {"text": "ThinkAI local transcription demo."}


class RerankBody(BaseModel):
    model: str = "rerank-multilingual-v3.0"
    query: str
    documents: list[str]


@router.post("/v1/rerank")
def rerank(body: RerankBody, request: Request, db: Session = Depends(get_db)):
    token, user = _api_pair(request, db)
    model = _model(db, body.model)
    consume(
        db,
        user=user,
        token=token,
        model=model,
        prompt_tokens=max(8, len(body.query) // 4),
        completion_tokens=0,
        stream=False,
        ip=request.client.host if request.client else "",
        path="/v1/rerank",
    )
    ranked = [
        {"index": i, "relevance_score": round(1 - i / max(len(body.documents), 1), 4)}
        for i in range(len(body.documents))
    ]
    return {"model": body.model, "results": ranked}


@router.get("/v1beta/models")
def gemini_models(request: Request, db: Session = Depends(get_db)):
    token, user = _api_pair(request, db)
    group = resolve_group(token, user)
    models = group_models(db, group)
    return {
        "models": [
            {
                "name": f"models/{m.model_name}",
                "version": "v1beta",
                "displayName": m.model_name,
                "supportedGenerationMethods": ["generateContent"],
            }
            for m in models
        ]
    }
