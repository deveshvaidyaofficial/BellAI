"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { FormEvent, useCallback, useState } from "react";
import { ConfirmButton } from "@/components/ConfirmButton";
import { ContactRow } from "@/components/ContactRow";
import { ElderFields, readElderForm } from "@/components/ElderFields";
import { TaskTable } from "@/components/TaskTable";
import { api, errorText } from "@/lib/api";
import { callWindow, isValidPhone, LANGUAGES, normalizePhone } from "@/lib/format";
import { usePolling } from "@/lib/usePolling";
import { Skeleton } from "@/components/Skeleton";

export default function ElderPage() {
  const id = Number(useParams<{ id: string }>().id);
  const router = useRouter();
  const load = useCallback(
    () => Promise.all([api.getElder(id), api.listContacts(id), api.listTasks(id)]),
    [id],
  );
  const { data, error, reload } = usePolling(load);
  const [editing, setEditing] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const [deleteError, setDeleteError] = useState<string | null>(null);

  if (!data) return error ? <p className="error">{error}</p> : <Skeleton />;
  const [elder, contacts, tasks] = data;

  const saveProfile = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const body = readElderForm(new FormData(e.currentTarget));
    if (!isValidPhone(body.phone)) return setFormError("Phone number needs a country code.");
    try {
      await api.updateElder(id, { ...body, phone: normalizePhone(body.phone) });
      setEditing(false);
      setFormError(null);
      reload();
    } catch (err) {
      setFormError(errorText(err));
    }
  };

  // 409 while they still have reminders; the API's message says so.
  const deleteElder = async () => {
    try {
      setDeleteError(null);
      await api.deleteElder(id);
      router.push("/elders");
    } catch (err) {
      setDeleteError(errorText(err));
    }
  };

  const addContact = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const form = e.currentTarget;
    const f = new FormData(form);
    const phone = String(f.get("phone"));
    if (!isValidPhone(phone)) return setFormError("Contact phone number needs a country code.");
    try {
      await api.addContact(id, {
        name: String(f.get("name")).trim(),
        phone: normalizePhone(phone),
        relation: String(f.get("relation") || "").trim() || null,
      });
      form.reset();
      setFormError(null);
      reload();
    } catch (err) {
      setFormError(errorText(err));
    }
  };

  return (
    <>
      <p><Link href="/elders" className="muted small">← People</Link></p>
      <div className="card-head">
        <h1>{elder.name}</h1>
        <button className="btn" onClick={() => setEditing(!editing)}>{editing ? "Cancel" : "Edit profile"}</button>
      </div>
      {formError && <p className="error">{formError}</p>}

      {editing ? (
        <form className="card" onSubmit={saveProfile}>
          <ElderFields elder={elder} />
          <div className="actions">
            <button className="btn primary">Save</button>
            <ConfirmButton label={`Delete ${elder.name}`} confirmLabel="Yes, delete" onConfirm={deleteElder} />
          </div>
          {deleteError && <p className="error">{deleteError}</p>}
        </form>
      ) : (
        <p className="muted">
          {elder.phone} · speaks {LANGUAGES[elder.language] ?? elder.language} · calls {callWindow(elder.call_window_start, elder.call_window_end)} ({elder.timezone})
          {elder.notes && <><br />{elder.notes}</>}
        </p>
      )}

      <section className="card">
        <div className="card-head">
          <h2>Reminders</h2>
          <Link href={`/tasks/new?elder=${id}`} className="btn primary">Add reminder</Link>
        </div>
        <TaskTable tasks={tasks} onChange={reload} empty="No reminders yet." />
      </section>

      <section className="card" id="contacts">
        <h2>Family contacts</h2>
        <p className="muted small">Alerted when a reminder is missed or {elder.name} asks for help.</p>
        {contacts.length > 0 && (
          <ul className="rows">
            {contacts.map((c) => <ContactRow key={c.id} contact={c} onChange={reload} />)}
          </ul>
        )}
        <form className="inline-form" onSubmit={addContact}>
          <input name="name" placeholder="Name" required aria-label="Contact name" />
          <input name="phone" type="tel" placeholder="+91 …" required aria-label="Contact phone" />
          <input name="relation" placeholder="Relation" aria-label="Relation" />
          <button className="btn">Add contact</button>
        </form>
      </section>
    </>
  );
}
