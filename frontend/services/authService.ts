import axios from "axios";

const BASE = process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/api\/?$/, "") || "http://localhost:8000";
const authApi = axios.create({ baseURL: `${BASE}/api/auth` });

export interface AuthUser {
  id: number;
  username: string;
  email: string;
  full_name: string;
  is_staff: boolean;
  date_joined: string;
}

export interface AuthResponse {
  token: string;
  user: AuthUser;
}

export async function loginUser(username: string, password: string): Promise<AuthResponse> {
  const { data } = await authApi.post<AuthResponse>("/login/", { username, password });
  return data;
}

export async function registerUser(payload: {
  username: string;
  email: string;
  password: string;
  full_name: string;
}): Promise<AuthResponse> {
  const { data } = await authApi.post<AuthResponse>("/register/", payload);
  return data;
}

export async function logoutUser(token: string): Promise<void> {
  await authApi.post("/logout/", {}, { headers: { Authorization: `Token ${token}` } });
}

export async function fetchMe(token: string): Promise<AuthUser> {
  const { data } = await authApi.get<{ user: AuthUser }>("/me/", {
    headers: { Authorization: `Token ${token}` },
  });
  return data.user;
}
