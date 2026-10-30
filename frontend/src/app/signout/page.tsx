"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { setToken } from "@/lib/session";

/**
 * Signed-out screen. The backend has no logout endpoint (the login token is
 * stateless), so signing out means forgetting the stored token.
 * Clearing it here as well makes /signout work when opened directly.
 */
export default function SignOut() {
  const [done, setDone] = useState(false);

  useEffect(() => {
    setToken(null);
    setDone(true);
  }, []);

  return (
    <section className="login">
      <h1 aria-live="polite">{done ? "You're signed out" : "Signing you out…"}</h1>
      <p className="lede">
        BellAI keeps calling your family on schedule. Sign in again any time to see how they're doing.
      </p>
      <div className="actions">
        <Link href="/login" className="btn primary">Sign in again</Link>
        <Link href="/" className="btn ghost">Back to home</Link>
      </div>
    </section>
  );
}
