<template>
  <div class="card">
    <div class="card-title">兑换码管理</div>
    <div class="toolbar">
      <input class="search" v-model="name" placeholder="批次名称" />
      <input class="search" type="number" v-model.number="count" placeholder="数量" />
      <input class="search" type="number" v-model.number="amount" placeholder="面值 USD" />
      <button class="primary-btn" @click="create">生成兑换码</button>
    </div>
    <p v-if="msg" class="ok">{{ msg }}</p>
    <p v-if="created.length" class="muted">新码：{{ created.join(" , ") }}</p>
    <table class="table">
      <thead><tr><th>名称</th><th>码</th><th>面值</th><th>状态</th><th>操作</th></tr></thead>
      <tbody>
        <tr v-for="r in rows" :key="r.id">
          <td>{{ r.name }}</td>
          <td>{{ r.key }}</td>
          <td>${{ r.quota_usd }}</td>
          <td>{{ r.status === 1 ? "未使用" : r.status === 3 ? "已使用" : "已禁用" }}</td>
          <td>
            <button class="ghost-btn" v-if="r.status === 1" @click="disable(r)">禁用</button>
            <button class="ghost-btn danger" @click="remove(r.id)">删除</button>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<script setup>
import { onMounted, ref } from "vue";
import http from "../api/http";

const rows = ref([]);
const name = ref("promo");
const count = ref(1);
const amount = ref(10);
const created = ref([]);
const msg = ref("");

async function load() {
  const { data } = await http.get("/api/redemption/");
  rows.value = data.data || [];
}
async function create() {
  const { data } = await http.post("/api/redemption/", { name: name.value, count: count.value, amount_usd: amount.value });
  created.value = data.data || [];
  msg.value = data.message;
  await load();
}
async function disable(r) {
  await http.put("/api/redemption/", { id: r.id, status: 2 });
  await load();
}
async function remove(id) {
  await http.delete(`/api/redemption/${id}`);
  await load();
}
onMounted(load);
</script>
