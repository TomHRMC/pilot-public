import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";
import path from "path";

export default defineConfig({
  plugins: [react()],
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./vitest.setup.ts"],
    include: ["**/__tests__/**/*.test.{ts,tsx}", "**/*.test.{ts,tsx}"],
    exclude: ["node_modules", ".next", "e2e/**"],
  },
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
      "@pilot/ui": path.resolve(__dirname, "../../packages/ui/src"),
      "@pilot/shared-api": path.resolve(
        __dirname,
        "../../packages/shared-api/src",
      ),
      // Stub out React Native + Expo mobile modules for Vitest
      // (same stub used in Turbopack config for builds)
      "react-native": path.resolve(__dirname, "./src/lib/react-native-stub.js"),
      "@react-native-async-storage/async-storage": path.resolve(
        __dirname,
        "./src/lib/react-native-stub.js",
      ),
      "expo-av": path.resolve(__dirname, "./src/lib/react-native-stub.js"),
      "expo-modules-core": path.resolve(
        __dirname,
        "./src/lib/react-native-stub.js",
      ),
      "expo-asset": path.resolve(__dirname, "./src/lib/react-native-stub.js"),
      react: path.resolve(
        __dirname,
        "../../node_modules/.pnpm/react@19.2.4/node_modules/react",
      ),
      "react-dom": path.resolve(
        __dirname,
        "../../node_modules/.pnpm/react-dom@19.2.4_react@19.2.4/node_modules/react-dom",
      ),
    },
  },
});
