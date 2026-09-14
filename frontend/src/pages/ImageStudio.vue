<template>
  <div class="page-shell home">
    <AppHeader />
    <section class="image-hero">
      <h1>ThinkAI × GPT-Image2</h1>
      <p class="muted">用 GPT-Image2 生成超写实摄影、精致 UI 视觉、商业产品效果图和可编辑的创意概念图。</p>
      <div class="hero-actions" style="justify-content:flex-start">
        <a class="primary-btn" href="#studio">立即出图</a>
        <router-link class="ghost-btn" to="/pricing">找灵感</router-link>
      </div>
    </section>
    <section id="studio" class="main">
      <div class="toolbar">
        <button class="ghost-btn" @click="reset">+ 新建生图任务</button>
        <button class="ghost-btn" @click="tasks = []">清空</button>
        <span style="flex:1"></span>
        <select class="search" v-model="tokenId" style="min-width:220px">
          <option :value="0">自动匹配生图分组密钥</option>
          <option v-for="t in imageTokens" :key="t.id" :value="t.id">{{ t.name }} · {{ t.group || "default" }}</option>
        </select>
        <router-link class="ghost-btn" to="/console/token">去创建密钥</router-link>
      </div>
      <p v-if="auth.isLogin && !imageTokens.length" class="error">当前账号没有生图分组密钥。请到控制台创建分组为 gpt-image-2-1k / 2k / 4k 或 OpenAI-image2生图专用 的密钥。</p>
      <div class="studio">
        <aside class="studio-side">
          <p class="muted" v-if="!tasks.length">还没有图片记录，输入提示词后会在这里显示。</p>
          <div v-for="t in tasks" :key="t.id" style="margin-bottom:10px;cursor:pointer" @click="current = t">
            <img :src="'data:image/png;base64,' + t.b64" style="width:100%;border-radius:8px" />
            <div class="muted">{{ t.prompt }}</div>
          </div>
        </aside>
        <div style="padding:16px">
          <div class="card-title">
            <div>
              <div>ThinkAI生图工作台</div>
              <div class="muted">消耗走所选密钥的分组倍率，并同步扣减账户余额。</div>
            </div>
          </div>
          <div class="image-canvas">
            <img v-if="current" :src="'data:image/png;base64,' + current.b64" />
            <span v-else>从下方输入提示词开始新的生图任务。</span>
          </div>
          <textarea class="input plain" style="height:80px;margin:12px 0;padding:12px;width:100%" v-model="prompt" placeholder="描述你想生成的画面..."></textarea>
          <div class="chips">
            <button class="chip" v-for="s in sizes" :key="s" :class="{ active: size === s }" @click="size = s">{{ s }}</button>
          </div>
          <div class="chips">
            <button class="chip" v-for="q in qualities" :key="q" :class="{ active: quality === q }" @click="quality = q">{{ q }}</button>
          </div>
          <div class="toolbar">
            <button class="ghost-btn" @click="n = Math.max(1, n - 1)">-</button>
            <span>{{ n }} 张</span>
            <button class="ghost-btn" @click="n = Math.min(4, n + 1)">+</button>
            <button class="primary-btn" :disabled="loading || !auth.isLogin" @click="generate">{{ auth.isLogin ? "立即出图" : "立即登录" }}</button>
          </div>
          <p v-if="err" class="error">{{ err }}</p>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import AppHeader from "../components/AppHeader.vue";
import http from "../api/http";
import { useAuthStore } from "../store/auth";

const IMAGE_GROUPS = ["OpenAI-image2生图专用", "gpt-image-2-1k", "gpt-image-2-2k", "gpt-image-2-4k", "Grok image", "Nano Banana Pro"];
const auth = useAuthStore();
const router = useRouter();
const prompt = ref("");
const size = ref("1:1");
const quality = ref("1K 分辨率");
const n = ref(1);
const loading = ref(false);
const err = ref("");
const tasks = ref([]);
const current = ref(null);
const tokens = ref([]);
const tokenId = ref(0);
const sizes = ["1:1", "16:9", "4:3", "3:4", "9:16"];
const qualities = ["1K 分辨率", "2K 分辨率", "4K 分辨率"];
const qualityMap = { "1K 分辨率": "1k", "2K 分辨率": "2k", "4K 分辨率": "4k" };
const modelMap = { "1K 分辨率": "gpt-image-2-1k", "2K 分辨率": "gpt-image-2-2k", "4K 分辨率": "gpt-image-2-4k" };
const imageTokens = computed(() =>
  tokens.value.filter((t) => t.status === 1 && IMAGE_GROUPS.includes(t.group || auth.user?.group))
);

function imageModel() {
  const t = imageTokens.value.find((x) => x.id === tokenId.value);
  if (t?.group === "OpenAI-image2生图专用") return "gpt-image-2";
  if (t?.group === "gpt-image-2-1k") return "gpt-image-2-1k";
  if (t?.group === "gpt-image-2-2k") return "gpt-image-2-2k";
  if (t?.group === "gpt-image-2-4k") return "gpt-image-2-4k";
  if (t?.group === "Grok image") return "grok-imagine-image";
  if (t?.group === "Nano Banana Pro") return "nano-banana-pro";
  return modelMap[quality.value];
}

onMounted(async () => {
  if (!auth.isLogin) return;
  const [taskRes, tokenRes] = await Promise.all([http.get("/api/image/tasks"), http.get("/api/token/", { params: { p: 0, size: 50 } })]);
  tasks.value = taskRes.data.data || [];
  current.value = tasks.value[0] || null;
  tokens.value = tokenRes.data.data || [];
});

function reset() {
  prompt.value = "";
  current.value = null;
}

async function generate() {
  if (!auth.isLogin) return router.push("/login?redirect=/gpt-image-2");
  if (!prompt.value.trim()) return;
  loading.value = true;
  err.value = "";
  try {
    const { data } = await http.post("/api/image/generate", {
      model: imageModel(),
      prompt: prompt.value,
      n: n.value,
      size: size.value,
      quality: qualityMap[quality.value],
      token_id: tokenId.value || undefined,
    });
    const imgs = data.data.images || [data.data];
    current.value = imgs[0];
    tasks.value = [...imgs, ...tasks.value];
    await auth.refresh();
  } catch (e) {
    err.value = e.message;
  } finally {
    loading.value = false;
  }
}
</script>
