import secrets

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def err_msg(r):
    body = r.json()
    if isinstance(body.get("error"), dict):
        return body["error"].get("message") or ""
    return body.get("message") or ""


def _login(username="FengYu", password="Feng1010"):
    r = client.post("/api/user/login", json={"username": username, "password": password})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["success"]
    return body["data"]["access_token"], body["data"]["user"]


def test_login_reject_wrong_password():
    r = client.post("/api/user/login", json={"username": "FengYu", "password": "bad"})
    assert r.status_code == 401
    assert r.json()["success"] is False


def test_token_group_and_quota_consume():
    jwt, user_before = _login()
    headers = {"Authorization": f"Bearer {jwt}"}
    r = client.post(
        "/api/token/",
        headers=headers,
        json={"name": "biz-codex", "group": "Codex（推荐）", "unlimited_quota": True},
    )
    assert r.json()["success"]
    raw = r.json()["data"]["raw_key"]
    r = client.post(
        "/v1/chat/completions",
        headers={"Authorization": f"Bearer {raw}"},
        json={"model": "gpt-5.4-mini", "messages": [{"role": "user", "content": "hi"}]},
    )
    assert r.status_code == 200, r.text
    assert r.json()["choices"][0]["message"]["content"]
    after = client.get("/api/user/self", headers=headers).json()["data"]
    assert after["used_quota"] >= user_before["used_quota"]
    assert after["quota"] < user_before["quota"]


def test_model_not_in_group_rejected():
    jwt, _ = _login()
    r = client.post(
        "/api/token/",
        headers={"Authorization": f"Bearer {jwt}"},
        json={"name": "biz-ds", "group": "Deepseek-官方", "unlimited_quota": True},
    )
    raw = r.json()["data"]["raw_key"]
    r = client.post(
        "/v1/chat/completions",
        headers={"Authorization": f"Bearer {raw}"},
        json={"model": "gpt-5.4-mini", "messages": [{"role": "user", "content": "hi"}]},
    )
    assert r.status_code == 403
    assert "不可用模型" in err_msg(r)


def test_token_quota_limit():
    jwt, _ = _login()
    r = client.post(
        "/api/token/",
        headers={"Authorization": f"Bearer {jwt}"},
        json={"name": "tiny", "group": "Codex（推荐）", "unlimited_quota": False, "remain_quota": 1},
    )
    raw = r.json()["data"]["raw_key"]
    r = client.post(
        "/v1/chat/completions",
        headers={"Authorization": f"Bearer {raw}"},
        json={"model": "gpt-5.4-mini", "messages": [{"role": "user", "content": "hi"}]},
    )
    assert r.status_code == 403
    assert "令牌额度不足" in err_msg(r)


def test_disabled_token():
    jwt, _ = _login()
    headers = {"Authorization": f"Bearer {jwt}"}
    r = client.post("/api/token/", headers=headers, json={"name": "off", "group": "Codex（推荐）"})
    tid = r.json()["data"]["id"]
    raw = r.json()["data"]["raw_key"]
    client.put("/api/token/", headers=headers, json={"id": tid, "status": 2})
    r = client.post(
        "/v1/chat/completions",
        headers={"Authorization": f"Bearer {raw}"},
        json={"model": "gpt-5.4-mini", "messages": [{"role": "user", "content": "hi"}]},
    )
    assert r.status_code == 401


def test_invite_and_aff_transfer():
    jwt, inviter = _login()
    aff = inviter["aff_code"]
    uname = "u" + secrets.token_hex(3)
    r = client.post("/api/user/register", json={"username": uname, "password": "123456", "aff_code": aff})
    assert r.json()["success"]
    jwt2, after = _login()
    assert after["aff_count"] >= inviter["aff_count"] + 1
    assert after["aff_quota"] > inviter["aff_quota"]
    r = client.post("/api/user/aff_transfer", headers={"Authorization": f"Bearer {jwt2}"}, json={})
    assert r.json()["success"]
    me = client.get("/api/user/self", headers={"Authorization": f"Bearer {jwt2}"}).json()["data"]
    assert me["aff_quota"] == 0
    assert me["quota"] >= after["quota"]


def test_redeem_once():
    jwt, _ = _login("admin", "admin123")
    headers = {"Authorization": f"Bearer {jwt}"}
    r = client.post("/api/redemption/", headers=headers, json={"name": "t", "count": 1, "amount_usd": 2})
    key = r.json()["data"][0]
    jwt_u, before = _login()
    uh = {"Authorization": f"Bearer {jwt_u}"}
    r = client.post("/api/user/topup", headers=uh, json={"key": key})
    assert r.json()["success"]
    r2 = client.post("/api/user/topup", headers=uh, json={"key": key})
    assert r2.status_code == 400
    after = client.get("/api/user/self", headers=uh).json()["data"]
    assert after["quota"] > before["quota"]
    logs = client.get("/api/log/self", headers=uh, params={"type": 1, "page_size": 20}).json()
    assert any("兑换码" in (x.get("content") or "") for x in logs["data"]["items"])


