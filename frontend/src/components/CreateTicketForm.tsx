import { useRef, useState, type FormEvent } from "react";

import { createTicket } from "../api";
import type { CreateTicketInput, Priority, Ticket } from "../types";

interface CreateTicketFormProps {
  onCreated: (ticket: Ticket) => void;
}

type FormErrors = Partial<Record<"title" | "description", string>>;

const initialForm: CreateTicketInput = {
  title: "",
  description: "",
  reportedPriority: null,
};

export function CreateTicketForm({ onCreated }: CreateTicketFormProps) {
  const [form, setForm] = useState<CreateTicketInput>(initialForm);
  const [errors, setErrors] = useState<FormErrors>({});
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const titleRef = useRef<HTMLInputElement>(null);
  const descriptionRef = useRef<HTMLTextAreaElement>(null);

  function validate(): FormErrors {
    const nextErrors: FormErrors = {};
    const titleLength = form.title.trim().length;
    const descriptionLength = form.description.trim().length;
    if (titleLength < 5) {
      nextErrors.title = "Use at least 5 characters.";
    } else if (titleLength > 150) {
      nextErrors.title = "Use no more than 150 characters.";
    }
    if (descriptionLength < 10) {
      nextErrors.description = "Use at least 10 characters.";
    } else if (descriptionLength > 4000) {
      nextErrors.description = "Use no more than 4,000 characters.";
    }
    return nextErrors;
  }

  function changeField(field: "title" | "description", value: string) {
    setForm((current) => ({ ...current, [field]: value }));
    setErrors((current) => {
      const next = { ...current };
      delete next[field];
      return next;
    });
    setSubmitError(null);
    setSuccessMessage(null);
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const nextErrors = validate();
    setErrors(nextErrors);
    if (Object.keys(nextErrors).length > 0) {
      if (nextErrors.title) {
        titleRef.current?.focus();
      } else {
        descriptionRef.current?.focus();
      }
      return;
    }
    setSubmitting(true);
    setSubmitError(null);
    setSuccessMessage(null);
    try {
      const ticket = await createTicket({
        ...form,
        title: form.title.trim(),
        description: form.description.trim(),
      });
      setForm(initialForm);
      setSuccessMessage("Ticket created. Prediction is now in progress.");
      onCreated(ticket);
      titleRef.current?.focus();
    } catch (error) {
      setSubmitError(error instanceof Error ? error.message : "Could not create the ticket.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <section className="create-panel" aria-labelledby="create-ticket-heading">
      <div className="section-heading">
        <div>
          <p className="eyebrow">New request</p>
          <h2 id="create-ticket-heading">Create a support ticket</h2>
        </div>
        <span className="async-note">Prediction runs asynchronously</span>
      </div>

      <form onSubmit={handleSubmit} noValidate aria-busy={submitting}>
        <div className="form-field">
          <label htmlFor="ticket-title">Title</label>
          <input
            ref={titleRef}
            id="ticket-title"
            name="title"
            required
            autoComplete="off"
            value={form.title}
            maxLength={150}
            aria-invalid={Boolean(errors.title)}
            aria-describedby={errors.title ? "ticket-title-error" : undefined}
            onChange={(event) => changeField("title", event.target.value)}
            placeholder="Briefly describe the issue"
          />
          {errors.title && (
            <span className="field-error" id="ticket-title-error">
              {errors.title}
            </span>
          )}
          <span className="character-count">{form.title.length}/150</span>
        </div>

        <div className="form-field">
          <label htmlFor="ticket-description">Description</label>
          <textarea
            ref={descriptionRef}
            id="ticket-description"
            name="description"
            required
            value={form.description}
            maxLength={4000}
            rows={4}
            aria-invalid={Boolean(errors.description)}
            aria-describedby={errors.description ? "ticket-description-error" : undefined}
            onChange={(event) => changeField("description", event.target.value)}
            placeholder="Include the impact, symptoms, and relevant context"
          />
          {errors.description && (
            <span className="field-error" id="ticket-description-error">
              {errors.description}
            </span>
          )}
          <span className="character-count">{form.description.length}/4,000</span>
        </div>

        <div className="form-actions">
          <div className="form-field priority-field">
            <label htmlFor="reported-priority">Reported priority</label>
            <select
              id="reported-priority"
              name="reportedPriority"
              value={form.reportedPriority ?? ""}
              onChange={(event) =>
                setForm({
                  ...form,
                  reportedPriority: (event.target.value || null) as Priority | null,
                })
              }
            >
              <option value="">Not specified</option>
              <option value="LOW">Low</option>
              <option value="MEDIUM">Medium</option>
              <option value="HIGH">High</option>
            </select>
          </div>
          <button className="primary-button" type="submit" disabled={submitting}>
            {submitting ? "Creating…" : "Create ticket"}
          </button>
        </div>
        {submitError && (
          <div className="inline-error" role="alert">
            {submitError}
          </div>
        )}
        {successMessage && (
          <div className="inline-success" role="status">
            {successMessage}
          </div>
        )}
      </form>
    </section>
  );
}
