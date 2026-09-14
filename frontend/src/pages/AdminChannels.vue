<template>
  <div class="card">
    <div class="card-title"><span>上游渠道</span><button class="primary-btn" @click="openCreate">添加渠道</button></div>
    <p class="muted">按优先级和分组为模型选择上游；连续失败 3 次的渠道会自动停用。</p>
    <table class="table"><thead><tr><th>名称</th><th>供应商</th><th>地址</th><th>分组</th><th>模型</th><th>状态</th><th>失败</th><th>操作</th></tr></thead>
      <tbody><tr v-for="c in rows" :key="c.id"><td>{{ c.name }}</td><td>{{ c.provider }}</td><td>{{ c.base_url }}</td><td>{{ c.groups }}</td><td>{{ c.models || "全部" }}</td><td>{{ c.status === 1 ? "启用" : "停用" }}</td><td>{{ c.failure_count }}</td><td><button class="ghost-btn" @click="edit(c)">编辑</button><button class="ghost-btn danger" @click="remove(c.id)">删除</button></td></tr></tbody>
    </table>
    <div v-if="!rows.length" class="empty">尚未配置数据库渠道，可使用 UPSTREAM_BASE_URL / UPSTREAM_API_KEY 作为默认渠道。</div>
  </div>
  <div v-if="modal" class="modal-mask" @click.self="modal=false"><div class="modal"><h5>{{ form.id ? "编辑渠道" : "添加渠道" }}</h5>
    <div class="field"><label>名称</label><input class="input plain" v-model="form.name" /></div>
    <div class="field"><label>Base URL</label><input class="input plain" v-model="form.base_url" placeholder="https://api.openai.com/v1" /></div>
    <div class="field"><label>API Key</label><input class="input plain" type="password" v-model="form.api_key" /></div>
    <div class="row"><div class="field"><label>供应商</label><input class="input plain" v-model="form.provider" /></div><div class="field"><label>优先级</label><input class="input plain" type="number" v-model.number="form.priority" /></div></div>
    <div class="field"><label>分组（逗号分隔）</label><input class="input plain" v-model="form.groups" /></div>
    <div class="field"><label>模型（逗号分隔，空=全部）</label><input class="input plain" v-model="form.models" /></div>
    <div class="notice-actions"><button class="ghost-btn" @click="modal=false">取消</button><button class="primary-btn" @click="save">保存</button></div>
  </div></div>
</template>
<script setup>
import { onMounted, reactive, ref } from "vue";
import http from "../api/http";
const rows = ref([]); const modal = ref(false);
const form = reactive({ id: 0, name: "", base_url: "", api_key: "", provider: "openai", groups: "default", models: "", priority: 0, status: 1, weight: 1 });
async function load() { const { data } = await http.get("/api/channel/"); rows.value = data.data || []; }
function openCreate() { Object.assign(form, { id: 0, name: "", base_url: "", api_key: "", provider: "openai", groups: "default", models: "", priority: 0, status: 1, weight: 1 }); modal.value = true; }
function edit(row) { Object.assign(form, row, { api_key: "" }); modal.value = true; }
async function save() { if (form.id) await http.put(`/api/channel/${form.id}`, form); else await http.post("/api/channel/", form); modal.value = false; await load(); }
async function remove(id) { await http.delete(`/api/channel/${id}`); await load(); }
onMounted(load);
</script>
