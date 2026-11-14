/**
 * @pilot/shared-api — barrel export
 *
 * Re-exports all domain modules. Consumers using the package-level
 * import get everything; consumers targeting a specific domain can
 * import directly (e.g., `import { checkApiHealth } from '@pilot/shared-api/health'`).
 */

export * from "./client";
export * from "./health";
export * from "./queryClient";
export * from "./auth";
export * from "./constants";
export * from "./impersonation";
export * from "./problem";
