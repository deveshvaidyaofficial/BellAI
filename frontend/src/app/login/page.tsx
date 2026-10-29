"use client";

import Script from "next/script";
import { useRouter, useSearchParams } from "next/navigation";
import { FormEvent, Suspense, useCallback, useEffect, useRef, useState } from "react";
import { useAuth } from "@/components/AuthProvider";
import { api, ApiError, errorText } from "@/lib/api";
import { isValidPhone, normalizePhone } from "@/lib/format";
import type { AuthSession } from "@/lib/types";

const GOOGLE_CLIENT_ID = process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID ?? "";
const RESEND_SECONDS = 30;

// Minimal typing for Google Identity Services (https://developers.google.com/identity/gsi/web).
declare global {
  interface Window {
    google?: {
      accounts: {
        id: {
          initialize: (opts: { client_id: string; callback: (r: { credential: string }) => void }) => void;
          renderButton: (el: HTMLElement, opts: Record<string, unknown>) => void;
        };
      };
    };
  }
}

function LoginForm() {
  const router = useRouter();
  const next = useSearchParams().get("next") || "/";
  const { caregiver, signIn } = useAuth();

  const [phone, setPhone] = useState("");
  const [code, setCode] = useState("");
  const [codeSent, setCodeSent] = useState(false);
  const [devCode, setDevCode] = useState<string | null>(null);
  const [cooldown, setCooldown] = useState(0);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const googleButton = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (caregiver) router.replace(next.startsWith("/") ? next : "/");
  }, [caregiver, next, router]);

  useEffect(() => {
    if (cooldown <= 0) return;
    const id = setTimeout(() => setCooldown(cooldown - 1), 1000);
    return () => clearTimeout(id);
  }, [cooldown]);

  const finish = useCallback((session: AuthSession) => signIn(session), [signIn]);

  const sendCode = async (e?: FormEvent) => {
    e?.preventDefault();
    if (!isValidPhone(phone)) return setError("Enter your phone number with the country code, like +91 98765 43210.");
    setBusy(true);
    setError(null);
    try {
      const res = await api.requestOtp(normalizePhone(phone));
      setCodeSent(true);
      setDevCode(res.code ?? null);
      setCooldown(RESEND_SECONDS);
    } catch (err) {
      if (err instanceof ApiError && err.status === 429) setCooldown(RESEND_SECONDS);
      setError(errorText(err));
    } finally {
      setBusy(false);
    }
  };

  const verify = async (e: FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      finish(await api.verifyOtp(normalizePhone(phone), code.trim()));
    } catch (err) {
      setError(errorText(err));
      setBusy(false);
    }
  };

  const initGoogle = useCallback(() => {
    if (!window.google || !googleButton.current) return;
    window.google.accounts.id.initialize({
      client_id: GOOGLE_CLIENT_ID,
      callback: async ({ credential }) => {
        setError(null);
        try {
          finish(await api.googleLogin(credential));
        } catch (err) {
          setError(errorText(err));
        }
      },
    });
    window.google.accounts.id.renderButton(googleButton.current, { theme: "outline", size: "large", text: "continue_with", shape: "pill" });
  }, [finish]);

  // The script may already be loaded from an earlier visit to this page.
  useEffect(() => {
    if (GOOGLE_CLIENT_ID && window.google) initGoogle();
  }, [initGoogle]);

  return (
    <section className="login">
      <h1>Sign in to BellAI</h1>
      <p className="lede">Look after the people you care for.</p>

      {!codeSent ? (
        <form onSubmit={sendCode}>
          <label>
            Your phone number
            <input type="tel" value={phone} onChange={(e) => setPhone(e.target.value)} placeholder="+91 98765 43210" autoComplete="tel" autoFocus required />
          </label>
          <button className="btn primary" disabled={busy || cooldown > 0}>
            {busy ? "Sending…" : cooldown > 0 ? `Wait ${cooldown}s` : "Send code"}
          </button>
        </form>
      ) : (
        <form onSubmit={verify}>
          <p className="muted small">
            We sent a code to {phone}.{" "}
            <button type="button" className="link" onClick={() => { setCodeSent(false); setCode(""); setError(null); }}>Change number</button>
          </p>
          <label>
            Code
            <input value={code} onChange={(e) => setCode(e.target.value)} inputMode="numeric" autoComplete="one-time-code" autoFocus required />
          </label>
          {devCode && (
            <p className="hint">
              Dev mode: your code is <button type="button" className="link" onClick={() => setCode(devCode)}>{devCode}</button>
            </p>
          )}
          <button className="btn primary" disabled={busy}>{busy ? "Checking…" : "Sign in"}</button>
          <button type="button" className="btn ghost" disabled={busy || cooldown > 0} onClick={() => sendCode()}>
            {cooldown > 0 ? `Resend code in ${cooldown}s` : "Resend code"}
          </button>
        </form>
      )}

      {error && <p className="error">{error}</p>}

      {GOOGLE_CLIENT_ID && (
        <>
          <p className="divider"><span>or</span></p>
          <div ref={googleButton} />
          <Script src="https://accounts.google.com/gsi/client" strategy="afterInteractive" onLoad={initGoogle} />
        </>
      )}
    </section>
  );
}

export default function Login() {
  return (
    <Suspense fallback={<p className="muted">Loading…</p>}>
      <LoginForm />
    </Suspense>
  );
}
