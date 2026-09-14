<template>
  <div>
    <div class="profile-hero">
      <div class="avatar">{{ (auth.user?.username || "U").slice(0, 2).toUpperCase() }}</div>
      <div>
        <h2 style="margin:0">{{ auth.user?.display_name }}</h2>
        <p class="muted">普通用户 · ID: {{ auth.user?.id }}</p>
      </div>
    </div>
    <div class="card" style="margin-top:16px">
      <div class="num">${{ (auth.user?.balance_usd || 0).toFixed(2) }} <span class="badge" style="background:#7f1d1d;color:#fecaca">当前余额</span></div>
      <div class="stat"><span class="muted">历史消耗</span><b style="margin-left:auto">${{ (auth.user?.used_usd || 0).toFixed(2) }}</b></div>
      <div class="stat"><span class="muted">请求次数</span><b style="margin-left:auto">{{ auth.user?.request_count }}</b></div>
      <div class="stat"><span class="muted">用户分组</span><b style="margin-left:auto">{{ auth.user?.group }}</b></div>
    </div>
    <div class="card">
      <div class="card-title">账户管理</div>
      <div class="tabs">
        <span :class="{ active: tab === 'bind' }" @click="tab = 'bind'">账户绑定</span>
        <span :class="{ active: tab === 'sec' }" @click="tab = 'sec'">安全设置</span>
      </div>
      <div v-if="tab === 'bind'">
        <div class="field"><label>邮箱</label><input class="input plain" v-model="form.email" /></div>
        <button class="primary-btn" @click="save">保存绑定</button>
        <p v-if="msg" class="ok">{{ msg }}</p>
        <div class="stat"><span>微信</span><span class="muted" style="margin-left:auto">未启用</span></div>
        <div class="stat"><span>GitHub</span><span class="muted" style="margin-left:auto">未启用</span></div>
      </div>
      <div v-else>
        <div class="field"><label>显示名</label><input class="input plain" v-model="form.display_name" /></div>
        <div class="field"><label>邮箱</label><input class="input plain" v-model="form.email" /></div>
        <div class="field"><label>原密码</label><input class="input plain" type="password" v-model="form.original_password" /></div>
        <div class="field"><label>新密码</label><input class="input plain" type="password" v-model="form.password" /></div>
        <p v-if="msg" class="ok">{{ msg }}</p>
        <button class="primary-btn" @click="save">保存设置</button>
        <button class="ghost-btn" style="margin-left:8px" @click="logout">退出登录</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from "vue";
import { useRouter } from "vue-router";
import http from "../api/http";
import { useAuthStore } from "../store/auth";

const auth = useAuthStore();
const router = useRouter();
const tab = ref("bind");
const msg = ref("");
const form = reactive({ display_name: "", email: "", password: "", original_password: "" });

onMounted(() => {
  form.display_name = auth.user?.display_name || "";
  form.email = auth.user?.email || "";
});

async function save() {
  const payload = { display_name: form.display_name, email: form.email };
  if (form.password) {
    payload.password = form.password;
    payload.original_password = form.original_password;
  }
  const { data } = await http.put("/api/user/self", payload);
  auth.user = data.data;
  localStorage.setItem("user", JSON.stringify(data.data));
  msg.value = "保存成功";
  form.password = "";
  form.original_password = "";
}
function logout() {
  auth.logout();
  router.push("/login");
}
</script>
