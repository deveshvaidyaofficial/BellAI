"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { api, ApiError } from "@/lib/api";
import { getToken, setToken } from "@/lib/session";
import type { AuthSession, Caregiver } from "@/lib/types";

interface Auth {
  caregiver: Caregiver | null;
  signIn: (session: AuthSession) => void;
  signOut: () => void;
}

const AuthContext = createContext<Auth>({ caregiver: null, signIn: () => {}, signOut: () => {} });
export const useAuth = () => useContext(AuthContext);

const PUBLIC_PATHS = ["/login"];

/**
 * Keeps the signed-in caregiver and sends everyone else to /login.
 * The API doesn't require login yet; this only gates the screens.
 */
export function AuthProvider({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  // undefined = still checking the stored token
  const [caregiver, setCaregiver] = useState<Caregiver | null | undefined>(undefined);
  const isPublic = PUBLIC_PATHS.includes(pathname);

  useEffect(() => {
    if (!getToken()) return setCaregiver(null);
    api
      .me()
      .then(setCaregiver)
      .catch((e) => {
        if (e instanceof ApiError && e.status === 401) setToken(null); // expired or invalid
        setCaregiver(null);
      });
  }, []);

  useEffect(() => {
    if (caregiver === null && !isPublic) router.replace(`/login?next=${encodeURIComponent(pathname)}`);
  }, [caregiver, isPublic, pathname, router]);

  const signIn = useCallback((session: AuthSession) => {
    setToken(session.token);
    setCaregiver(session.caregiver);
  }, []);

  const signOut = useCallback(() => {
    setToken(null);
    setCaregiver(null);
  }, []);

  const ready = isPublic || caregiver;
  return (
    <AuthContext.Provider value={{ caregiver: caregiver ?? null, signIn, signOut }}>
      <header className="nav">
        <Link href="/" className="brand">BellAI</Link>
        {caregiver && (
          <nav>
            <Link href="/">Today</Link>
            <Link href="/elders">People</Link>
            <Link href="/calls">Calls</Link>
            <Link href="/tasks/new" className="btn primary">Add reminder</Link>
            <button className="btn ghost" onClick={signOut} title={caregiver.phone ?? caregiver.email ?? ""}>
              Sign out
            </button>
          </nav>
        )}
      </header>
      <main>{ready ? children : <p className="muted">Loading…</p>}</main>
    </AuthContext.Provider>
  );
}
