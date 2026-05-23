import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Hermes-MiMo Writer — Live Sanitizer Demo",
  description:
    "Multi-agent academic writing pipeline powered by Xiaomi MiMo V2.5 Pro. Live demo of the AI-detector sanitizer agent with token-by-token SSE streaming.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
