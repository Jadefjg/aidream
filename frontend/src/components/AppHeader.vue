<template>
  <header class="header">
    <div class="header-left">
      <Logo />
      <nav class="nav" :class="{ open: menuOpen }" @click="menuOpen = false">
        <router-link to="/">首页</router-link>
        <router-link to="/console">控制台</router-link>
        <router-link to="/gpt-image-2">GPT-Image2</router-link>
        <router-link to="/pricing">模型广场</router-link>
        <a href="https://zcnxuiqg768o.feishu.cn/wiki/MsWbwBaH8ijZUwkVru3cuwscnMd" target="_blank">文档</a>
      </nav>
    </div>
    <div class="header-right">
      <button class="icon-btn desktop-tool" type="button" title="系统公告" aria-label="系统公告" @click="$emit('notice')"><Bell :size="17" /></button>
      <button class="icon-btn desktop-tool" type="button" title="当前为深色主题" aria-label="当前为深色主题"><Moon :size="17" /></button>
      <button class="icon-btn desktop-tool" type="button" title="简体中文" aria-label="简体中文"><Languages :size="17" /></button>
      <div v-if="auth.isLogin" class="dropdown">
        <button class="pill-btn" @click="open = !open">{{ initial }} {{ auth.user.display_name || auth.user.username }}</button>
        <div v-if="open" class="dropdown-menu">
          <router-link to="/console/personal" @click="open = false">个人设置</router-link>
          <router-link to="/console/topup" @click="open = false">钱包充值</router-link>
          <button @click="logout">退出登录</button>
        </div>
      </div>
      <template v-else>
        <router-link class="ghost-btn" to="/login">登录</router-link>
        <router-link class="primary-btn" to="/register">注册</router-link>
      </template>
      <button class="icon-btn menu-toggle" type="button" :aria-expanded="menuOpen" aria-label="切换导航" @click="menuOpen = !menuOpen">
        <X v-if="menuOpen" :size="19" /><Menu v-else :size="19" />
      </button>
    </div>
  </header>
</template>

<script setup>
import { computed, ref } from "vue";
import { Bell, Languages, Menu, Moon, X } from "@lucide/vue";
import { useRouter } from "vue-router";
import Logo from "./Logo.vue";
import { useAuthStore } from "../store/auth";

const auth = useAuthStore();
const router = useRouter();
const open = ref(false);
const menuOpen = ref(false);
const initial = computed(() => (auth.user?.username || "U").slice(0, 1).toUpperCase());
function logout() {
  open.value = false;
  auth.logout();
  router.push("/login");
}
</script>
