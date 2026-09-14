<template>
  <div class="card">
    <div class="card-title">
      <span>密钥管理</span>
      <span class="muted">{{ hint }}</span>
    </div>
    <div class="toolbar">
      <button class="primary-btn" @click="openCreate">添加密钥</button>
      <button class="ghost-btn" @click="copySelected">复制所选密钥</button>
      <button class="ghost-btn danger" @click="removeSelected">删除所选密钥</button>
      <input class="search" v-model="keyword" placeholder="搜索关键字" @keyup.enter="load" />
      <button class="ghost-btn" @click="page = 0; load()">查询</button>
    </div>
    <table class="table">
      <thead>
        <tr>
          <th></th><th>名称</th><th>状态</th><th>剩余额度</th><th>分组</th><th>密钥</th><th>操作</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="t in tokens" :key="t.id">
          <td><input type="checkbox" :value="t.id" v-model="picked" /></td>
          <td>{{ t.name }}</td>
          <td>
            <span class="badge" :class="t.status === 1 ? 'ok' : 'warn'">{{ statusText(t) }}</span>
          </td>
          <td>
            <span class="badge warn">{{ t.unlimited_quota ? "无限额度" : "$" + (t.remain_quota / 500000).toFixed(2) }}</span>
          </td>
          <td>{{ t.group || "跟随用户" }}</td>
          <td>{{ t.key }}</td>
          <td>
            <button class="ghost-btn" @click="copyOne(t)">复制</button>
            <button class="ghost-btn" @click="goPlay(t)">聊天</button>
            <button class="ghost-btn" @click="openEdit(t)">编辑</button>
            <button class="ghost-btn" @click="toggle(t)">{{ t.status === 1 ? "禁用" : "启用" }}</button>
            <button class="ghost-btn danger" @click="remove(t.id)">删除</button>
          </td>
        </tr>
      </tbody>
    </table>
    <div v-if="!tokens.length" class="empty">搜索无结果</div>
    <p class="muted">显示第 {{ from }} 条 - 第 {{ to }} 条，共 {{ total }} 条</p>
    <div class="toolbar">
      <button class="ghost-btn" :disabled="page===0" @click="page--; load()">上一页</button>
      <span>{{ page + 1 }}</span>
      <button class="ghost-btn" :disabled="to>=total" @click="page++; load()">下一页</button>
    </div>
  </div>

  <div v-if="modal" class="modal-mask" @click.self="modal = false">
    <div class="modal">
      <h5>{{ editing ? "编辑密钥" : "添加密钥" }}</h5>
      <div class="field"><label>名称</label><input class="input plain" v-model="form.name" /></div>
      <div class="field">
        <label>分组</label>
        <select class="input plain" v-model="form.group">
          <option value="">跟随用户分组</option>
          <option v-for="g in groups" :key="g" :value="g">{{ g }}</option>
        </select>
      </div>
      <div class="field"><label>模型限制（逗号分隔，空=不限制）</label><input class="input plain" v-model="form.models" placeholder="gpt-5.4-mini,gpt-image-2-1k" /></div>
      <div class="field"><label>IP 白名单（逗号分隔）</label><input class="input plain" v-model="form.subnet" /></div>
      <label style="display:flex;gap:8px;align-items:center;margin-bottom:12px">
        <input type="checkbox" v-model="form.unlimited_quota" /> 无限额度
      </label>
      <div class="field" v-if="!form.unlimited_quota">
        <label>剩余额度（USD）</label>
        <input class="input plain" type="number" v-model.number="remainUsd" />
      </div>
      <p v-if="createdKey" class="ok">新密钥（只显示一次）：{{ createdKey }}</p>
      <p v-if="hint" class="muted">{{ hint }}</p>
      <div class="notice-actions">
        <button class="ghost-btn" @click="modal = false">关闭</button>
        <button class="primary-btn" @click="submit">提交</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from "vue";
import { useRouter } from "vue-router";
import http from "../api/http";

const router = useRouter();
const tokens = ref([]);
const total = ref(0);
const page = ref(0);
const size = 10;
const keyword = ref("");
const picked = ref([]);
const modal = ref(false);
const editing = ref(null);
const createdKey = ref("");
const hint = ref("");
const groups = ref([]);
const remainUsd = ref(1);
const from = computed(() => (total.value ? page.value * size + 1 : 0));
const to = computed(() => Math.min((page.value + 1) * size, total.value));
const form = reactive({ name: "default", group: "", unlimited_quota: true, models: "", subnet: "" });

function statusText(t) {
  if (t.status === 1) return "已启用";
  if (t.status === 4) return "已耗尽";
  return "已禁用";
}
function openCreate() {
  editing.value = null;
  createdKey.value = "";
  form.name = "default";
  form.group = "";
  form.unlimited_quota = true;
  form.models = "";
  form.subnet = "";
  remainUsd.value = 1;
  modal.value = true;
}
function openEdit(t) {
  editing.value = t;
  createdKey.value = "";
  form.name = t.name;
  form.group = t.group || "";
  form.unlimited_quota = t.unlimited_quota;
  form.models = t.models || "";
  form.subnet = t.subnet || "";
  remainUsd.value = Number((t.remain_quota / 500000).toFixed(2));
  modal.value = true;
}
async function load() {
  const { data } = await http.get("/api/token/", { params: { p: page.value, size, keyword: keyword.value } });
  tokens.value = data.data || [];
  total.value = data.total || tokens.value.length;
}
async function submit() {
  const payload = {
    ...form,
    remain_quota: form.unlimited_quota ? 0 : Math.round(remainUsd.value * 500000),
  };
  if (editing.value) {
    await http.put("/api/token/", { id: editing.value.id, ...payload });
    hint.value = "已更新";
  } else {
    const { data } = await http.post("/api/token/", payload);
    createdKey.value = data.data.raw_key || data.data.key;
    hint.value = "请立即复制密钥，关闭后只显示掩码";
  }
  await load();
}
async function copyOne(t) {
  const { data } = await http.get(`/api/token/${t.id}/key`);
  await navigator.clipboard.writeText(data.data.key);
  hint.value = `已复制 ${t.name}`;
}
async function copySelected() {
  const keys = [];
  for (const id of picked.value) {
    const { data } = await http.get(`/api/token/${id}/key`);
    keys.push(data.data.key);
  }
  await navigator.clipboard.writeText(keys.join("\n"));
  hint.value = `已复制 ${keys.length} 个密钥`;
}
async function toggle(t) {
  await http.put("/api/token/", { id: t.id, status: t.status === 1 ? 2 : 1 });
  await load();
}
async function remove(id) {
  await http.delete(`/api/token/${id}`);
  await load();
}
async function removeSelected() {
  for (const id of picked.value) await remove(id);
  picked.value = [];
}
function goPlay(t) {
  router.push({ path: "/console/playground", query: { token_id: t.id } });
}
onMounted(async () => {
  await load();
  const { data } = await http.get("/api/user/self/groups");
  groups.value = Object.keys(data.data || {});
});
</script>
