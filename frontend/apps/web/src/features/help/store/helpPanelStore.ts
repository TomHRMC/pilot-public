/**
 * helpPanelStore — Zustand — FE-B16
 *
 * Location: apps/web/src/features/help/store/helpPanelStore.ts
 *
 * Global singleton panel state for the HelpDrawer.
 * Any entry point (nav "?" icon, contextual anchor, settings CTA) shares
 * this single store. Not persisted — ephemeral UI state.
 */

import { create } from "zustand";
import type { HelpContextPayload } from "@pilot/ui";
import type { HelpPanelView } from "../types";

interface HelpPanelStoreState {
  isOpen: boolean;
  view: HelpPanelView;
  context: HelpContextPayload | null;
  activeSessionId: string | null;

  // Actions
  open: () => void;
  close: () => void;
  toggle: () => void;
  openWithContext: (payload: HelpContextPayload) => void;
  clearContext: () => void;
  setActiveSession: (id: string | null) => void;
  setView: (view: HelpPanelView) => void;
}

export const useHelpPanel = create<HelpPanelStoreState>((set) => ({
  isOpen: false,
  view: "chat",
  context: null,
  activeSessionId: null,

  open: () => set({ isOpen: true }),
  close: () => set({ isOpen: false }),
  toggle: () => set((state) => ({ isOpen: !state.isOpen })),

  openWithContext: (payload: HelpContextPayload) =>
    set({ isOpen: true, view: "chat", context: payload }),

  clearContext: () => set({ context: null }),

  setActiveSession: (id: string | null) => set({ activeSessionId: id }),

  setView: (view: HelpPanelView) => set({ view }),
}));
