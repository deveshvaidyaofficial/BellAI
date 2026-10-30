import Link from "next/link";
import { BellLogo } from "./BellLogo";
import { LandingCta } from "./LandingCta";

/** Header shared by the public pages (landing and how-it-works). */
export function SiteHeader() {
  return (
    <div className="site-header">
      <nav className="wrap landing-nav">
        <Link className="logo" href="/" aria-label="BellAI home">
          <BellLogo />
          BellAI
        </Link>
        <div className="links">
          <Link href="/how-it-works">How it works</Link>
          <Link href="/#market">Why BellAI</Link>
          <Link href="/#families">For families</Link>
          <Link href="/#faq">Questions</Link>
          <LandingCta label="Get started" next="/dashboard" />
        </div>
      </nav>
    </div>
  );
}

export function SiteFooter() {
  return (
    <div className="wrap">
      <footer className="site-footer">
        <div className="foot-brand">
          <Link className="logo" href="/"><BellLogo />BellAI</Link>
          <p>A friendly voice that remembers for you.</p>
        </div>
        <div className="foot-cols">
          <div>
            <b>Product</b>
            <Link href="/how-it-works">How it works</Link>
            <Link href="/#outcomes">What happens after a call</Link>
            <Link href="/#market">Why BellAI</Link>
            <Link href="/#families">Family dashboard</Link>
          </div>
          <div>
            <b>Get going</b>
            <Link href="/login">Sign in</Link>
            <Link href="/how-it-works#setup">Set up in 3 steps</Link>
            <Link href="/#faq">Questions</Link>
          </div>
        </div>
      </footer>
    </div>
  );
}
