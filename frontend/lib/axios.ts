import axios from "axios";

const localHost = typeof window !== "undefined" && window.location.hostname === "localhost" ? "localhost" : "127.0.0.1";
const baseURL = process.env.NEXT_PUBLIC_API_BASE_URL || `http://${localHost}:8000/api`;
let csrfToken: string | undefined;
export const apiClient = axios.create({ baseURL, withCredentials: true });
apiClient.interceptors.request.use(async (config) => {
  if (!["get", "head", "options"].includes(config.method || "get")) {
    if (!csrfToken) {
      const response = await axios.get(baseURL + "/auth/csrf/", { withCredentials: true });
      csrfToken = response.data.csrfToken;
    }
    config.headers.set("X-CSRFToken", csrfToken);
  }
  return config;
});
apiClient.interceptors.response.use(response => {
  if (response.data?.csrfToken) csrfToken = response.data.csrfToken;
  return response;
}, error => {
  if (error.response?.status === 401 && typeof window !== "undefined") {
    window.dispatchEvent(new Event("auth-expired"));
  }
  return Promise.reject(error);
});
export function errorMessage(error: unknown): string {
  if (axios.isAxiosError(error)) {
    const data = error.response?.data;
    return data?.detail || (data ? JSON.stringify(data) : "Cannot reach the API. Check the connection.");
  }
  return error instanceof Error ? error.message : "Request failed.";
}
