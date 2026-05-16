"use client";

import { createContext, useContext, useMemo, useState, type ReactNode } from "react";

type ToastType = "success" | "error" | "info";

type ToastMessage = {
  id: number;
  title: string;
  description?: string;
  type: ToastType;
};

type ToastContextValue = {
  pushToast: (toast: Omit<ToastMessage, "id">) => void;
};

const ToastContext = createContext<ToastContextValue | null>(null);

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<ToastMessage[]>([]);

  const pushToast = (toast: Omit<ToastMessage, "id">) => {
    const id = Date.now() + Math.floor(Math.random() * 1000);
    setToasts((current) => [...current, { ...toast, id }]);
    window.setTimeout(() => {
      setToasts((current) => current.filter((item) => item.id !== id));
    }, 3500);
  };

  const value = useMemo(() => ({ pushToast }), []);

  return (
    <ToastContext.Provider value={value}>
      {children}
      <div className="fixed right-4 top-4 z-[60] flex w-full max-w-sm flex-col gap-3 px-2">
        {toasts.map((toast) => (
          <div
            key={toast.id}
            className={`rounded-2xl border p-4 shadow-2xl backdrop-blur ${
              toast.type === "success"
                ? "border-emerald-200 bg-emerald-50 text-emerald-900"
                : toast.type === "error"
                  ? "border-rose-200 bg-rose-50 text-rose-900"
                  : "border-blue-200 bg-blue-50 text-blue-900"
            }`}
          >
            <div className="text-sm font-semibold">{toast.title}</div>
            {toast.description ? <div className="mt-1 text-sm opacity-90">{toast.description}</div> : null}
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}

export function useToast() {
  const context = useContext(ToastContext);
  if (!context) {
    throw new Error("useToast must be used within ToastProvider");
  }
  return context;
}
