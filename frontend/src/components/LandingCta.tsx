"use client";

import Link from "next/link";
import { useAuth } from "./AuthProvider";

/** Landing-page button that opens the app for signed-in caregivers and sign-in for everyone else. */
export function LandingCta({ label, next, className = "btn primary" }: { label: string; next: string; className?: string }) {
  const { caregiver } = useAuth();
  if (caregiver) return <Link className={className} href={next}>{next === "/dashboard" ? "Open dashboard" : label}</Link>;
  return <Link className={className} href={`/login?next=${encodeURIComponent(next)}`}>{label}</Link>;
}
