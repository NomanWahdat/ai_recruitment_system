"use client";

import { useState } from "react";
import type { FormEvent } from "react";
import { useAuth } from "@/contexts/AuthContext";

export function SignInForm({ onSwitch }: { onSwitch: () => void }) {
  const { login } = useAuth();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await login(username, password);
    } catch (err: any) {
      setError(err?.response?.data?.detail || "Login failed. Check your credentials.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="w-full space-y-8">
      <div className="text-center">
        <div className="inline-block rounded-xl bg-gradient-to-br from-blue-100 to-blue-50 px-4 py-2">
          <span className="text-xs font-bold uppercase tracking-widest text-blue-700">🚀 AI Recruitment</span>
        </div>
        <h1 className="mt-4 text-4xl font-bold tracking-tight text-slate-900">Welcome back</h1>
        <p className="mt-2 text-base text-slate-600">Continue to manage your recruitment workflow</p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-5">
        {error && (
          <div className="rounded-xl bg-rose-50 px-4 py-3 text-sm font-medium text-rose-700 ring-1 ring-rose-200">
            {error}
          </div>
        )}

        <div>
          <label className="block text-sm font-semibold text-slate-700">Username or Email</label>
          <input
            required
            type="text"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            className="mt-2 w-full rounded-xl border border-slate-300 bg-slate-50 px-4 py-3 text-sm outline-none transition placeholder:text-slate-400 focus:border-blue-500 focus:bg-white focus:ring-2 focus:ring-blue-200"
            placeholder="Enter your username or email"
          />
        </div>

        <div>
          <label className="block text-sm font-semibold text-slate-700">Password</label>
          <input
            required
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="mt-2 w-full rounded-xl border border-slate-300 bg-slate-50 px-4 py-3 text-sm outline-none transition placeholder:text-slate-400 focus:border-blue-500 focus:bg-white focus:ring-2 focus:ring-blue-200"
            placeholder="Enter your password"
          />
        </div>

        <button
          type="submit"
          disabled={loading}
          className="w-full rounded-xl bg-gradient-to-r from-blue-600 to-blue-700 py-3 text-sm font-semibold text-white shadow-lg transition hover:from-blue-700 hover:to-blue-800 hover:shadow-xl disabled:opacity-50"
        >
          {loading ? "Signing in..." : "Sign In"}
        </button>
      </form>

      <div className="relative">
        <div className="absolute inset-0 flex items-center">
          <div className="w-full border-t border-slate-300"></div>
        </div>
        <div className="relative flex justify-center text-sm">
          <span className="bg-white px-2 text-slate-500">New to AI Recruitment?</span>
        </div>
      </div>

      <button
        onClick={onSwitch}
        className="w-full rounded-xl border-2 border-slate-200 bg-slate-50 py-3 text-sm font-semibold text-slate-700 transition hover:border-blue-300 hover:bg-blue-50"
      >
        Create an account
      </button>
    </div>
  );
}
