/**
 * WatermelonDB Database Singleton — Pilot Mobile
 *
 * Location: apps/mobile/database/index.ts
 *
 * Exports the singleton WatermelonDB Database instance.
 * All features and hooks import `database` from this module — never create a new
 * Database instance directly.
 *
 * The database is initialized once at app startup (imported by app/_layout.tsx
 * via the SyncProvider). Force-quit recovery runs before the first sync trigger.
 *
 * ── Adapter Strategy ─────────────────────────────────────────────────────────
 * Native (iOS / Android): SQLiteAdapter with JSI mode (expo-sqlite JSI bridge).
 * Web (expo web / localhost:8081): LokiJSAdapter (in-memory, no native SQLite).
 *
 * CRITICAL: Do NOT use a static top-level import for SQLiteAdapter.
 * Metro's web bundler traces static imports unconditionally and will attempt to
 * resolve `@nozbe/watermelondb/adapters/sqlite` → `sqlite-node/Database.js` →
 * `better-sqlite3` (a Node.js native addon) which crashes the Hermes / web
 * bundler.  Instead, we use a dynamic require() inside a Platform.OS branch so
 * the web bundle never includes the SQLite adapter module graph.
 *
 * Per batch-fe-b7-design.md Section A.2.1.
 * Per arch doc §11.2: uses expo-sqlite JSI adapter for native.
 */

import { Platform } from "react-native";
import { Database } from "@nozbe/watermelondb";

import { schema } from "./schema";
import { TimeEntry } from "./models/TimeEntry";
import { Expense } from "./models/Expense";
import { Photo } from "./models/Photo";
import { ChangeOrder } from "./models/ChangeOrder";
import { LotoCheck } from "./models/LotoCheck";
import { JobStatusChange } from "./models/JobStatusChange";
import { JobNote } from "./models/JobNote";
import { VoiceAudioQueue } from "./models/VoiceAudioQueue";
import { InvoiceSignoff } from "./models/InvoiceSignoff";

// ─── Adapter selection (platform-conditional) ─────────────────────────────────
//
// We use require() inside an if/else so Metro's static analyser only includes
// ONE adapter module in each platform bundle:
//   - native bundle  → SQLiteAdapter (resolves expo-sqlite JSI)
//   - web bundle     → LokiJSAdapter (resolves lokijs, no native addons)
//
// eslint-disable-next-line @typescript-eslint/no-explicit-any
let adapter: any;

if (Platform.OS === "web" || __DEV__) {
  // Use LokiJS (in-memory) adapter for:
  //   1. Web (expo web / localhost:8081) — no native SQLite available.
  //   2. ALL dev builds including Expo Go (__DEV__ === true) — Expo Go does NOT
  //      link WatermelonDB's native module (WMDatabaseBridge). This causes:
  //        "NativeModules.WMDatabaseBridge is not defined!"
  //      WMDatabaseBridge requires a custom dev client (expo-dev-client) or a
  //      production EAS build where native modules are properly linked.
  //
  // In dev mode, LokiJS data is in-memory only (lost on reload) — acceptable for
  // development since Pilot's offline-first features target production builds.
  // eslint-disable-next-line @typescript-eslint/no-require-imports
  const LokiJSAdapter = require("@nozbe/watermelondb/adapters/lokijs").default;
  adapter = new LokiJSAdapter({
    schema,
    useWebWorker: false,
    useIncrementalIndexedDB: false,
    onSetUpError: (error: Error) => {
      console.error(
        "[WatermelonDB/LokiJS] Dev/Web adapter setup error:",
        error,
      );
    },
  });
} else {
  // Production native build only (EAS build / expo export).
  // WMDatabaseBridge is properly linked; JSI mode available.
  // Dynamic require() prevents the web bundler from ever walking this import.
  // eslint-disable-next-line @typescript-eslint/no-require-imports
  const SQLiteAdapter = require("@nozbe/watermelondb/adapters/sqlite").default;
  adapter = new SQLiteAdapter({
    schema,
    // JSI mode: enabled in production — WMDatabaseBridge + JSI are both linked.
    // Disabled in test environment (Jest does not support JSI).
    jsi: process.env.NODE_ENV !== "test",
    onSetUpError: (error: Error) => {
      console.error("[WatermelonDB/SQLite] Database setup error:", error);
      throw error;
    },
  });
}

/**
 * The singleton WatermelonDB database instance.
 * Import this throughout the mobile app:
 *   import { database } from '@/database';
 */
export const database = new Database({
  adapter,
  modelClasses: [
    TimeEntry,
    Expense,
    Photo,
    ChangeOrder,
    LotoCheck,
    JobStatusChange,
    JobNote,
    VoiceAudioQueue,
    InvoiceSignoff,
  ],
});

// Re-export model classes for convenience
export {
  TimeEntry,
  Expense,
  Photo,
  ChangeOrder,
  LotoCheck,
  JobStatusChange,
  JobNote,
  VoiceAudioQueue,
  InvoiceSignoff,
};

export type { SyncStatus } from "./models/SyncableModel";
