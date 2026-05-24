/**
 * Mode context provider.
 *
 * Reads VITE_NEXUS_MODE from the environment and exposes convenience
 * booleans for conditional rendering throughout the app.
 */

import React, { createContext, useContext, useMemo } from "react";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

type NexusMode = "tracker" | "portfolio";

interface ModeContextValue {
  /** The raw mode string */
  mode: NexusMode;
  /** True when the platform is running in Tracker Mode */
  isTrackerMode: boolean;
  /** True when the platform is running in Portfolio Mode */
  isPortfolioMode: boolean;
}

// ---------------------------------------------------------------------------
// Context
// ---------------------------------------------------------------------------

const ModeContext = createContext<ModeContextValue | undefined>(undefined);

// ---------------------------------------------------------------------------
// Provider
// ---------------------------------------------------------------------------

export function ModeProvider({ children }: { children: React.ReactNode }) {
  const value = useMemo<ModeContextValue>(() => {
    const raw = import.meta.env.VITE_NEXUS_MODE;
    const mode: NexusMode = raw === "portfolio" ? "portfolio" : "tracker";
    return {
      mode,
      isTrackerMode: mode === "tracker",
      isPortfolioMode: mode === "portfolio",
    };
  }, []);

  return <ModeContext.Provider value={value}>{children}</ModeContext.Provider>;
}

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------

export function useMode(): ModeContextValue {
  const ctx = useContext(ModeContext);
  if (ctx === undefined) {
    throw new Error("useMode must be used within a ModeProvider");
  }
  return ctx;
}
