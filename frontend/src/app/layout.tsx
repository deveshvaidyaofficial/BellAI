import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";

export const metadata: Metadata = {
  title: "BellAI",
  description: "Voice reminders that help elders live independently",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <header className="nav">
          <Link href="/" className="brand">🔔 BellAI</Link>
          <nav>
            <Link href="/elders/new">Add elder</Link>
            <Link href="/tasks/new">Add reminder</Link>
          </nav>
        </header>
        <main>{children}</main>
      </body>
    </html>
  );
}
