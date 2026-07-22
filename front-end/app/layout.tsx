import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { Sidebar } from "@/components/sidebar";
import { ThemeProvider } from "@/components/theme-provider";

// Inter is the reference UI's typeface (see front-end/CLAUDE.md).
const inter = Inter({ subsets: ["latin"], display: "swap" });

export const metadata: Metadata = {
  title: "mmm-os · Data Ingestion & Transformation",
  description:
    "Marketing data ingestion & transformation platform — ingest, map, transform, validate.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={inter.className} suppressHydrationWarning>
      <body>
        <ThemeProvider>
          <div className="flex">
            <Sidebar />
            <main className="h-screen flex-1 overflow-y-auto">
              <div className="mx-auto max-w-7xl px-6 py-5">{children}</div>
            </main>
          </div>
        </ThemeProvider>
      </body>
    </html>
  );
}
