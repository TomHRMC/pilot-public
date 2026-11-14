/**
 * Metro bundler configuration for pnpm monorepo
 *
 * Location: apps/mobile/metro.config.js
 *
 * Fixes two pnpm + Metro issues:
 *
 * 1. Module resolution: Metro can't follow pnpm's symlink structure by default.
 *    watchFolders + nodeModulesPaths lets it find workspace packages.
 *
 * 2. Duplicate React: pnpm creates isolated node_modules per package.
 *    resolveRequest re-anchors all singleton package imports to resolve
 *    from apps/mobile so only one copy of React/RN is ever bundled.
 *
 * 3. Test/mock isolation: MSW (msw/node) calls setupServer() which polyfills
 *    PerformanceEntry and crashes the iOS Hermes engine. The blockList below
 *    prevents Metro from ever walking into __tests__/, mocks/, or any
 *    *.test.* / *.spec.* file so msw is never accidentally bundled into the
 *    production or development Metro graph.
 */

const { getDefaultConfig } = require("expo/metro-config");
// metro-config ships exclusionList under the "private/*" export map entry.
// The public path is metro-config/private/defaults/exclusionList (maps to
// src/defaults/exclusionList.js internally).  CommonJS require() returns
// { default: fn }, so we destructure accordingly.
const {
  default: exclusionList,
} = require("metro-config/private/defaults/exclusionList");
const path = require("path");

// Monorepo root (two directories up from apps/mobile)
const monorepoRoot = path.resolve(__dirname, "../..");
const frontendRoot = path.resolve(__dirname, "..");

// ─── Test/mock file block list ────────────────────────────────────────────────
// These regexes are matched against ABSOLUTE paths Metro resolves during
// dependency tracing.  Any path matching is silently excluded from the bundle.
//
// 1. __tests__/ directories — contain Jest integration tests that import msw/node.
// 2. mocks/server.ts ONLY — this file calls setupServer() from msw/node which
//    polyfills PerformanceEntry and crashes the iOS Hermes JIT engine.
//    The mocks/handlers/ files use the main msw package (browser-safe) and
//    are intentionally allowed through so the MSW browser service worker
//    (mocks/browser.ts) can bundle them for web dev with EXPO_PUBLIC_USE_MOCK_AUTH.
// 3. *.test.{ts,tsx,js,jsx,mjs} / *.spec.* — test files by extension.
// 4. jest.setup.ts — Jest bootstrap; irrelevant to Metro.
const mobileMocksServerFile = path.resolve(__dirname, "mocks", "server.ts");
const TEST_BLOCK_LIST = exclusionList([
  // Any path segment named __tests__
  /.*\/__tests__\/.*/,
  // ONLY mocks/server.ts — the file that imports msw/node (Node.js only, crashes Hermes)
  // mocks/handlers/** are browser-safe and allowed through for the MSW browser worker
  new RegExp(`^${mobileMocksServerFile.replace(/[/\\]/g, "[\\\\/]")}$`),
  // Test and spec files by extension (catches files outside __tests__ dirs)
  /.*\.(test|spec)\.(ts|tsx|js|jsx|mjs)$/,
  // Jest setup file
  /.*\/jest\.setup\.(ts|js)$/,
]);

const config = getDefaultConfig(__dirname);

// Apply the block list — Metro will never walk into test/mock files
config.resolver.blockList = TEST_BLOCK_LIST;

// Watch the entire monorepo so Metro can find packages in packages/
config.watchFolders = [monorepoRoot];

// Add node_modules paths to walk up when resolving modules
config.resolver.nodeModulesPaths = [
  path.resolve(__dirname, "node_modules"),
  path.resolve(frontendRoot, "node_modules"),
  path.resolve(monorepoRoot, "node_modules"),
];

// Enable symlink resolution for pnpm's virtual store layout
config.resolver.unstable_enableSymlinks = true;

// Singleton packages: must resolve to ONE copy to prevent duplicate-module crashes.
// Any monorepo package importing these gets redirected to apps/mobile's copy.
//
// @tanstack/react-query: if packages/shared-api and apps/mobile each resolve a
//   separate copy, the QueryClient created in _layout.tsx (from copy A) won't be
//   found by useQueryClient() in hooks imported via packages/shared-api (copy B),
//   causing: "Error: No QueryClient set, use QueryClientProvider to set one"
//
// react-native-svg: pnpm symlinks can cause packages/ui and apps/mobile to each
//   resolve a separate copy of react-native-svg.  React Native's view registry
//   allows each native component name to be registered exactly once; two copies
//   both calling registerComponent("RNSVGCircle", ...) crashes with:
//   "Invariant Violation: Tried to register two views with the same name RNSVGCircle"
const SINGLETON_PACKAGES = [
  "react",
  "react-native",
  "react-dom",
  "react-native-safe-area-context",
  "react-native-screens",
  "@tanstack/react-query",
  "react-native-svg",
];

// Fake origin inside apps/mobile — used to re-anchor module resolution.
// When Metro resolves a request "from" this path, it will find node_modules
// in apps/mobile first, ignoring any symlinked copies in packages/ui or
// packages/shared-api.
const MOBILE_ANCHOR = path.resolve(__dirname, "package.json");

// Native-only packages that must not be evaluated on web.
//
// These packages call createPermissionHook() or other native-only APIs from
// expo-modules-core at module factory load time (before any component renders).
// On web, expo-modules-core exposes a different surface and createPermissionHook
// is undefined, crashing the page immediately on import.
//
// Metro's resolveRequest returns { type: "empty" } for web — an empty module
// stub — which prevents the crash.  Components that use these packages must
// guard their usage with Platform.OS checks so they never call the stub APIs.
//
// Rule: any Expo SDK package that ships native permission hooks OR native-only
// bindings with no web fallback must be listed here.
const NATIVE_ONLY_PACKAGES = [
  // ── Expo packages with no web implementation ────────────────────────────
  "expo-notifications", // ServerRegistrationModule.web.js crashes on localStorage
  "expo-secure-store", // KeychainServices — no web equivalent
  "expo-location", // createPermissionHook — no web GPS API in expo-modules-core
  "expo-image-picker", // createPermissionHook — no web camera/library in expo-modules-core
  "expo-haptics", // Taptic Engine — no web equivalent
  "expo-file-system", // Native FS bindings — no web equivalent
  "expo-sharing", // Share sheet — no web equivalent
  "expo-av", // AVFoundation / ExoPlayer — no web equivalent
  // ── WatermelonDB Node/SQLite internals ──────────────────────────────────
  // Belt-and-suspenders alongside the dynamic require() in database/index.ts.
  // If any transitive import pulls in the sqlite adapter on web, this intercepts.
  "better-sqlite3",
  "@nozbe/watermelondb/adapters/sqlite/sqlite-node",
];

config.resolver.resolveRequest = (context, moduleName, platform) => {
  // Block native-only packages on web — return an empty module stub
  if (
    platform === "web" &&
    NATIVE_ONLY_PACKAGES.some(
      (pkg) => moduleName === pkg || moduleName.startsWith(`${pkg}/`),
    )
  ) {
    return {
      type: "empty",
    };
  }

  const isSingleton = SINGLETON_PACKAGES.some(
    (pkg) => moduleName === pkg || moduleName.startsWith(`${pkg}/`),
  );

  if (isSingleton) {
    // Re-anchor: resolve as if the import originated from apps/mobile
    return context.resolveRequest(
      { ...context, originModulePath: MOBILE_ANCHOR },
      moduleName,
      platform,
    );
  }

  // Default resolution for all other modules
  return context.resolveRequest(context, moduleName, platform);
};

module.exports = config;
