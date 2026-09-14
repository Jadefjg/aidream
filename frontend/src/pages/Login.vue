<template>
  <div class="page-shell home">
    <AppHeader @notice="notice = true" />
    <div class="auth-wrap">
      <div>
        <div style="text-align:center;margin-bottom:18px"><Logo /></div>
        <div class="auth-card">
          <h3>登录</h3>
          <div class="field">
            <label>用户名或邮箱</label>
            <div class="input-wrap">
              <span class="lead"><Mail :size="16" /></span>
              <input class="input" v-model="username" placeholder="请输入您的用户名或邮箱地址" />
            </div>
          </div>
          <div class="field">
            <label>密码</label>
            <div class="input-wrap">
              <span class="lead"><LockKeyhole :size="16" /></span>
              <input class="input" :type="show ? 'text' : 'password'" v-model="password" placeholder="请输入您的密码" @keyup.enter="submit" />
              <button class="password-toggle" type="button" :aria-label="show ? '隐藏密码' : '显示密码'" @click="show = !show"><EyeOff v-if="show" :size="16" /><Eye v-else :size="16" /></button>
            </div>
          </div>
          <p v-if="error" class="error">{{ error }}</p>
          <button class="primary-btn full" :disabled="loading" @click="submit">{{ loading ? "登录中..." : "继续" }}</button>
          <div class="auth-links"><span>忘记密码？</span></div>
          <div class="auth-links">没有账户？ <router-link to="/register">注册</router-link></div>
        </div>
      </div>
    </div>
    <footer class="footer">
      <span>© 2026. 版权所有</span>
      <span>设计与开发由 New API</span>
    </footer>
    <NoticeModal :open="notice" @close="notice = false" />
  </div>
</template>

<script setup>
import { ref } from "vue";
import { Eye, EyeOff, LockKeyhole, Mail } from "@lucide/vue";
import { useRoute, useRouter } from "vue-router";
import AppHeader from "../components/AppHeader.vue";
import Logo from "../components/Logo.vue";
import NoticeModal from "../components/NoticeModal.vue";
import http from "../api/http";
import { useAuthStore } from "../store/auth";

const username = ref("FengYu");
const password = ref("Feng1010");
const show = ref(false);
const error = ref("");
const loading = ref(false);
const notice = ref(false);
const auth = useAuthStore();
const router = useRouter();
const route = useRoute();

async function submit() {
  if (loading.value) return;
  error.value = "";
  loading.value = true;
  try {
    const { data } = await http.post("/api/user/login", { username: username.value, password: password.value });
    auth.setSession(data.data);
    router.push(route.query.redirect || "/console");
  } catch (e) {
    error.value = e.message;
  } finally {
    loading.value = false;
  }
}
</script>
