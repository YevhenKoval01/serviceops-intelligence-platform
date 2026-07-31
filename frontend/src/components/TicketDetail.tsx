import { useEffect, useRef, useState } from "react";

import { updateTicketStatus } from "../api";
import { formatLabel } from "../format";
import type { Ticket, TicketStatus } from "../types";

interface TicketDetailProps {
  ticket: Ticket;
  onUpdated: (ticket: Ticket) => void;
  onClose: () => void;
  predictionDelayed?: boolean;
}

export function TicketDetail({
  ticket,
  onUpdated,
  onClose,
  predictionDelayed = false,
}: TicketDetailProps) {
  const [updating, setUpdating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [statusMessage, setStatusMessage] = useState("");
  const panelRef = useRef<HTMLElement>(null);
  const closeButtonRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    const previouslyFocused = document.activeElement as HTMLElement | null;
    closeButtonRef.current?.focus();

    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        onClose();
        return;
      }
      if (event.key !== "Tab" || !panelRef.current) {
        return;
      }
      const focusable = Array.from(
        panelRef.current.querySelectorAll<HTMLElement>(
          'button:not([disabled]), select:not([disabled]), [tabindex]:not([tabindex="-1"])',
        ),
      );
      if (focusable.length === 0) {
        return;
      }
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    }

    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.removeEventListener("keydown", handleKeyDown);
      previouslyFocused?.focus();
    };
  }, [onClose]);

  async function changeStatus(status: TicketStatus) {
    if (status === ticket.status) {
      return;
    }
    setUpdating(true);
    setError(null);
    setStatusMessage("");
    try {
      const updated = await updateTicketStatus(ticket.id, status);
      onUpdated(updated);
      setStatusMessage(`Status updated to ${formatLabel(updated.status)}.`);
    } catch (updateError) {
      setError(updateError instanceof Error ? updateError.message : "Could not update status.");
    } finally {
      setUpdating(false);
    }
  }

  return (
    <div className="detail-layer">
      <button className="detail-backdrop" type="button" onClick={onClose} aria-label="Close ticket details" />
      <aside
        ref={panelRef}
        className="detail-panel"
        role="dialog"
        aria-modal="true"
        aria-labelledby="ticket-detail-heading"
        aria-describedby="ticket-detail-description"
        aria-busy={updating}
      >
        <div className="detail-header">
          <div>
            <p className="eyebrow">Ticket #{ticket.id.slice(0, 8)}</p>
            <h2 id="ticket-detail-heading">{ticket.title}</h2>
          </div>
          <button
            ref={closeButtonRef}
            className="icon-button"
            type="button"
            onClick={onClose}
            aria-label="Close ticket details"
          >
            ×
          </button>
        </div>

        <p className="description" id="ticket-detail-description">
          {ticket.description}
        </p>

        <div className="detail-grid">
          <div>
            <span>Status</span>
            <strong>{formatLabel(ticket.status)}</strong>
          </div>
          <div>
            <span>Reported priority</span>
            <strong>
              {ticket.reportedPriority ? formatLabel(ticket.reportedPriority) : "Not specified"}
            </strong>
          </div>
          <div>
            <span>ML category</span>
            <strong>
              {ticket.predictedCategory
                ? formatLabel(ticket.predictedCategory)
                : predictionDelayed
                  ? "Delayed"
                  : "Analyzing…"}
            </strong>
          </div>
          <div>
            <span>ML priority</span>
            <strong>
              {ticket.predictedPriority
                ? formatLabel(ticket.predictedPriority)
                : predictionDelayed
                  ? "Delayed"
                  : "Analyzing…"}
            </strong>
          </div>
          <div>
            <span>Confidence</span>
            <strong>
              {ticket.predictionConfidence === null
                ? predictionDelayed
                  ? "Delayed"
                  : "Pending"
                : `${Math.round(ticket.predictionConfidence * 100)}%`}
            </strong>
          </div>
          <div>
            <span>Model</span>
            <strong>{ticket.modelVersion ?? "Pending"}</strong>
          </div>
        </div>

        <div className="status-controls">
          <label htmlFor="ticket-status">Update status</label>
          <select
            id="ticket-status"
            value={ticket.status}
            disabled={updating}
            onChange={(event) => void changeStatus(event.target.value as TicketStatus)}
          >
            <option value="OPEN">Open</option>
            <option value="IN_PROGRESS">In progress</option>
            <option value="RESOLVED">Resolved</option>
          </select>
        </div>
        {statusMessage && (
          <div className="inline-success" role="status">
            {statusMessage}
          </div>
        )}
        {error && (
          <div className="inline-error" role="alert">
            {error}
          </div>
        )}
      </aside>
    </div>
  );
}
