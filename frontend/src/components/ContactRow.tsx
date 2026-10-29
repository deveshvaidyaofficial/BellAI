"use client";

import { FormEvent, useState } from "react";
import { api, errorText } from "@/lib/api";
import { isValidPhone, normalizePhone } from "@/lib/format";
import type { Contact } from "@/lib/types";
import { ConfirmButton } from "./ConfirmButton";

export function ContactRow({ contact, onChange }: { contact: Contact; onChange: () => void }) {
  const [editing, setEditing] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const run = async (action: () => Promise<unknown>) => {
    setBusy(true);
    setError(null);
    try {
      await action();
      setEditing(false);
      onChange();
    } catch (e) {
      setError(errorText(e));
    } finally {
      setBusy(false);
    }
  };

  const save = (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const f = new FormData(e.currentTarget);
    const phone = String(f.get("phone"));
    if (!isValidPhone(phone)) return setError("Phone number needs a country code, like +91 98765 43210.");
    run(() =>
      api.updateContact(contact.elder_id, contact.id, {
        name: String(f.get("name")).trim(),
        phone: normalizePhone(phone),
        relation: String(f.get("relation") || "").trim() || null,
        notify_on_missed: f.get("notify_on_missed") === "on",
      }),
    );
  };

  return (
    <li className="row">
      {editing ? (
        <form className="inline-form" onSubmit={save}>
          <input name="name" defaultValue={contact.name} required aria-label="Name" />
          <input name="phone" type="tel" defaultValue={contact.phone} required aria-label="Phone" />
          <input name="relation" defaultValue={contact.relation ?? ""} placeholder="Relation" aria-label="Relation" />
          <label className="check">
            <input type="checkbox" name="notify_on_missed" defaultChecked={contact.notify_on_missed ?? true} /> Send alerts
          </label>
          <button className="btn primary" disabled={busy}>Save</button>
          <button type="button" className="btn ghost" onClick={() => { setEditing(false); setError(null); }}>Cancel</button>
        </form>
      ) : (
        <>
          <div className="row-main">
            <span className="row-title">{contact.name}</span>
            <span className="muted small">
              {contact.phone}
              {contact.relation && ` · ${contact.relation}`}
              {contact.notify_on_missed === false && " · alerts off"}
            </span>
          </div>
          <div className="actions">
            <button className="btn" disabled={busy} onClick={() => setEditing(true)}>Edit</button>
            <ConfirmButton
              label="Remove"
              confirmLabel={`Remove ${contact.name}`}
              disabled={busy}
              onConfirm={() => run(() => api.deleteContact(contact.elder_id, contact.id))}
            />
          </div>
        </>
      )}
      {error && <p className="error small">{error}</p>}
    </li>
  );
}
