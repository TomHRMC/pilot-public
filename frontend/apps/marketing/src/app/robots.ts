import type { MetadataRoute } from "next";

export const dynamic = "force-static";

export default function robots(): MetadataRoute.Robots {
  return {
    rules: [
      {
        userAgent: "*",
        allow: "/",
        disallow: ["/pricing-preview", "/_next/"],
      },
    ],
    sitemap: "https://pilotfortrades.com/sitemap.xml",
    host: "https://pilotfortrades.com",
  };
}
