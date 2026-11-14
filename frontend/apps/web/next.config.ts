import path from "path";
import type { NextConfig } from "next";

const BACKEND_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";

const nextConfig: NextConfig = {
  /* Standalone output for the Docker image run as the pilot-web ECS Fargate service */
  output: "standalone",

  /**
   * Skip TypeScript type-checking during `next build`.
   *
   * packages/ui contains mobile-only components (24+ files) that import from
   * "react-native". These are stubbed at bundle time by Turbopack resolveAlias
   * and are never executed in the web build, but tsc still type-checks them
   * during the Docker production build and fails on RN-specific style types
   * (flexDirection: string vs FlexDirection, FlatList<T> generics, etc.).
   *
   * TypeScript checking for the web app is enforced separately in CI via:
   *   pnpm --filter web check-types
   * This flag only suppresses the redundant check inside `next build`.
   *
   * Reference: https://nextjs.org/docs/app/api-reference/config/next-config-js/typescript
   */
  typescript: {
    ignoreBuildErrors: true,
  },

  /* Turn on the React Compiler */
  reactCompiler: true,

  /* Tell Next.js to compile our local monorepo packages! */
  transpilePackages: ["@pilot/shared-api", "@pilot/shared-types", "@pilot/ui"],

  /**
   * API proxy: forward all /api/v1/* requests to the FastAPI backend.
   * This lets browser-side fetch('/api/v1/...') work without CORS issues
   * and without hard-coding the backend URL in every hook.
   */
  async rewrites() {
    return [
      {
        source: "/api/v1/:path*",
        destination: `${BACKEND_URL}/api/v1/:path*`,
      },
    ];
  },

  /**
   * Turbopack module aliases: stub out React Native + Expo modules that leak into
   * packages/ui via mobile-specific components (VoiceConfirmTurn, expo-av, etc.).
   *
   * Next.js 16 uses `turbopack.resolveAlias` at the top level.
   * See: https://nextjs.org/docs/app/api-reference/config/next-config-js/turbopack
   */
  turbopack: {
    resolveAlias: {
      // Mobile-only stubs — prevents Turbopack from bundling RN code in web build
      "react-native": "./src/lib/react-native-stub.js",
      "@react-native-async-storage/async-storage":
        "./src/lib/react-native-stub.js",
      "expo-av": "./src/lib/react-native-stub.js",
      "expo-modules-core": "./src/lib/react-native-stub.js",
      "expo-asset": "./src/lib/react-native-stub.js",
    },
    // resolveExtensions ensures Turbopack resolves web-compatible module formats
    // when packages ship both .web.js and .native.js variants
    resolveExtensions: [
      ".web.tsx",
      ".web.ts",
      ".web.jsx",
      ".web.js",
      ".tsx",
      ".ts",
      ".jsx",
      ".js",
      ".json",
    ],
  },

  /**
   * Webpack aliases for the production build (next build uses webpack, not Turbopack).
   *
   * 1. Stub react-native and Expo packages — same stubs as Turbopack above,
   *    but applied to webpack so `next build` doesn't try to bundle mobile code.
   *
   * 2. Pin react and react-dom to a single resolved instance.
   *    pnpm workspace symlinks can cause multiple React copies to be resolved
   *    (one from apps/web/node_modules, one from the workspace root), which
   *    causes "useContext is not a function" / hooks invariant errors at build time.
   */
  webpack(config) {
    const stubPath = path.resolve(__dirname, "src/lib/react-native-stub.js");

    // resolve react/react-dom to their package root directories, not index files.
    // Using path.dirname(require.resolve("react/package.json")) gives webpack the
    // directory, so "react/jsx-runtime", "react/jsx-dev-runtime", etc. all resolve
    // from the same instance.  A file-level alias (require.resolve("react")) only
    // covers "react" exactly — subpath imports resolve elsewhere, creating two instances.
    const reactDir = path.dirname(require.resolve("react/package.json"));
    const reactDomDir = path.dirname(require.resolve("react-dom/package.json"));

    config.resolve.alias = {
      ...(config.resolve.alias as Record<string, unknown>),
      // Mobile-only stubs (webpack production build; Turbopack handles dev)
      "react-native": stubPath,
      "@react-native-async-storage/async-storage": stubPath,
      "expo-av": stubPath,
      "expo-modules-core": stubPath,
      "expo-asset": stubPath,
      // Pin all react/react-dom imports to a single package directory so the
      // SSR bundle doesn't load two copies (one from apps/web, one from packages/ui)
      react: reactDir,
      "react-dom": reactDomDir,
    };

    return config;
  },
};

export default nextConfig;
