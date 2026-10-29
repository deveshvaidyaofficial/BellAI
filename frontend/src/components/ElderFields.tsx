import { LANGUAGES } from "@/lib/format";
import type { Elder } from "@/lib/types";

const TIMEZONES = ["Asia/Kolkata", "Asia/Dubai", "Europe/London", "America/New_York", "America/Los_Angeles", "Asia/Singapore"];

/** Shared by "add a person" and the profile editor. Read with readElderForm(). */
export function ElderFields({ elder }: { elder?: Elder }) {
  return (
    <>
      <label>Name <input name="name" defaultValue={elder?.name} required /></label>
      <label>
        Phone number
        <input name="phone" type="tel" defaultValue={elder?.phone} placeholder="+91 98765 43210" required />
        <span className="hint">Include the country code.</span>
      </label>
      <label>
        Language Bell should speak
        <select name="language" defaultValue={elder?.language ?? "en"}>
          {Object.entries(LANGUAGES).map(([code, name]) => <option key={code} value={code}>{name}</option>)}
        </select>
      </label>
      <label>
        Their timezone
        <select name="timezone" defaultValue={elder?.timezone ?? "Asia/Kolkata"}>
          {TIMEZONES.map((tz) => <option key={tz}>{tz}</option>)}
        </select>
      </label>
      <fieldset className="inline">
        <legend>OK to call between</legend>
        <input name="call_window_start" type="time" defaultValue={elder?.call_window_start ?? "08:00"} aria-label="From" />
        <span>and</span>
        <input name="call_window_end" type="time" defaultValue={elder?.call_window_end ?? "21:00"} aria-label="Until" />
      </fieldset>
      <label>Notes for Bell <textarea name="notes" rows={2} defaultValue={elder?.notes ?? ""} placeholder="Hard of hearing, prefers to be called Aai…" /></label>
    </>
  );
}

export function readElderForm(f: FormData) {
  return {
    name: String(f.get("name")).trim(),
    phone: String(f.get("phone")),
    language: String(f.get("language")),
    timezone: String(f.get("timezone")),
    call_window_start: String(f.get("call_window_start")),
    call_window_end: String(f.get("call_window_end")),
    notes: String(f.get("notes") || "").trim() || null,
  };
}
