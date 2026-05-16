import type { Metadata } from "next";
import { AuthGate } from "@/components/layout/AuthGate";
import { Providers } from "./providers";
import "@/styles/globals.css";
import type { ReactNode } from "react";

export const metadata: Metadata = {
  title: "AI Recruitment System",
  description: "Professional SaaS frontend foundation for AI recruitment workflows.",
};

export default function RootLayout({ children }: Readonly<{ children: ReactNode }>) {
  return (
    <html lang="en">
      <body>
        <Providers>
          <AuthGate>{children}</AuthGate>
        </Providers>
      </body>
    </html>
  );
}