def test_image_requires_group_key():
    jwt, _ = _login()
    headers = {"Authorization": f"Bearer {jwt}"}
    r = client.post(
        "/api/image/generate",
        headers=headers,
        json={"model": "gpt-image-2-1k", "prompt": "cat", "size": "1:1", "quality": "1k"},
    )
    assert r.status_code == 200, r.text
    assert r.json()["data"]["b64"]
    assert r.json()["data"]["images"]


def test_image_wrong_group_key():
    jwt, _ = _login()
    headers = {"Authorization": f"Bearer {jwt}"}
    r = client.post(
        "/api/token/",
        headers=headers,
        json={"name": "codex-img", "group": "Codex（推荐）", "unlimited_quota": True},
    )
    raw = r.json()["data"]["raw_key"]
    tid = r.json()["data"]["id"]
    r = client.post(
        "/v1/images/generations",
        headers={"Authorization": f"Bearer {raw}"},
        json={"model": "gpt-image-2-1k", "prompt": "cat"},
    )
    assert r.status_code in (400, 403)
    r = client.post(
        "/api/image/generate",
        headers=headers,
        json={"model": "gpt-image-2-1k", "prompt": "cat", "token_id": tid},
    )
    assert r.status_code == 400
    assert "生图" in err_msg(r) or "分组" in err_msg(r)


def test_image_no_key_rejected():
    uname = "img" + secrets.token_hex(3)
    r = client.post("/api/user/register", json={"username": uname, "password": "123456"})
    jwt = r.json()["data"]["access_token"]
    r = client.post(
        "/api/image/generate",
        headers={"Authorization": f"Bearer {jwt}"},
        json={"model": "gpt-image-2-1k", "prompt": "cat", "size": "1:1", "quality": "1k"},
    )
    assert r.status_code == 400
    assert "生图分组" in err_msg(r)


def test_v1_models_filtered_by_group():
    jwt, _ = _login()
    r = client.post(
        "/api/token/",
        headers={"Authorization": f"Bearer {jwt}"},
        json={"name": "ds-only", "group": "Deepseek-官方", "unlimited_quota": True},
    )
    raw = r.json()["data"]["raw_key"]
    r = client.get("/v1/models", headers={"Authorization": f"Bearer {raw}"})
    ids = [m["id"] for m in r.json()["data"]]
    assert "deepseek-v4-flash" in ids
    assert "gpt-5.4-mini" not in ids


def test_embeddings_and_messages():
    jwt, _ = _login()
    r = client.post(
        "/api/token/",
        headers={"Authorization": f"Bearer {jwt}"},
        json={"name": "emb", "group": "Codex（推荐）", "unlimited_quota": True},
    )
    raw = r.json()["data"]["raw_key"]
    r = client.post(
        "/v1/embeddings",
        headers={"Authorization": f"Bearer {raw}"},
        json={"model": "text-embedding-3-small", "input": "hello"},
    )
    assert r.status_code == 200, r.text
    assert r.json()["data"][0]["embedding"]
    r = client.post(
        "/api/token/",
        headers={"Authorization": f"Bearer {jwt}"},
        json={"name": "claude", "group": "Claude Lite", "unlimited_quota": True},
    )
    raw = r.json()["data"]["raw_key"]
    r = client.post(
        "/v1/messages",
        headers={"x-api-key": raw},
        json={"model": "claude-sonnet-4-6", "max_tokens": 32, "messages": [{"role": "user", "content": "hi"}]},
    )
    assert r.status_code == 200, r.text
    assert r.json()["content"][0]["text"]


def test_responses_api_contract_and_streaming():
    jwt, _ = _login()
    r = client.post("/api/token/", headers={"Authorization": f"Bearer {jwt}"}, json={"name": "responses", "group": "Codex（推荐）", "unlimited_quota": True})
    raw = r.json()["data"]["raw_key"]
    headers = {"Authorization": f"Bearer {raw}"}
    r = client.post("/v1/responses", headers=headers, json={"model": "gpt-5.4-mini", "input": "hello"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["object"] == "response"
    assert body["status"] == "completed"
    assert body["output"][0]["content"][0]["type"] == "output_text"
    assert body["output_text"]
    with client.stream("POST", "/v1/responses", headers=headers, json={"model": "gpt-5.4-mini", "input": "hello", "stream": True}) as stream:
        content = "".join(stream.iter_text())
    assert "event: response.created" in content
    assert "event: response.output_text.delta" in content
    assert "event: response.completed" in content


def test_anthropic_streaming_contract():
    jwt, _ = _login()
    r = client.post("/api/token/", headers={"Authorization": f"Bearer {jwt}"}, json={"name": "claude-stream", "group": "Claude Lite", "unlimited_quota": True})
    raw = r.json()["data"]["raw_key"]
    with client.stream("POST", "/v1/messages", headers={"x-api-key": raw}, json={"model": "claude-sonnet-4-6", "max_tokens": 32, "stream": True, "messages": [{"role": "user", "content": "hi"}]}) as stream:
        content = "".join(stream.iter_text())
    assert "event: message_start" in content
    assert "event: content_block_delta" in content
    assert "event: message_stop" in content
