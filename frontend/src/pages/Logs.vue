<template>
  <div class="card">
    <div class="card-title">
      <span>使用日志</span>
      <button class="ghost-btn">紧凑列表</button>
    </div>
    <div class="toolbar">
      <input class="search" type="datetime-local" v-model="start" />
      <input class="search" type="datetime-local" v-model="end" />
      <input class="search" v-model="token_name" placeholder="令牌名称" />
      <input class="search" v-model="model_name" placeholder="模型名称" />
      <input class="search" v-model="group" placeholder="分组" />
      <select class="search" v-model="type">
        <option :value="null">全部</option>
        <option :value="1">充值</option>
        <option :value="2">消费</option>
        <option :value="7">登录</option>
        <option :value="4">系统</option>
        <option :value="5">错误</option>
      </select>
      <button class="ghost-btn" @click="load">查询</button>
      <button class="ghost-btn" @click="reset">重置</button>
    </div>
    <table class="table">
      <thead>
        <tr>
          <th>时间</th><th>令牌</th><th>分组</th><th>类型</th><th>模型</th><th>用时</th><th>输入</th><th>输出</th><th>花费</th><th>详情</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="l in items" :key="l.id">
          <td>{{ fmt(l.created_at) }}</td>
          <td>{{ l.token_name || "-" }}</td>
          <td>{{ l.group || "-" }}</td>
          <td>{{ l.type_name || (l.type === 2 ? "消费" : "系统") }}</td>
          <td>{{ l.model_name || "-" }}</td>
          <td>{{ l.use_time }}s</td>
          <td>{{ l.prompt_tokens }}</td>
          <td>{{ l.completion_tokens }}</td>
          <td>${{ (l.quota_usd || 0).toFixed(4) }}</td>
          <td class="muted">{{ l.request_id }}</td>
        </tr>
      </tbody>
    </table>
    <div v-if="!items.length" class="empty">搜索无结果</div>
    <p class="muted">共 {{ total }} 条，第 {{ page }} 页</p>
    <div class="toolbar">
      <button class="ghost-btn" :disabled="page===1" @click="page--; load()">上一页</button>
      <button class="ghost-btn" :disabled="page * 20 >= total" @click="page++; load()">下一页</button>
    </div>
  </div>
</template>

<script setup>
import { onMounted, ref } from "vue";
import http from "../api/http";

const items = ref([]);
const total = ref(0);
const token_name = ref("");
const model_name = ref("");
const group = ref("");
const type = ref(null);
const start = ref("");
const end = ref("");
const page = ref(1);

function fmt(ts) {
  if (!ts) return "-";
  return new Date(ts * 1000).toLocaleString();
}
function toTs(v) {
  return v ? Math.floor(new Date(v).getTime() / 1000) : 0;
}
async function load() {
  const params = {
    p: page.value,
    page_size: 20,
    token_name: token_name.value,
    model_name: model_name.value,
    group: group.value,
    start_timestamp: toTs(start.value),
    end_timestamp: toTs(end.value),
  };
  if (type.value !== null && type.value !== "") params.type = type.value;
  const { data } = await http.get("/api/log/self", { params });
  items.value = data.data.items || [];
  total.value = data.data.total || 0;
}
function reset() {
  token_name.value = model_name.value = group.value = start.value = end.value = "";
  type.value = null;
  page.value = 1;
  load();
}
onMounted(load);
</script>
