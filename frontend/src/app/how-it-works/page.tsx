import type { Metadata } from "next";
import { ArrowRight, Clock, Globe, Moon, Phone, RefreshCw } from "lucide-react";
import { LandingCta } from "@/components/LandingCta";
import { SiteFooter, SiteHeader } from "@/components/SiteChrome";
import { StatusBadge } from "@/components/StatusBadge";
import { STATUS_HELP } from "@/lib/format";
import type { TaskStatus } from "@/lib/types";
import "../landing.css";
import "./docs.css";

export const metadata: Metadata = { title: "How BellAI works" };

const TOC = [
  ["flow", "Overview"],
  ["setup", "Setup"],
  ["rules", "Call rules"],
  ["answers", "Answers"],
  ["retries", "Retries"],
  ["dashboard", "Dashboard"],
];

const FLOW = ["You add a reminder", "BellAI waits for the time", "Their phone rings", "They answer", "You see the result"];

const SETUP = [
  ["Add a person", "Name, phone, language, time zone, call hours."],
  ["Add a family contact", "Who gets alerted when something is wrong."],
  ["Add a reminder", "What, when, and how often it repeats."],
];

const RULES = [
  { icon: Clock, k: "Timing", v: "Checks every 30 s. Calls within a minute of the time." },
  { icon: Moon, k: "Call hours", v: "Only inside the hours you set, in their time zone." },
  { icon: Globe, k: "Language", v: "English or Hindi, per person." },
  { icon: RefreshCw, k: "Retries", v: "3 tries, 10 minutes apart. Both adjustable." },
];

const ANSWERS = [
  ["“I’ve taken it.”", "badge-outcome-completed", "Confirmed", "Done. Repeating reminders move to the next time."],
  ["“Call me later.”", "badge-outcome-later", "Later", "Rings back after 5 min – 4 h. Default 30 min."],
  ["“I need help.”", "badge-outcome-needs_help", "Needs help", "Family is alerted right away."],
  ["No answer", "badge-outcome-no_answer", "No answer", "Tries again. See retries."],
];

const STATUSES: TaskStatus[] = ["pending", "calling", "snoozed", "completed", "needs_help", "missed"];

const BUTTONS = [
  ["Call now", "", "Call immediately. Good for a test."],
  ["Call again", "", "Retry a reminder that needs you."],
  ["Mark handled", "primary", "You checked on them. Clears the alert."],
  ["Reset call", "ghost", "Only if a call looks stuck."],
];

export default function HowItWorks() {
  return (
    <div className="landing docs">
      <SiteHeader />

      <header className="wrap docs-hero">
        <p className="eyebrow">How it works</p>
        <h1>How BellAI works</h1>
        <p className="hero-sub">The whole product on one page.</p>
      </header>

      <div className="wrap docs-grid">
        <nav className="toc" aria-label="On this page">
          {TOC.map(([id, label]) => <a key={id} href={`#${id}`}>{label}</a>)}
        </nav>

        <article className="doc">
          <section id="flow">
            <h2>Overview</h2>
            <ol className="d-flow">
              {FLOW.map((f, i) => (
                <li key={f}><span>{i + 1}</span>{f}</li>
              ))}
            </ol>
          </section>

          <section id="setup">
            <h2>Setup</h2>
            <ol className="d-steps">
              {SETUP.map(([t, d], i) => (
                <li key={t}><span className="d-n">{i + 1}</span><div><b>{t}</b><p>{d}</p></div></li>
              ))}
            </ol>
          </section>

          <section id="rules">
            <h2>Call rules</h2>
            <dl className="d-rules">
              {RULES.map((r) => (
                <div key={r.k}><dt><r.icon size={18} />{r.k}</dt><dd>{r.v}</dd></div>
              ))}
            </dl>
          </section>

          <section id="answers">
            <h2>Answers</h2>
            <div className="d-table">
              {ANSWERS.map(([say, cls, label, then]) => (
                <div key={label} className="d-tr">
                  <span className="d-say">{say}</span>
                  <span><span className={`badge ${cls}`}>{label}</span></span>
                  <span className="d-then">{then}</span>
                </div>
              ))}
            </div>
          </section>

          <section id="retries">
            <h2>Retries</h2>
            <ol className="d-timeline">
              <li><Phone size={14} /><b>8:00</b>No answer</li>
              <li><Phone size={14} /><b>8:10</b>No answer</li>
              <li><Phone size={14} /><b>8:20</b>No answer</li>
              <li className="bad"><b>Missed</b>Family alerted</li>
            </ol>
          </section>

          <section id="dashboard">
            <h2>Dashboard</h2>
            <div className="d-legend">
              {STATUSES.map((s) => (
                <div key={s}><StatusBadge status={s} /><span>{STATUS_HELP[s]}</span></div>
              ))}
            </div>
            <div className="d-legend">
              {BUTTONS.map(([label, cls, text]) => (
                <div key={label}><span className={`btn ${cls} d-btn`}>{label}</span><span>{text}</span></div>
              ))}
            </div>
          </section>

          <div className="d-cta">
            <b>Ready to try it?</b>
            <LandingCta label="Get started" next="/elders/new" />
            <a href="/" className="d-back">Back to home <ArrowRight size={14} /></a>
          </div>
        </article>
      </div>

      <SiteFooter />
    </div>
  );
}
