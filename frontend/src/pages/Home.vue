<template>
  <div class="page-shell home">
    <AppHeader @notice="notice = true" />
    <section class="hero">
      <h1>统一的<br /><span>大模型接口网关</span></h1>
      <p>更好的价格，更好的稳定性，只需要将模型基址替换为：</p>
      <div class="endpoint">
        <span class="host">{{ host }}</span>
        <select v-model="path">
          <option v-for="p in paths" :key="p" :value="p">{{ p }}</option>
        </select>
        <button class="icon-btn" type="button" :title="copied ? '已复制' : '复制接口地址'" aria-label="复制接口地址" @click="copy"><Check v-if="copied" :size="17" /><Copy v-else :size="17" /></button>
      </div>
      <div class="hero-actions">
        <router-link class="primary-btn" to="/console">立即开始</router-link>
        <a class="ghost-btn" href="https://qm.qq.com/cgi-bin/qm/qr?k=" target="_blank">联系我们</a>
      </div>
    </section>
    <section class="providers">
      <div>支持众多的大模型供应商</div>
      <div class="provider-grid">
        <div v-for="p in providers" :key="p.name" class="provider-orb" :style="{ background: p.color }">{{ p.short }}</div>
        <div class="provider-orb" style="background:#222;width:auto;padding:0 12px;border-radius:12px">30+</div>
      </div>
    </section>
    <footer class="footer">
      <span>© 2026. 版权所有</span>
      <span>设计与开发由 <a href="https://github.com/QuantumNous/new-api" target="_blank">New API</a></span>
    </footer>
    <NoticeModal :open="notice" @close="notice = false" />
  </div>
</template>

<script setup>
import { onMounted, ref } from "vue";
import { Check, Copy } from "@lucide/vue";
import AppHeader from "../components/AppHeader.vue";
import NoticeModal from "../components/NoticeModal.vue";

const notice = ref(!sessionStorage.getItem("notice_closed"));
const host = ref(location.origin);
const path = ref("/v1/chat/completions");
const copied = ref(false);
const paths = [
  "/v1/chat/completions",
  "/v1/responses",
  "/v1/responses/compact",
  "/v1/messages",
  "/v1beta/models",
  "/v1/embeddings",
  "/v1/rerank",
  "/v1/images/generations",
  "/v1/images/edits",
  "/v1/images/variations",
  "/v1/audio/speech",
  "/v1/audio/transcriptions",
  "/v1/audio/translations",
];
const providers = [
  { name: "OpenAI", short: "OA", color: "#10a37f" },
  { name: "Anthropic", short: "AN", color: "#d97706" },
  { name: "xAI", short: "xAI", color: "#111" },
  { name: "Google", short: "G", color: "#4285f4" },
  { name: "Azure", short: "Az", color: "#0078d4" },
  { name: "Meta", short: "M", color: "#0668e1" },
  { name: "Mistral", short: "Mi", color: "#ff7000" },
  { name: "Cohere", short: "C", color: "#39594d" },
  { name: "DeepSeek", short: "DS", color: "#4d6bfe" },
  { name: "Qwen", short: "Q", color: "#615ced" },
  { name: "Zhipu", short: "Z", color: "#3859ff" },
  { name: "Moonshot", short: "K", color: "#1f1f1f" },
  { name: "Yi", short: "Yi", color: "#0037ff" },
  { name: "Baidu", short: "B", color: "#2932e1" },
  { name: "Minimax", short: "Mm", color: "#ef4444" },
  { name: "Step", short: "S", color: "#7c3aed" },
  { name: "Grok", short: "X", color: "#222" },
];

async function copy() {
  await navigator.clipboard.writeText(host.value + path.value);
  copied.value = true;
  window.setTimeout(() => (copied.value = false), 1600);
}
onMounted(() => {
  if (!sessionStorage.getItem("notice_closed")) notice.value = true;
});
</script>
