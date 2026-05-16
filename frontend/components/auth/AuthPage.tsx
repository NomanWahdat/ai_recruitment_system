"use client";

import { useState } from "react";
import { SignInForm } from "./SignInForm";
import { SignUpForm } from "./SignUpForm";

export function AuthPage() {
  const [mode, setMode] = useState<"signin" | "signup">("signin");

  const features = [
    {
      icon: "📄",
      title: "Smart CV Extraction",
      description: "AI-powered extraction of candidate data from resumes",
    },
    {
      icon: "🤖",
      title: "AI-Powered Analysis",
      description: "Automatically analyze skills, experience, and match scores",
    },
    {
      icon: "🎯",
      title: "Smart Matching",
      description: "Match candidates with job requirements in seconds",
    },
    {
      icon: "📊",
      title: "Advanced Rankings",
      description: "Rank candidates based on AI analysis and job fit",
    },
  ];

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-blue-900 to-slate-900">
      {/* Background decoration */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="absolute -top-40 -right-40 w-80 h-80 bg-blue-500/10 rounded-full blur-3xl"></div>
        <div className="absolute -bottom-40 -left-40 w-80 h-80 bg-blue-500/10 rounded-full blur-3xl"></div>
      </div>

      <div className="relative min-h-screen flex flex-col lg:flex-row items-center justify-center px-4 py-8 lg:px-20">
        {/* Left side - Features & Info */}
        <div className="w-full lg:w-1/2 mb-8 lg:mb-0 lg:pr-12">
          <div className="space-y-8">
            <div>
              <div className="inline-block rounded-xl bg-blue-500/20 backdrop-blur-sm px-4 py-2 border border-blue-400/30">
                <span className="text-sm font-semibold text-blue-300">Next Generation Recruitment</span>
              </div>
              <h1 className="mt-6 text-5xl lg:text-6xl font-bold text-white leading-tight">
                AI Recruitment <span className="text-blue-400">System</span>
              </h1>
              <p className="mt-4 text-xl text-slate-300">
                Transform your hiring process with intelligent candidate screening and matching powered by advanced AI.
              </p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {features.map((feature, idx) => (
                <div
                  key={idx}
                  className="rounded-xl bg-white/5 backdrop-blur-sm border border-white/10 p-4 hover:border-blue-400/50 transition"
                >
                  <div className="text-3xl mb-2">{feature.icon}</div>
                  <h3 className="font-semibold text-white text-sm">{feature.title}</h3>
                  <p className="text-slate-400 text-xs mt-1">{feature.description}</p>
                </div>
              ))}
            </div>

            <div className="grid grid-cols-3 gap-4 pt-4">
              <div className="rounded-lg bg-blue-500/10 p-4 text-center">
                <div className="text-2xl font-bold text-blue-400">100%</div>
                <div className="text-xs text-slate-400 mt-1">Automated</div>
              </div>
              <div className="rounded-lg bg-blue-500/10 p-4 text-center">
                <div className="text-2xl font-bold text-blue-400">Real-time</div>
                <div className="text-xs text-slate-400 mt-1">Results</div>
              </div>
              <div className="rounded-lg bg-blue-500/10 p-4 text-center">
                <div className="text-2xl font-bold text-blue-400">AI-Powered</div>
                <div className="text-xs text-slate-400 mt-1">Insights</div>
              </div>
            </div>
          </div>
        </div>

        {/* Right side - Auth Form */}
        <div className="w-full lg:w-1/2 lg:max-w-md">
          <div className="rounded-2xl border border-white/10 bg-white/5 backdrop-blur-md p-8 shadow-2xl">
            <div className="space-y-8">
              {mode === "signin" ? (
                <SignInForm onSwitch={() => setMode("signup")} />
              ) : (
                <SignUpForm onSwitch={() => setMode("signin")} />
              )}
            </div>

            <div className="mt-8 pt-6 border-t border-white/10">
              <p className="text-center text-xs text-slate-400">
                By continuing, you agree to our Terms of Service and Privacy Policy
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
