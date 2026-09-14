<template>
  <div class="page-shell">
    <AppHeader @notice="notice = true" />
    <div class="console">
      <aside class="sidebar">
        <div class="side-label">聊天</div>
        <router-link class="side-item" to="/console/playground" :class="{ active: is('/console/playground') }"><Bot :size="17" /><span>操练场</span></router-link>
        <router-link class="side-item" to="/console/chat" :class="{ active: is('/console/chat') }"><MessageSquare :size="17" /><span>聊天</span></router-link>
        <div class="side-label">控制台</div>
        <router-link class="side-item" to="/console" :class="{ active: route.path === '/console' }"><LayoutDashboard :size="17" /><span>数据看板</span></router-link>
        <router-link class="side-item" to="/console/token" :class="{ active: is('/console/token') }"><KeyRound :size="17" /><span>API密钥</span></router-link>
        <router-link class="side-item" to="/console/log" :class="{ active: is('/console/log') }"><ScrollText :size="17" /><span>使用日志</span></router-link>
        <div class="side-label">个人中心</div>
        <router-link class="side-item" to="/console/personal" :class="{ active: is('/console/personal') }"><UserRound :size="17" /><span>个人设置</span></router-link>
        <router-link class="side-item" to="/console/topup" :class="{ active: is('/console/topup') }"><WalletCards :size="17" /><span>钱包充值</span></router-link>
        <template v-if="auth.user?.role >= 10">
          <div class="side-label">管理员</div>
          <router-link class="side-item" to="/console/redemption" :class="{ active: is('/console/redemption') }">兑换码</router-link>
          <router-link class="side-item" to="/console/user" :class="{ active: is('/console/user') }">用户管理</router-link>
          <router-link class="side-item" to="/console/channel" :class="{ active: is('/console/channel') }">上游渠道</router-link>
        </template>
      </aside>
      <main class="main">
        <router-view />
      </main>
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
import { Bot, KeyRound, LayoutDashboard, MessageSquare, ScrollText, UserRound, WalletCards } from "@lucide/vue";
import { useRoute } from "vue-router";
import AppHeader from "../components/AppHeader.vue";
import NoticeModal from "../components/NoticeModal.vue";
import { useAuthStore } from "../store/auth";

const route = useRoute();
const auth = useAuthStore();
const notice = ref(false);
function is(path) {
  return route.path.startsWith(path);
}
</script>
