/**
 * force-dynamic: prevent Next.js from attempting static prerendering of any
 * route during `next build`. All routes in this app require client-side auth
 * (Cognito) and cannot be meaningfully generated at build time.
 *
 * Without this, Next.js tries to SSR-prerender authed pages in isolated worker
 * threads, which creates a separate React module graph. The NotificationQueue
 * context created in providers.tsx is invisible to that worker, causing:
 *   TypeError: (0 , c.useContext) is not a function
 */
export const dynamic = "force-dynamic";

import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import { RootProviders } from "./providers";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Pilot for Trades",
  description: "Electrical contractor operations platform",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
    >
      <body className="min-h-full flex flex-col">
        <RootProviders>{children}</RootProviders>
      </body>
    </html>
  );
}
