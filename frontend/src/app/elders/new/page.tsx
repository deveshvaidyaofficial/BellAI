"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import { ElderFields, readElderForm } from "@/components/ElderFields";
import { api, errorText } from "@/lib/api";
import { isValidPhone, normalizePhone } from "@/lib/format";

// TODO(frontend): OTP / Google login once auth exists.
export default function NewElder() {
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  const onSubmit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const f = new FormData(e.currentTarget);
    const elder = readElderForm(f);
    const contactName = String(f.get("contact_name") || "").trim();
    const contactPhone = String(f.get("contact_phone") || "");

    if (!isValidPhone(elder.phone)) return setError("Their phone number needs a country code, like +91 98765 43210.");
    if (contactName && !isValidPhone(contactPhone)) return setError("The family contact's phone number needs a country code.");

    setSaving(true);
    setError(null);
    try {
      const created = await api.createElder({ ...elder, phone: normalizePhone(elder.phone) });
      if (contactName) {
        await api.addContact(created.id, {
          name: contactName,
          phone: normalizePhone(contactPhone),
          relation: String(f.get("contact_relation") || "").trim() || null,
        });
      }
      router.push(`/tasks/new?elder=${created.id}`);
    } catch (err) {
      setError(errorText(err));
      setSaving(false);
    }
  };

  return (
    <>
      <h1>Add a person</h1>
      <p className="lede">Who should Bell call?</p>
      <form onSubmit={onSubmit}>
        <ElderFields />

        <h2>Who should we tell if something's wrong?</h2>
        <p className="muted small">They'll be alerted if a reminder is missed or help is asked for. You can add more later.</p>
        <label>Name <input name="contact_name" /></label>
        <label>Phone number <input name="contact_phone" type="tel" placeholder="+91 …" /></label>
        <label>Relation <input name="contact_relation" placeholder="Son, daughter, neighbour…" /></label>

        {error && <p className="error">{error}</p>}
        <button className="btn primary" disabled={saving}>{saving ? "Saving…" : "Save and add a reminder"}</button>
      </form>
    </>
  );
}
