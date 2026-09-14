import axios from "axios";
import { useAuthStore } from "../store/auth";

const http = axios.create({ baseURL: "" });

http.interceptors.request.use((config) => {
  const auth = useAuthStore();
  if (auth.accessToken) {
    config.headers.Authorization = `Bearer ${auth.accessToken}`;
  }
  return config;
});

http.interceptors.response.use(
  (res) => res,
  (err) => {
    const msg = err.response?.data?.message || err.response?.data?.detail || err.response?.data?.error?.message || err.message;
    if (err.response?.status === 401 && !err.config?.url?.includes("/api/user/login")) {
      const auth = useAuthStore();
      auth.logout();
    }
    return Promise.reject(new Error(typeof msg === "string" ? msg : "请求失败"));
  }
);

export default http;
