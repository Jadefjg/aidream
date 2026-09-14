<template>
  <div>
    <div class="card">
      <div class="card-title">
        <div>
          <div>账户充值</div>
          <div class="muted">兑换码到账后立即计入余额，并写入使用日志</div>
        </div>
        <router-link class="primary-btn" to="/console/log">账单</router-link>
      </div>
      <div class="topup-hero">
        <div><div class="n">${{ (auth.user?.balance_usd || 0).toFixed(2) }}</div><div>当前余额</div></div>
        <div><div class="n">${{ (auth.user?.used_usd || 0).toFixed(2) }}</div><div>历史消耗</div></div>
        <div><div class="n">{{ auth.user?.request_count || 0 }}</div><div>请求次数</div></div>
      </div>
      <div class="card" style="margin-top:16px">
        <div class="card-title">兑换码充值</div>
        <div class="toolbar">
          <input class="search" style="flex:1" v-model="code" placeholder="请输入兑换码" />
          <button class="primary-btn" @click="redeem">兑换额度</button>
        </div>
        <p v-if="msg" class="ok">{{ msg }}</p>
        <p v-if="err" class="error">{{ err }}</p>
        <p class="muted">演示兑换码：WELCOME100（$100）</p>
      </div>
    </div>
    <div class="card">
      <div class="card-title">
        <div>
          <div>邀请计划</div>
          <div class="muted">好友注册后奖励进入待使用收益，需划转到余额后才能调用模型</div>
        </div>
      </div>
      <div class="row">
        <div>
          <div class="muted">待使用收益</div>
          <div class="num" style="color:#5b9dff">${{ ((auth.user?.aff_quota || 0) / 500000).toFixed(2) }}</div>
        </div>
        <div>
          <div class="muted">总收益</div>
          <div class="num">${{ ((auth.user?.aff_history_quota || 0) / 500000).toFixed(2) }}</div>
        </div>
        <div>
          <div class="muted">邀请人数</div>
          <div class="num">{{ auth.user?.aff_count || 0 }}</div>
        </div>
      </div>
      <div class="toolbar" style="margin-top:12px">
        <input class="search" style="flex:1" :value="inviteLink" readonly />
        <button class="ghost-btn" @click="copy">复制</button>
        <button class="primary-btn" :disabled="!(auth.user?.aff_quota > 0)" @click="transfer">划转到余额</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from "vue";
import http from "../api/http";
import { useAuthStore } from "../store/auth";

const auth = useAuthStore();
const code = ref("");
const msg = ref("");
const err = ref("");
const inviteLink = computed(() => `${location.origin}/register?aff=${auth.user?.aff_code || ""}`);

onMounted(() => auth.refresh());

async function redeem() {
  msg.value = err.value = "";
  try {
    const { data } = await http.post("/api/user/topup", { key: code.value });
    msg.value = data.message;
    await auth.refresh();
  } catch (e) {
    err.value = e.message;
  }
}
async function transfer() {
  msg.value = err.value = "";
  try {
    const { data } = await http.post("/api/user/aff_transfer", {});
    msg.value = data.message;
    await auth.refresh();
  } catch (e) {
    err.value = e.message;
  }
}
function copy() {
  navigator.clipboard.writeText(inviteLink.value);
  msg.value = "邀请链接已复制";
}
</script>
