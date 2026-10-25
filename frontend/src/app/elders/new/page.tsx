"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";

// TODO(frontend): trusted contacts section, validation (E.164 phone), auth.
export default function NewElder() {
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  const onSubmit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const f = new FormData(e.currentTarget);
    setSaving(true);
    try {
      const elder = await api.createElder({
        name: String(f.get("name")),
        phone: String(f.get("phone")),
        language: String(f.get("language")),
        call_window_start: String(f.get("call_window_start")),
        call_window_end: String(f.get("call_window_end")),
        notes: String(f.get("notes") || "") || null,
      });
      const contactName = String(f.get("contact_name") || "");
      if (contactName) {
        await api.addContact(elder.id, {
          name: contactName,
          phone: String(f.get("contact_phone")),
          relation: String(f.get("contact_relation") || "") || null,
        });
      }
      router.push("/");
    } catch (err) {
      setError(String(err));
      setSaving(false);
    }
  };

  return (
    <>
      <h1>Add elder</h1>
      <form onSubmit={onSubmit}>
        <label>Name <input name="name" required /></label>
        <label>Phone (with country code) <input name="phone" placeholder="+919876543210" required /></label>
        <label>Preferred language
          <select name="language" defaultValue="en">
            <option value="en">English</option>
            <option value="hi">Hindi</option>
            <option value="mr">Marathi</option>
          </select>
        </label>
        <label>Call window start <input name="call_window_start" type="time" defaultValue="08:00" /></label>
        <label>Call window end <input name="call_window_end" type="time" defaultValue="21:00" /></label>
        <label>Notes <textarea name="notes" rows={2} /></label>

        <h3>Trusted contact (optional)</h3>
        <label>Name <input name="contact_name" /></label>
        <label>Phone <input name="contact_phone" /></label>
        <label>Relation <input name="contact_relation" placeholder="Son, daughter, neighbour…" /></label>

        {error && <p className="error">{error}</p>}
        <button disabled={saving}>{saving ? "Saving…" : "Save"}</button>
      </form>
    </>
  );
}
