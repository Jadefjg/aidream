import { createRouter, createWebHistory } from "vue-router";
import { useAuthStore } from "../store/auth";

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: "/", component: () => import("../pages/Home.vue") },
    { path: "/login", component: () => import("../pages/Login.vue") },
    { path: "/register", component: () => import("../pages/Register.vue") },
    { path: "/pricing", component: () => import("../pages/Pricing.vue") },
    { path: "/gpt-image-2", component: () => import("../pages/ImageStudio.vue") },
    {
      path: "/console",
      component: () => import("../layouts/ConsoleLayout.vue"),
      meta: { auth: true },
      children: [
        { path: "", component: () => import("../pages/Dashboard.vue") },
        { path: "token", component: () => import("../pages/Tokens.vue") },
        { path: "log", component: () => import("../pages/Logs.vue") },
        { path: "personal", component: () => import("../pages/Personal.vue") },
        { path: "topup", component: () => import("../pages/Topup.vue") },
        { path: "playground", component: () => import("../pages/Playground.vue") },
        { path: "chat", component: () => import("../pages/Chat.vue") },
        { path: "redemption", component: () => import("../pages/AdminRedemption.vue"), meta: { admin: true } },
        { path: "user", component: () => import("../pages/AdminUsers.vue"), meta: { admin: true } },
        { path: "channel", component: () => import("../pages/AdminChannels.vue"), meta: { admin: true } },
      ],
    },
    { path: "/:pathMatch(.*)*", redirect: "/" },
  ],
});

router.beforeEach((to) => {
  const auth = useAuthStore();
  if (to.meta.auth && !auth.isLogin) {
    return { path: "/login", query: { redirect: to.fullPath } };
  }
  if (to.meta.admin && (auth.user?.role || 0) < 10) {
    return { path: "/console" };
  }
});

export default router;
