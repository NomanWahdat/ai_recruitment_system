import axios from "axios";

const baseURL = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000/api";

export const apiClient = axios.create({
  baseURL,
  headers: {
    "Content-Type": "application/json",
  },
});

apiClient.interceptors.request.use((config) => {
  if (typeof window !== "undefined") {
    const token = localStorage.getItem("auth_token");
    if (token) {
      config.headers = config.headers || {};
      config.headers.Authorization = `Token ${token}`;
    }
  }
  if (process.env.NODE_ENV !== "production") {
    console.log("[api] request", config.method?.toUpperCase(), config.url);
  }
  return config;
});

apiClient.interceptors.response.use(
  (response) => {
    if (process.env.NODE_ENV !== "production") {
      console.log("[api] response", response.status, response.config.url);
    }
    return response;
  },
  (error) => {
    if (process.env.NODE_ENV !== "production") {
      try {
        const status = error?.response?.status;
        const url = error?.config?.url;
        const data = error?.response?.data;
        console.error("[api] error", status, url, data);
      } catch (e) {
        console.error("[api] error", error?.message || error);
      }
    }
    return Promise.reject(error);
  },
);
