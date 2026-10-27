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
export function validationMessage(value: unknown): string {
  if (typeof value === "string") return value;
  if (Array.isArray(value)) return value.map(validationMessage).filter(Boolean).join(" ");
  if (value && typeof value === "object") return Object.entries(value).map(([key,item]) => {
    const text = validationMessage(item);
    return key === "detail" || key === "non_field_errors" ? text : `${key.replaceAll("_", " ")}: ${text}`;
  }).join(" ");
  return "";
}
export function errorMessage(error: unknown): string {
  if (axios.isAxiosError(error)) return validationMessage(error.response?.data) || "We couldn't reach the service. Please check your connection and try again.";
  return error instanceof Error ? error.message : "Something went wrong. Please try again.";
}
