import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";

import { AccessGate } from "@/components/AccessGate";
import { Header } from "@/components/Header";
import { Providers } from "@/components/Providers";
import { Toaster } from "@/components/ui/sonner";

import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Credentialing Tracker",
  description: "Verify clinical staff credentials and track expirations.",
  // Beacon's icon when its file is in public/partners/ (see next.config.ts), otherwise a neutral one.
  icons: { icon: process.env.BEACON_ICON || "/app-icon.svg" },
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html
      lang="en"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
    >
      <body className="flex min-h-full flex-col bg-muted/40 print:bg-white">
        <Providers>
          <AccessGate>
            <Header />
            <main className="mx-auto w-full max-w-6xl flex-1 px-4 py-8 sm:px-6 print:max-w-none print:p-0">{children}</main>
          </AccessGate>
          <Toaster theme="light" position="bottom-right" richColors />
        </Providers>
      </body>
    </html>
  );
}
