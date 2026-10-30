import type { Metadata } from "next";
import Link from "next/link";
import {
  ArrowRight, BellRing, Building2, CalendarDays, Check, Clock, Droplet, HeartPulse, House, ListChecks,
  MessageCircle, Minus, Moon, Phone, Pill, ShieldCheck, Smartphone, Stethoscope, TriangleAlert, Users, Utensils, X,
} from "lucide-react";
import { LandingCta } from "@/components/LandingCta";
import { SiteFooter, SiteHeader } from "@/components/SiteChrome";
import { Faq } from "@/components/site/Faq";
import { IPhoneCall } from "@/components/site/IPhoneCall";
import { MacWindow } from "@/components/site/MacWindow";
import { GrowthBars, Ring, TwoInThree } from "@/components/site/MarketViz";
import { NumberTicker, Reveal, SpotlightCard } from "@/components/site/Motion";
import { Splash } from "@/components/site/Splash";
import "./landing.css";

export const metadata: Metadata = { title: "BellAI: a friendly voice that remembers for you" };

const MARQUEE = [
  { icon: Pill, text: "Metformin · 8:00 am" },
  { icon: Droplet, text: "Glass of water · 11:00 am" },
  { icon: Utensils, text: "Lunch · 1:00 pm" },
  { icon: CalendarDays, text: "Dr. Rao check-up · Tue 10:00" },
  { icon: HeartPulse, text: "Blood pressure tablet · 9:00 pm" },
  { icon: Clock, text: "Evening walk · 6:00 pm" },
  { icon: Pill, text: "Vitamin D · every Sunday" },
  { icon: Droplet, text: "Eye drops · 10:00 pm" },
];

const STEPS = [
  { icon: ListChecks, title: "You add the routine", text: "Medicines, visits, meals and water, each at the time it matters." },
  { icon: Phone, title: "BellAI calls on time", text: "A warm voice rings their ordinary phone, only in the hours you allow." },
  { icon: MessageCircle, title: "They just answer", text: "“Done”, “call me later” or “I need help”. No buttons, no app." },
  { icon: HeartPulse, title: "You stay in the loop", text: "Every call lands on your dashboard. Trouble alerts the family." },
];

const OUTCOMES = [
  { tone: "ok", say: "“Yes, I’ve taken it.”", label: "Done", then: "Marked as done. Tomorrow’s call is already set." },
  { tone: "warn", say: "“Call me in half an hour.”", label: "Call later", then: "BellAI rings back when asked, from 5 minutes to 4 hours." },
  { tone: "bad", say: "“I’m feeling dizzy.”", label: "Needs help", then: "Flagged at once. The family contacts you chose are alerted." },
  { tone: "info", say: "No answer", label: "Tries again", then: "Up to 3 calls, 10 minutes apart. Then the family is told." },
];

const SEGMENTS = [
  { icon: House, title: "Families living apart", text: "Children in another city or country who can’t call at 8 am every day." },
  { icon: Building2, title: "Home-care services", text: "One coordinator watches many people instead of dialling each by hand." },
  { icon: Stethoscope, title: "Clinics and pharmacies", text: "Follow-up calls that keep patients on their treatment at home." },
];

type Mark = "yes" | "no" | "some";
const COMPARE: { row: string; marks: Mark[] }[] = [
  { row: "Works on any phone, even a landline", marks: ["yes", "no", "yes", "yes"] },
  { row: "No tech skills needed from the elder", marks: ["yes", "no", "yes", "yes"] },
  { row: "Checks that it was actually done", marks: ["yes", "some", "no", "yes"] },
  { row: "Tells the family when something is wrong", marks: ["yes", "some", "no", "yes"] },
  { row: "Speaks their language", marks: ["yes", "some", "no", "yes"] },
  { row: "Every reminder, every day, at low cost", marks: ["yes", "yes", "yes", "no"] },
];

const FAQ: [string, string][] = [
  ["Does my parent need a smartphone or an app?", "No. BellAI rings the phone they already have, mobile or landline, and they just talk."],
  ["What languages does BellAI speak?", "English and Hindi today. You choose the language for each person."],
  ["Will it call in the middle of the night?", "No. You set call hours for each person in their own time zone. A reminder that falls outside them waits until the hours open."],
  ["What if they don’t pick up?", "BellAI tries again 10 minutes later, up to 3 times. If there is still no answer, it marks the reminder as missed and alerts the family."],
  ["Who gets alerted when something goes wrong?", "The family contacts you add for that person. You can switch alerts off for anyone."],
  ["Can I see what was said?", "Yes. Every call is written down on your dashboard with the outcome, a short note and the transcript."],
];

const COLS = ["BellAI", "Reminder apps", "Alarms & pill boxes", "Daily family call"];

