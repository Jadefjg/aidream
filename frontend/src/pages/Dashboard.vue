<template>
  <div>
    <h2 class="hello">{{ greet }}，{{ auth.user?.display_name || auth.user?.username }}</h2>
    <div class="row">
      <div class="card">
        <div class="card-title">账户数据</div>
        <div class="stat">
          <div class="dot" style="background:#3b82f6">$</div>
          <div>
            <div class="muted">当前余额</div>
            <div class="num">${{ data.balance_usd?.toFixed?.(2) ?? "0.00" }}</div>
          </div>
          <router-link class="ghost-btn" style="margin-left:auto" to="/console/topup">充值</router-link>
        </div>
        <div class="stat">
          <div class="dot" style="background:#7c3aed">📈</div>
          <div>
            <div class="muted">历史消耗</div>
            <div class="num">${{ data.used_usd?.toFixed?.(2) ?? "0.00" }}</div>
          </div>
        </div>
      </div>
      <div class="card">
        <div class="card-title">使用统计</div>
        <div class="stat">
          <div class="dot" style="background:#22c55e">➤</div>
          <div>
            <div class="muted">请求次数</div>
            <div class="num">{{ data.request_count || 0 }}</div>
          </div>
        </div>
        <div class="stat">
          <div class="dot" style="background:#06b6d4">∿</div>
          <div>
            <div class="muted">统计次数</div>
            <div class="num">{{ data.stat_count || 0 }}</div>
          </div>
        </div>
      </div>
    </div>
    <div class="row" style="margin-top:16px">
      <div class="card">
        <div class="card-title">资源消耗</div>
        <div class="stat">
          <div class="dot" style="background:#eab308">●</div>
          <div>
            <div class="muted">统计额度</div>
            <div class="num">${{ ((data.stat_quota || 0) / 500000).toFixed(2) }}</div>
          </div>
        </div>
        <div class="stat">
          <div class="dot" style="background:#ec4899">T</div>
          <div>
            <div class="muted">统计 Tokens</div>
            <div class="num">{{ (data.stat_tokens || 0).toLocaleString() }}</div>
          </div>
        </div>
      </div>
      <div class="card">
        <div class="card-title">性能指标</div>
        <div class="stat">
          <div class="dot" style="background:#3b82f6">⏱</div>
          <div>
            <div class="muted">平均 RPM</div>
            <div class="num">{{ data.rpm || 0 }}</div>
          </div>
        </div>
        <div class="stat">
          <div class="dot" style="background:#f97316">Ag</div>
          <div>
            <div class="muted">平均 TPM</div>
            <div class="num">{{ data.tpm || 0 }}</div>
          </div>
        </div>
      </div>
    </div>
    <div class="card" style="margin-top:16px">
      <div class="card-title">模型数据分析</div>
      <div class="tabs">
        <span :class="{ active: tab === '消耗分布' }" @click="tab = '消耗分布'">消耗分布</span>
        <span :class="{ active: tab === '调用趋势' }" @click="tab = '调用趋势'">调用趋势</span>
        <span :class="{ active: tab === '调用次数分布' }" @click="tab = '调用次数分布'">调用次数分布</span>
        <span :class="{ active: tab === '调用次数排行' }" @click="tab = '调用次数排行'">调用次数排行</span>
      </div>
      <svg class="chart" viewBox="0 0 800 240">
        <line v-for="i in 5" :key="i" :x1="40" :x2="780" :y1="40 * i" :y2="40 * i" stroke="#2a2a31" />
        <polyline fill="none" stroke="#5b9dff" stroke-width="2" :points="points" />
        <text x="40" y="230" fill="#8d8d96" font-size="12">近期调用消耗趋势 · 总计 ${{ ((data.stat_quota || 0) / 500000).toFixed(2) }}</text>
      </svg>
      <div class="row" style="margin-top:8px">
        <div>
          <div class="muted">模型消耗分布</div>
          <div v-for="m in data.models || []" :key="m.name" style="margin:8px 0">
            {{ m.name }} · ${{ (m.quota / 500000).toFixed(4) }} · {{ m.count }} 次
          </div>
          <div v-if="!(data.models || []).length" class="muted">暂无模型数据</div>
        </div>
      </div>
    </div>
    <div class="row" style="margin-top:16px">
      <div class="card"><h4>API信息</h4><p class="muted">暂无API信息<br />请联系管理员在系统设置中配置API信息</p></div>
      <div class="card"><h4>系统公告</h4><p class="muted">欢迎使用 THINK-AI 本地网关。兑换码：WELCOME100</p></div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from "vue";
import http from "../api/http";
import { useAuthStore } from "../store/auth";

const auth = useAuthStore();
const data = ref({});
const tab = ref("消耗分布");
const hour = new Date().getHours();
const greet = hour < 12 ? "👋上午好" : hour < 18 ? "👋下午好" : "👋晚上好";
const points = computed(() => {
  const trend = data.value.trend || [];
  if (!trend.length) return "40,180 780,180";
  const max = Math.max(...trend.map((t) => t.quota), 1);
  return trend
    .map((t, i) => {
      const x = 40 + (i * 740) / Math.max(trend.length - 1, 1);
      const y = 200 - (t.quota / max) * 150;
      return `${x},${y}`;
    })
    .join(" ");
});

onMounted(async () => {
  const { data: res } = await http.get("/api/data/");
  data.value = res.data;
  await auth.refresh();
});
</script>
