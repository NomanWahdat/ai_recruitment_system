import { apiClient } from "@/lib/axios";
export interface AuthUser { id: number; username: string; email: string; full_name: string; is_staff: boolean; date_joined: string }
export interface AuthResponse { user: AuthUser; csrfToken: string }
export async function loginUser(username: string, password: string): Promise<AuthResponse> {
  return (await apiClient.post("/auth/login/", { username, password })).data;
}
export async function registerUser(payload: {username: string; email: string; password: string; full_name: string}): Promise<AuthResponse> {
  return (await apiClient.post("/auth/register/", payload)).data;
}
export async function logoutUser(): Promise<void> { await apiClient.post("/auth/logout/"); }
export async function fetchMe(): Promise<AuthUser> { return (await apiClient.get("/auth/me/")).data.user; }
