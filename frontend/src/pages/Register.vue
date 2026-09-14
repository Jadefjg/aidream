<template>
  <div class="page-shell home">
    <AppHeader />
    <div class="auth-wrap">
      <div class="auth-card">
        <h3>注册</h3>
        <div class="field">
          <label>用户名</label>
          <input class="input plain" v-model="username" placeholder="请输入用户名" />
        </div>
        <div class="field">
          <label>密码</label>
          <input class="input plain" type="password" v-model="password" placeholder="请输入密码" />
        </div>
        <div class="field">
          <label>邮箱（可选）</label>
          <input class="input plain" v-model="email" placeholder="请输入邮箱" />
        </div>
        <div class="field">
          <label>邀请码（可选）</label>
          <input class="input plain" v-model="aff_code" placeholder="邀请码" />
        </div>
        <p v-if="error" class="error">{{ error }}</p>
        <button class="primary-btn full" @click="submit">继续</button>
        <div class="auth-links">已有账户？ <router-link to="/login">登录</router-link></div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { onMounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import AppHeader from "../components/AppHeader.vue";
import http from "../api/http";
import { useAuthStore } from "../store/auth";

const username = ref("");
const password = ref("");
const email = ref("");
const aff_code = ref("");
const error = ref("");
const auth = useAuthStore();
const router = useRouter();
const route = useRoute();

onMounted(() => {
  if (route.query.aff) aff_code.value = String(route.query.aff);
});

async function submit() {
  error.value = "";
  try {
    const { data } = await http.post("/api/user/register", {
      username: username.value,
      password: password.value,
      email: email.value,
      aff_code: aff_code.value,
    });
    auth.setSession(data.data);
    router.push("/console");
  } catch (e) {
    error.value = e.message;
  }
}
</script>
