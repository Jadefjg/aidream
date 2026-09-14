<template>
  <div class="card">
    <div class="card-title">聊天</div>
    <p class="muted">将 THINK-AI 作为 OpenAI 兼容网关接入常用客户端，只需替换 Base URL 与 API Key。</p>
    <div class="card" v-for="c in clients" :key="c.name" style="margin-top:12px">
      <b>{{ c.name }}</b>
      <p class="muted">{{ c.desc }}</p>
      <code>{{ c.cmd }}</code>
    </div>
    <div class="toolbar" style="margin-top:16px">
      <router-link class="primary-btn" to="/console/playground">打开操练场</router-link>
      <router-link class="ghost-btn" to="/console/token">复制密钥</router-link>
    </div>
  </div>
</template>

<script setup>
const origin = location.origin;
const clients = [
  { name: "Cherry Studio", desc: "在供应商设置中填入 OpenAI 兼容地址。", cmd: `${origin}/v1` },
  { name: "Cursor / Codex", desc: "将 OPENAI_BASE_URL 指向本站。", cmd: `OPENAI_BASE_URL=${origin}/v1` },
  { name: "Lobe Chat", desc: "OpenAI 提供商的 API Key + Base URL。", cmd: `${origin}/v1` },
  { name: "curl 示例", desc: "标准 Chat Completions。", cmd: `curl ${origin}/v1/chat/completions -H "Authorization: Bearer sk-xxx"` },
];
</script>
