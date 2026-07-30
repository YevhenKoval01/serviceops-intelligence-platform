import { useState } from "react";

import { updateTicketStatus } from "../api";
import { formatLabel } from "../format";
import type { Ticket, TicketStatus } from "../types";

interface TicketDetailProps {
  ticket: Ticket;
  onUpdated: (ticket: Ticket) => void;
  onClose: () => void;
}

export function TicketDetail({ ticket, onUpdated, onClose }: TicketDetailProps) {
  const [updating, setUpdating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function changeStatus(status: TicketStatus) {
    setUpdating(true);
    setError(null);
    try {
      onUpdated(await updateTicketStatus(ticket.id, status));
    } catch (updateError) {
      setError(updateError instanceof Error ? updateError.message : "Could not update status.");
    } finally {
      setUpdating(false);
    }
  }

  return (
    <aside className="detail-panel" aria-labelledby="ticket-detail-heading">
      <div className="detail-header">
        <div>
          <p className="eyebrow">Ticket #{ticket.id.slice(0, 8)}</p>
          <h2 id="ticket-detail-heading">{ticket.title}</h2>
        </div>
        <button className="icon-button" type="button" onClick={onClose} aria-label="Close ticket details">
          ×
        </button>
      </div>

      <p className="description">{ticket.description}</p>

      <div className="detail-grid">
        <div>
          <span>Status</span>
          <strong>{formatLabel(ticket.status)}</strong>
        </div>
        <div>
          <span>Reported priority</span>
          <strong>{ticket.reportedPriority ? formatLabel(ticket.reportedPriority) : "Not specified"}</strong>
        </div>
        <div>
          <span>ML category</span>
          <strong>{ticket.predictedCategory ? formatLabel(ticket.predictedCategory) : "Analyzing…"}</strong>
        </div>
        <div>
          <span>ML priority</span>
          <strong>
            {ticket.predictedPriority ? formatLabel(ticket.predictedPriority) : "Analyzing…"}
          </strong>
        </div>
        <div>
          <span>Confidence</span>
          <strong>
            {ticket.predictionConfidence === null
              ? "Pending"
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
      {error && (
        <div className="inline-error" role="alert">
          {error}
        </div>
      )}
    </aside>
  );
}
