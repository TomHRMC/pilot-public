/**
 * VoiceAudioQueue — WatermelonDB model for deferred voice audio uploads
 *
 * Location: apps/mobile/database/models/VoiceAudioQueue.ts
 *
 * Replaces the AsyncStorage-based queue in useDeferredVoiceUpload.ts (FE-B3 stub).
 * This model persists voice audio items across app restarts, surviving force-quit.
 *
 * The SyncOrchestrator.push('voice_audio') processes this queue on reconnect.
 * The public API of useDeferredVoiceUpload.ts is UNCHANGED per design doc §G.7.
 *
 * Per batch-fe-b7-design.md Section A.2.3 and §15.7 deferred voice upload.
 */

import { field } from "@nozbe/watermelondb/decorators";
import { SyncableModel } from "./SyncableModel";

export class VoiceAudioQueue extends SyncableModel {
  static table = "voice_audio_queue";

  /** Voice session ID this audio belongs to */
  @field("session_id") declare sessionId: string;

  /** Local file path (file:// URI) of the captured audio */
  @field("audio_path") declare audioPath: string;

  /** ISO timestamp when audio was captured on device */
  @field("captured_at") declare capturedAt: string;
}
