<template>
  <div class="page-shell">
    <AppHeader />
    <div class="main pricing-layout" style="padding-top:12px">
      <aside>
        <div class="card-title">筛选 <button class="ghost-btn" @click="reset">重置</button></div>
        <div class="side-label">供应商</div>
        <div class="filter-item" :class="{ active: vendor === '' }" @click="vendor = ''">全部供应商 <span>{{ items.length }}</span></div>
        <div class="filter-item" v-for="v in vendors" :key="v.name" :class="{ active: vendor === v.name }" @click="vendor = v.name">
          {{ v.name }} <span>{{ v.count }}</span>
        </div>
        <div class="side-label">计费类型</div>
        <div class="filter-item" :class="{ active: qtype === null }" @click="qtype = null">全部类型</div>
        <div class="filter-item" :class="{ active: qtype === 0 }" @click="qtype = 0">按量计费</div>
        <div class="filter-item" :class="{ active: qtype === 1 }" @click="qtype = 1">按次计费</div>
      </aside>
      <section>
        <div class="banner">
          <div style="font-size:22px;font-weight:800">全部供应商 <span class="badge" style="background:#fff;color:#2f6bff">共 {{ filtered.length }} 个模型</span></div>
          <p>查看所有可用的AI模型供应商，包括众多知名供应商的模型。</p>
        </div>
        <div class="toolbar">
          <input class="search" style="flex:1" v-model="q" placeholder="模糊搜索模型名称" />
        </div>
        <table class="table">
          <thead>
            <tr>
              <th>模型名称</th><th>供应商</th><th>计费类型</th><th>模型价格</th><th>官方价</th><th>节省</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="m in pageItems" :key="m.model_name">
              <td><span class="model-tag">{{ m.model_name }}</span></td>
              <td>{{ m.vendor_name }}</td>
              <td><span class="badge purple">{{ m.quota_type === 1 ? "按次计费" : "按量计费" }}</span></td>
              <td>
                <div v-if="m.quota_type === 1">模型价格 ${{ m.input_price }} / 次</div>
                <div v-else>
                  输入价格 ${{ m.input_price.toFixed(4) }} / 1M Tokens<br />
                  补全价格 ${{ m.completion_price.toFixed(4) }} / 1M Tokens
                </div>
              </td>
              <td>
                <div v-if="m.quota_type === 1">模型价格 ${{ m.official_input }} / 次</div>
                <div v-else>
                  输入价格 ${{ m.official_input.toFixed(4) }} / 1M Tokens<br />
                  补全价格 ${{ m.official_completion.toFixed(4) }} / 1M Tokens
                </div>
              </td>
              <td>{{ m.save_percent ? `-${m.save_percent}%` : "-" }}</td>
            </tr>
          </tbody>
        </table>
        <p class="muted">显示第 {{ from }} 条-第 {{ to }} 条，共 {{ filtered.length }} 条</p>
        <div class="toolbar">
          <button class="ghost-btn" :disabled="page===1" @click="page--">上一页</button>
          <span>{{ page }}</span>
          <button class="ghost-btn" :disabled="to>=filtered.length" @click="page++">下一页</button>
        </div>
      </section>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from "vue";
import AppHeader from "../components/AppHeader.vue";
import http from "../api/http";

const items = ref([]);
const q = ref("");
const vendor = ref("");
const qtype = ref(null);
const page = ref(1);
const size = 20;

const vendors = computed(() => {
  const map = {};
  for (const m of items.value) map[m.vendor_name] = (map[m.vendor_name] || 0) + 1;
  return Object.entries(map).map(([name, count]) => ({ name, count }));
});
const filtered = computed(() =>
  items.value.filter((m) => {
    if (vendor.value && m.vendor_name !== vendor.value) return false;
    if (qtype.value !== null && m.quota_type !== qtype.value) return false;
    if (q.value && !m.model_name.toLowerCase().includes(q.value.toLowerCase())) return false;
    return true;
  })
);
const pageItems = computed(() => filtered.value.slice((page.value - 1) * size, page.value * size));
const from = computed(() => (filtered.value.length ? (page.value - 1) * size + 1 : 0));
const to = computed(() => Math.min(page.value * size, filtered.value.length));

watch([q, vendor, qtype], () => (page.value = 1));
function reset() {
  q.value = "";
  vendor.value = "";
  qtype.value = null;
}
onMounted(async () => {
  const { data } = await http.get("/api/pricing");
  items.value = data.data || [];
});
</script>
