import type { NextConfig } from "next";
import createMDX from "@next/mdx";

const withMDX = createMDX({
  // Remark/rehype plugins are applied per-route via next-mdx-remote
  // to avoid Turbopack serialization errors with function objects
  options: {},
});

const nextConfig: NextConfig = {
  /* Static export — marketing site is pure HTML/CSS/JS */
  output: "export",

  /* Required for next/image with static export (no Image Optimization API available) */
  images: { unoptimized: true },

  /* Enable MDX file support (.mdx files can be imported) */
  pageExtensions: ["js", "jsx", "ts", "tsx", "md", "mdx"],

  /* Transpile local monorepo packages */
  transpilePackages: ["@pilot/shared-types"],
};

export default withMDX(nextConfig);
