import type { Metadata } from "next";
import { Inter } from "next/font/google";
import Header from "../components/Header";
import Footer from "../components/Footer";
import { SiteModeGate } from "../components/SiteModeGate";
import { getSiteMode } from "../lib/useSiteMode";
import "./globals.css";

const inter = Inter({
  subsets: ["latin"],
  display: "swap",
  variable: "--font-inter",
});

export const metadata: Metadata = {
  metadataBase: new URL("https://pilotfortrades.com"),
  title: {
    default:
      "Pilot for Trades — AI Voice Quoting & Field Operations for Contractors",
    template: "%s | Pilot for Trades",
  },
  description:
    "Turn 10-hour quotes into 5-minute voice estimates. AI-powered quoting, dispatch, invoicing & profitability tracking for electricians, plumbers & HVAC contractors. Try free for 14 days.",
  keywords: [
    "electrical estimating software",
    "contractor quoting software",
    "voice AI quoting",
    "field service management",
    "plumbing estimating software",
    "HVAC estimating software",
  ],
  openGraph: {
    type: "website",
    siteName: "Pilot for Trades",
    locale: "en_US",
    images: [
      {
        url: "/og-default.png",
        width: 1200,
        height: 630,
        alt: "Pilot for Trades — AI Voice Quoting for Contractors",
      },
    ],
  },
  twitter: {
    card: "summary_large_image",
    site: "@pilotfortrades",
  },
  robots: {
    index: true,
    follow: true,
    googleBot: { index: true, follow: true },
  },
};

export default async function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  const { mode } = await getSiteMode();

  return (
    <html lang="en" className={`h-full antialiased ${inter.variable}`}>
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link
          rel="preconnect"
          href="https://fonts.gstatic.com"
          crossOrigin="anonymous"
        />
      </head>
      <body className="min-h-full flex flex-col">
        <SiteModeGate>
          <Header siteMode={mode} />
          <main id="main-content" className="flex-1 pt-16">
            {children}
          </main>
          <Footer siteMode={mode} />
        </SiteModeGate>
      </body>
    </html>
  );
}
