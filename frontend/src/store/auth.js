import { defineStore } from "pinia";
import http from "../api/http";

export const useAuthStore = defineStore("auth", {
  state: () => ({
    accessToken: localStorage.getItem("access_token") || "",
    user: JSON.parse(localStorage.getItem("user") || "null"),
  }),
  getters: {
    isLogin: (s) => Boolean(s.accessToken && s.user),
  },
  actions: {
    setSession(data) {
      this.accessToken = data.access_token;
      this.user = data.user || data;
      localStorage.setItem("access_token", this.accessToken);
      localStorage.setItem("user", JSON.stringify(this.user));
    },
    logout() {
      this.accessToken = "";
      this.user = null;
      localStorage.removeItem("access_token");
      localStorage.removeItem("user");
    },
    async refresh() {
      if (!this.accessToken) return;
      const { data } = await http.get("/api/user/self");
      this.user = data.data;
      localStorage.setItem("user", JSON.stringify(this.user));
    },
  },
});
