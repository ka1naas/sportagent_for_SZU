import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Campus Fitness Scheduler",
  description: "校园智能健身规划助手前端 MVP",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="zh-CN">
      <body>{children}</body>
    </html>
  );
}
