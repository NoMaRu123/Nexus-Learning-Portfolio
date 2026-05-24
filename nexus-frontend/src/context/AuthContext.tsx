/**
 * Authentication context provider.
 *
 * Manages JWT storage in localStorage, exposes login / register / logout
 * helpers, and decodes basic user info from the token payload.
 */

import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";
import * as authApi from "@/services/api";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface DecodedUser {
  /** user_id extracted from the JWT `sub` claim */
  id: string;
}

interface AuthContextValue {
  /** Raw JWT string, or null when unauthenticated */
  token: string | null;
  /** Decoded user info from the JWT, or null */
  user: DecodedUser | null;
  /** Whether the user holds a valid (non-expired) token */
  isAuthenticated: boolean;
  /** Authenticate with email + password, stores token on success */
  login: (email: string, password: string) => Promise<void>;
  /** Register a new account and auto-login on success */
  register: (email: string, password: string) => Promise<void>;
  /** Clear token from state and localStorage */
  logout: () => void;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const TOKEN_KEY = "nexus_token";

/**
 * Decode the payload section of a JWT without verifying the signature.
 * Returns null if the token is malformed or expired.
 */
function decodeToken(token: string): DecodedUser | null {
  try {
    const payload = JSON.parse(atob(token.split(".")[1]));

    // Check expiry
    if (payload.exp && payload.exp * 1000 < Date.now()) {
      return null;
    }

    return { id: payload.sub };
  } catch {
    return null;
  }
}

// ---------------------------------------------------------------------------
// Context
// ---------------------------------------------------------------------------

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

// ---------------------------------------------------------------------------
// Provider
// ---------------------------------------------------------------------------

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [token, setToken] = useState<string | null>(() =>
    localStorage.getItem(TOKEN_KEY),
  );

  const user = useMemo<DecodedUser | null>(
    () => (token ? decodeToken(token) : null),
    [token],
  );

  const isAuthenticated = user !== null;

  // Sync token → localStorage
  useEffect(() => {
    if (token) {
      localStorage.setItem(TOKEN_KEY, token);
    } else {
      localStorage.removeItem(TOKEN_KEY);
    }
  }, [token]);

  const login = useCallback(async (email: string, password: string) => {
    const response = await authApi.login(email, password);
    setToken(response.access_token);
  }, []);

  const register = useCallback(async (email: string, password: string) => {
    await authApi.register(email, password);
    // Auto-login after successful registration
    const response = await authApi.login(email, password);
    setToken(response.access_token);
  }, []);

  const logout = useCallback(() => {
    setToken(null);
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({ token, user, isAuthenticated, login, register, logout }),
    [token, user, isAuthenticated, login, register, logout],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (ctx === undefined) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return ctx;
}
