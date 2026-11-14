"use client";

/**
 * useSidebarState — persists sidebar collapsed/expanded state to localStorage
 *
 * Location: apps/web/src/hooks/useSidebarState.ts
 *
 * localStorage key: "pilot.sidebar.collapsed"
 * Default: false (expanded)
 * Both AppSidebar and AuthedLayout consume this hook to share state.
 */

import { useState, useCallback } from "react";

interface SidebarState {
  isSidebarCollapsed: boolean;
  toggleSidebar: () => void;
}

export function useSidebarState(): SidebarState {
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState<boolean>(() => {
    if (typeof window === "undefined") return false;
    try {
      return JSON.parse(
        localStorage.getItem("pilot.sidebar.collapsed") ?? "false",
      );
    } catch {
      return false;
    }
  });

  const toggleSidebar = useCallback(() => {
    setIsSidebarCollapsed((prev) => {
      const next = !prev;
      try {
        localStorage.setItem("pilot.sidebar.collapsed", String(next));
      } catch {
        // localStorage unavailable — continue without persistence
      }
      return next;
    });
  }, []);

  return { isSidebarCollapsed, toggleSidebar };
}
