import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";
import path from "path";

export default defineConfig({
  plugins: [react()],
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./vitest.setup.ts"],
    include: ["src/**/*.test.{ts,tsx}"],
    exclude: ["node_modules", "dist"],
    server: {
      deps: {
        inline: ["react", "react-dom"],
      },
    },
  },
  resolve: {
    dedupe: ["react", "react-dom"],
    alias: {
      // Proper RN mock with DOM equivalents for unit testing
      "react-native": path.resolve(__dirname, "./__mocks__/react-native.tsx"),
      "@react-native-async-storage/async-storage": path.resolve(
        __dirname,
        "../../apps/web/src/lib/react-native-stub.js",
      ),
      "expo-av": path.resolve(
        __dirname,
        "../../apps/web/src/lib/react-native-stub.js",
      ),
      // MFA-WIRE-1 Part C: mobile wizard native deps — stubbed for vitest
      "react-native-svg": path.resolve(
        __dirname,
        "./__mocks__/expo-native-stubs.tsx",
      ),
      "expo-haptics": path.resolve(
        __dirname,
        "./__mocks__/expo-native-stubs.tsx",
      ),
      "expo-clipboard": path.resolve(
        __dirname,
        "./__mocks__/expo-native-stubs.tsx",
      ),
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