const markIcon = (m: Mark, label: string) =>
  m === "yes" ? <span className="mk yes" aria-label={`${label}: yes`}><Check size={14} strokeWidth={3} /></span>
  : m === "no" ? <span className="mk no" aria-label={`${label}: no`}><X size={13} strokeWidth={2.5} /></span>
  : <span className="mk some" aria-label={`${label}: partly`}><Minus size={13} strokeWidth={2.5} /></span>;

function SectionHead({ eyebrow, title, muted, lede, center = true }: { eyebrow: string; title: string; muted?: string; lede?: string; center?: boolean }) {
  return (
    <Reveal className={`section-head ${center ? "center" : ""}`}>
      <p className="eyebrow">{eyebrow}</p>
      <h2>{title} {muted && <span>{muted}</span>}</h2>
      {lede && <p className="lede">{lede}</p>}
    </Reveal>
  );
}

export default function Landing() {
  return (
    <div className="landing">
      <Splash />
      <SiteHeader />

      <header className="hero">
        <div className="hero-bg" aria-hidden="true" />
        <div className="wrap hero-grid">
          <div className="hero-copy">
            <Reveal>
              <p className="pill-tag"><span className="live" />Voice reminders for the people you love</p>
            </Reveal>
            <Reveal delay={0.08}>
              <h1>Your loved one’s day, <em>gently remembered.</em></h1>
            </Reveal>
            <Reveal delay={0.16}>
              <p className="hero-sub">BellAI phones your parent at the right moment for medicines, appointments and the small things that are easy to forget. They just pick up and talk. You see how it went.</p>
            </Reveal>
            <Reveal delay={0.24}>
              <div className="actions">
                <LandingCta label="Set up a first call" next="/elders/new" className="btn primary shine" />
                <Link className="btn plain" href="/how-it-works">See how it works <ArrowRight size={16} /></Link>
              </div>
              <ul className="hero-points">
                <li><Check size={16} />No app for them</li>
                <li><Check size={16} />English and Hindi</li>
                <li><Check size={16} />Family alerted if needed</li>
              </ul>
            </Reveal>
          </div>
          <div className="hero-stage">
            <div className="glow" aria-hidden="true" />
            <IPhoneCall />
          </div>
        </div>
      </header>

      <div className="strip">
        <p className="strip-label">Reminders families set up with BellAI</p>
        <div className="marquee">
          {[0, 1].map((row) => (
            <div key={row} className={`marquee-row ${row ? "reverse" : ""}`} aria-hidden={row === 1}>
              {[...MARQUEE, ...MARQUEE].map((m, i) => (
                <span key={i} className="mq-chip"><m.icon size={16} />{m.text}</span>
              ))}
            </div>
          ))}
        </div>
      </div>

      <section id="how" className="block">
        <div className="wrap">
          <SectionHead eyebrow="How it works" title="One call, one small thing." muted="Easy to answer, easy to trust." />
          <ol className="flow">
            {STEPS.map((s, i) => (
              <li key={s.title}>
                <Reveal delay={i * 0.08} className="flow-card">
                  <span className="flow-top">
                    <span className="flow-icon"><s.icon size={22} /></span>
                    <span className="flow-n">0{i + 1}</span>
                  </span>
                  <h3>{s.title}</h3>
                  <p>{s.text}</p>
                </Reveal>
              </li>
            ))}
          </ol>
          <div className="center-row">
            <Link href="/how-it-works" className="more">Read the full walkthrough <ArrowRight size={16} /></Link>
          </div>
        </div>
      </section>

      <section id="outcomes" className="block">
        <div className="wrap">
          <SectionHead eyebrow="After the call" title="Every answer has a next step." muted="You never have to guess." />
          <ul className="outcomes">
            {OUTCOMES.map((o, i) => (
              <li key={o.label}>
                <Reveal delay={i * 0.08} className="fill">
                  <SpotlightCard className={`outcome tone-${o.tone}`}>
                    <span className="tag">{o.label}</span>
                    <p className="say">{o.say}</p>
                    <p className="then">{o.then}</p>
                  </SpotlightCard>
                </Reveal>
              </li>
            ))}
          </ul>
        </div>
      </section>

      <section id="market" className="block tint">
        <div className="wrap">
          <SectionHead
            eyebrow="Why BellAI, why now"
            title="A huge, fast-growing need."
            muted="Met with the phone they already own."
            lede="India’s older population is set to more than double by 2050. Many manage daily medicines, and their children often live far away. A phone call is the one technology every parent already trusts."
          />

          <div className="bento">
            <Reveal className="bento-card big">
              <div className="bento-text">
                <p className="bento-k">Indians aged 60+</p>
                <div>
                  <p className="bento-v"><NumberTicker value={149} suffix="M" /> <span>→</span> <NumberTicker value={347} suffix="M" /></p>
                  <p className="bento-note">More than double by 2050, from 10.5% to about 1 in 5 Indians.</p>
                </div>
              </div>
              <GrowthBars />
            </Reveal>
            <Reveal delay={0.08} className="bento-card">
              <p className="bento-k">Chronic disease</p>
              <div className="bento-viz"><TwoInThree /></div>
              <div>
                <p className="bento-v sm"><NumberTicker value={2} suffix=" in 3" /></p>
                <p className="bento-note">seniors in India live with a chronic disease.</p>
              </div>
            </Reveal>
            <Reveal delay={0.16} className="bento-card">
              <p className="bento-k">Missed medicines</p>
              <div className="bento-viz"><Ring percent={50} /></div>
              <div>
                <p className="bento-v sm"><NumberTicker value={50} prefix="~" suffix="%" /></p>
                <p className="bento-note">of long-term medicines aren’t taken as prescribed.</p>
              </div>
            </Reveal>
          </div>

          <div className="segments">
            {SEGMENTS.map((s, i) => (
              <Reveal key={s.title} delay={i * 0.08} className="fill">
                <SpotlightCard className="segment">
                  <span className="seg-icon"><s.icon size={20} /></span>
                  <h3>{s.title}</h3>
                  <p>{s.text}</p>
                </SpotlightCard>
              </Reveal>
            ))}
          </div>

          <p className="sources">
            Sources: <a href="https://india.unfpa.org/en/news/india-ageing-elderly-make-20-population-2050-unfpa-report" target="_blank" rel="noreferrer">UNFPA &amp; IIPS, India Ageing Report 2023</a>
            <span>·</span><a href="https://www.downtoearth.org.in/health/almost-70-senior-citizens-in-india-have-a-chronic-illness-74944" target="_blank" rel="noreferrer">LASI Wave 1, 2017–18</a>
            <span>·</span><a href="https://www.who.int/news/item/01-07-2003-failure-to-take-prescribed-medicine-for-chronic-diseases-is-a-massive-world-wide-problem" target="_blank" rel="noreferrer">WHO, 2003</a>
          </p>
        </div>
      </section>

      <section id="compare" className="block">
        <div className="wrap">
          <SectionHead eyebrow="How BellAI compares" title="The best of every option," muted="in one phone call." />
          <Reveal>
            <div className="compare-wrap">
              <table className="compare">
                <thead>
                  <tr>
                    <th scope="col"><span className="sr-only">Feature</span></th>
                    <th scope="col" className="us"><BellRing size={16} />BellAI</th>
                    <th scope="col"><Smartphone size={16} />Reminder apps</th>
                    <th scope="col"><Clock size={16} />Alarms &amp; pill boxes</th>
                    <th scope="col"><Users size={16} />Daily family call</th>
                  </tr>
                </thead>
                <tbody>
                  {COMPARE.map((c) => (
                    <tr key={c.row}>
                      <th scope="row">{c.row}</th>
                      {c.marks.map((m, i) => <td key={i} className={i === 0 ? "us" : ""}>{markIcon(m, COLS[i])}</td>)}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Reveal>
        </div>
      </section>

      <section id="families" className="block">
        <div className="wrap families">
          <div>
            <SectionHead
              center={false}
              eyebrow="For families"
              title="Independence for them."
              muted="Peace of mind for you."
              lede="One calm page that tells you what needs you and what is coming up. Try the window buttons."
            />
            <Reveal delay={0.1}>
              <ul className="ticks">
                <li><span className="tick-icon"><TriangleAlert size={16} /></span><span><b>Needs your attention</b> only when they ask for help or miss a reminder.</span></li>
                <li><span className="tick-icon"><Moon size={16} /></span><span><b>Call hours</b> in their own time zone. No calls at night.</span></li>
                <li><span className="tick-icon"><Users size={16} /></span><span><b>Family contacts</b> alerted when something is wrong.</span></li>
                <li><span className="tick-icon"><ShieldCheck size={16} /></span><span><b>Every call written down</b>, with the transcript.</span></li>
              </ul>
            </Reveal>
          </div>
          <Reveal delay={0.1}>
            <MacWindow />
          </Reveal>
        </div>
      </section>

      <section id="faq" className="block">
        <div className="wrap faq-grid">
          <SectionHead center={false} eyebrow="Questions" title="Things families ask us." muted="Short answers." />
          <Reveal delay={0.08}>
            <Faq items={FAQ} />
          </Reveal>
        </div>
      </section>

      <section id="start" className="block last">
        <div className="wrap">
          <Reveal>
            <div className="cta-card">
              <div className="cta-rings" aria-hidden="true"><i /><i /><i /></div>
              <span className="cta-bell"><BellRing size={28} /></span>
              <h2>Start with one reminder.</h2>
              <p>Sign in with your phone number, add the person you care for and set their first reminder. It takes about two minutes.</p>
              <div className="actions">
                <LandingCta label="Set up a first call" next="/elders/new" className="btn on-dark" />
                <Link className="btn ghost-dark" href="/how-it-works">How it works</Link>
              </div>
            </div>
          </Reveal>
        </div>
      </section>

      <SiteFooter />
    </div>
  );
}
