import type { Metadata } from "next";
import { Instrument_Sans } from "next/font/google";
import Link from "next/link";
import "./globals.css";

const font = Instrument_Sans({ subsets: ["latin"], weight: ["400", "500", "600"] });

export const metadata: Metadata = {
  title: "BellAI",
  description: "A friendly voice that remembers for you",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className={font.className}>
        <header className="nav">
          <Link href="/" className="brand">BellAI</Link>
          <nav>
            <Link href="/">Today</Link>
            <Link href="/elders">People</Link>
            <Link href="/calls">Calls</Link>
            <Link href="/tasks/new" className="btn primary">Add reminder</Link>
          </nav>
        </header>
        <main>{children}</main>
      </body>
    </html>
  );
}
