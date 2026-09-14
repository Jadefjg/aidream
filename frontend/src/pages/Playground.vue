<template>
  <div class="playground">
    <div class="card">
      <h5>模型配置</h5>
      <div class="field">
        <label>分组</label>
        <select class="input plain" v-model="group" @change="loadModels" :disabled="Boolean(tokenId && tokenGroup)">
          <option v-for="g in groups" :key="g" :value="g">{{ g }}</option>
        </select>
      </div>
      <div class="field">
        <label>模型</label>
        <select class="input plain" v-model="model">
          <option v-for="m in models" :key="m" :value="m">{{ m }}</option>
        </select>
      </div>
      <div class="field"><label>Temperature {{ temperature }}</label><input type="range" min="0" max="2" step="0.1" v-model.number="temperature" /></div>
      <div class="field"><label>Top P {{ top_p }}</label><input type="range" min="0" max="1" step="0.05" v-model.number="top_p" /></div>
      <div class="field"><label>MaxTokens</label><input class="input plain" type="number" v-model.number="max_tokens" /></div>
      <label style="display:flex;gap:8px;align-items:center"><input type="checkbox" v-model="stream" /> 流式输出</label>
      <p v-if="tokenId" class="muted">当前使用密钥 ID {{ tokenId }}{{ tokenGroup ? ` · 分组 ${tokenGroup}` : "" }}</p>
    </div>
    <div class="card chat-box">
      <div class="card-title">
        <h5 style="margin:0">AI 对话</h5>
        <div>
          <button class="ghost-btn" @click="exportChat">导出</button>
          <button class="ghost-btn" @click="messages = defaultMsgs()">清空</button>
        </div>
      </div>
      <div class="msgs" ref="box">
        <div v-for="(m, i) in messages" :key="i" class="msg" :class="m.role">
          {{ m.content }}
        </div>
      </div>
      <div class="composer">
        <textarea v-model="input" placeholder="请输入您的问题...  Enter 发送，Shift+Enter 换行" @keydown.enter.exact.prevent="send"></textarea>
        <button class="primary-btn" :disabled="loading" @click="send">发送</button>
      </div>
      <p v-if="error" class="error">{{ error }}</p>
    </div>
  </div>
</template>

<script setup>
import { nextTick, onMounted, ref } from "vue";
import { useRoute } from "vue-router";
import http from "../api/http";
import { useAuthStore } from "../store/auth";

const auth = useAuthStore();
const route = useRoute();
const models = ref(["gpt-5.4-mini"]);
const groups = ref(["default"]);
const group = ref("default");
const model = ref("gpt-5.4-mini");
const tokenId = ref(route.query.token_id ? Number(route.query.token_id) : null);
const tokenGroup = ref("");
const temperature = ref(0.7);
const top_p = ref(1);
const max_tokens = ref(4096);
const stream = ref(true);
const input = ref("");
const loading = ref(false);
const error = ref("");
const box = ref(null);
function defaultMsgs() {
  return [
    { role: "user", content: "你好" },
    { role: "assistant", content: "你好！有什么我可以帮助你的吗？" },
  ];
}
const messages = ref(defaultMsgs());

async function loadModels() {
  const { data } = await http.get("/api/user/models", { params: { group: group.value } });
  models.value = (data.data || [])
    .filter((n) => !/^(tts-|whisper-)|embedding|rerank/i.test(n))
    .slice()
    .sort((a, b) => {
    const score = (n) => (n.startsWith("gpt-") ? 0 : n.startsWith("claude") ? 1 : 2);
    return score(a) - score(b) || a.localeCompare(b);
  });
  if (!models.value.includes(model.value)) model.value = models.value[0] || "";
}

onMounted(async () => {
  group.value = auth.user?.group || "default";
  const { data } = await http.get("/api/user/self/groups");
  groups.value = Object.keys(data.data || { default: 1 });
  if (tokenId.value) {
    const tok = await http.get("/api/token/", { params: { p: 0, size: 100 } });
    const t = (tok.data.data || []).find((x) => x.id === tokenId.value);
    if (t?.group) {
      tokenGroup.value = t.group;
      group.value = t.group;
    }
  }
  await loadModels();
});

async function send() {
  const text = input.value.trim();
  if (!text || loading.value) return;
  messages.value.push({ role: "user", content: text });
  input.value = "";
  loading.value = true;
  error.value = "";
  const payload = {
    model: model.value,
    messages: messages.value.filter((m) => m.role !== "system"),
    stream: stream.value,
    temperature: temperature.value,
    max_tokens: max_tokens.value,
    group: group.value,
    token_id: tokenId.value || undefined,
  };
  try {
    if (stream.value) {
      messages.value.push({ role: "assistant", content: "" });
      const idx = messages.value.length - 1;
      const resp = await fetch("/api/playground/chat", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${localStorage.getItem("access_token")}`,
        },
        body: JSON.stringify(payload),
      });
      if (!resp.ok) {
        const j = await resp.json().catch(() => ({}));
        throw new Error(j.message || "请求失败");
      }
      const reader = resp.body.getReader();
      const decoder = new TextDecoder();
      let buf = "";
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buf += decoder.decode(value, { stream: true });
        const parts = buf.split("\n\n");
        buf = parts.pop() || "";
        for (const part of parts) {
          const line = part.replace(/^data:\s*/, "");
          if (!line) continue;
          const json = JSON.parse(line);
          if (json.content) messages.value[idx].content += json.content;
        }
        await nextTick();
        if (box.value) box.value.scrollTop = box.value.scrollHeight;
      }
    } else {
      const { data } = await http.post("/api/playground/chat", payload);
      messages.value.push({ role: "assistant", content: data.data.content });
    }
    await auth.refresh();
  } catch (e) {
    error.value = e.message;
    const last = messages.value[messages.value.length - 1];
    if (last && last.role === "assistant" && !last.content) messages.value.pop();
  } finally {
    loading.value = false;
  }
}

function exportChat() {
  const blob = new Blob([JSON.stringify(messages.value, null, 2)], { type: "application/json" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = "playground.json";
  a.click();
}
</script>
