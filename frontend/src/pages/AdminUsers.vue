<template>
  <div class="card">
    <div class="card-title">用户管理</div>
    <table class="table">
      <thead><tr><th>ID</th><th>用户</th><th>分组</th><th>余额</th><th>状态</th><th>操作</th></tr></thead>
      <tbody>
        <tr v-for="u in rows" :key="u.id">
          <td>{{ u.id }}</td>
          <td>{{ u.username }}</td>
          <td>{{ u.group }}</td>
          <td>${{ u.balance_usd }}</td>
          <td>{{ u.status === 1 ? "正常" : "禁用" }}</td>
          <td>
            <button class="ghost-btn" @click="toggle(u)">{{ u.status === 1 ? "禁用" : "启用" }}</button>
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
async function load() {
  const { data } = await http.get("/api/user/");
  rows.value = data.data || [];
}
async function toggle(u) {
  await http.put("/api/user/", { id: u.id, status: u.status === 1 ? 2 : 1 });
  await load();
}
onMounted(load);
</script>
