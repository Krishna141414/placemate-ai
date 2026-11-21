import type { Metadata, Viewport } from "next";
import { Geist_Mono, Inter } from "next/font/google";

import { Providers } from "@/components/providers";
import "./globals.css";

const inter = Inter({ variable: "--font-inter", subsets: ["latin"], display: "swap" });
const geistMono = Geist_Mono({ variable: "--font-geist-mono", subsets: ["latin"], display: "swap" });

export const metadata: Metadata = {
  title: { default: "PlaceMate", template: "%s | PlaceMate" },
  description: "Cited answers from your college's placement documents, eligibility checks, resume matching and a prep plan you approve.",
};

export const viewport: Viewport = {
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#ffffff" },
    { media: "(prefers-color-scheme: dark)", color: "#0b1220" },
  ],
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" suppressHydrationWarning className={`${inter.variable} ${geistMono.variable} antialiased`}>
      <body className="min-h-dvh">
        <a href="#main" className="skip-link">
          Skip to content
        </a>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
