import type { Ticket } from "../types";
import { formatLabel } from "../format";

interface TicketTableProps {
  tickets: Ticket[];
  selectedId: string | null;
  onSelect: (ticket: Ticket) => void;
}

function Confidence({ ticket }: { ticket: Ticket }) {
  if (ticket.predictionConfidence === null) {
    return <span className="pending-prediction">Analyzing…</span>;
  }
  return <span>{Math.round(ticket.predictionConfidence * 100)}%</span>;
}

export function TicketTable({ tickets, selectedId, onSelect }: TicketTableProps) {
  if (tickets.length === 0) {
    return (
      <div className="empty-state">
        <div className="empty-mark">0</div>
        <h3>No tickets in the queue</h3>
        <p>Create the first request to watch the event-driven prediction flow.</p>
      </div>
    );
  }

  return (
    <div className="table-scroll">
      <table>
        <thead>
          <tr>
            <th>Ticket</th>
            <th>Status</th>
            <th>Category</th>
            <th>Priority</th>
            <th>Confidence</th>
            <th>Created</th>
          </tr>
        </thead>
        <tbody>
          {tickets.map((ticket) => (
            <tr
              key={ticket.id}
              className={ticket.id === selectedId ? "selected-row" : undefined}
              onClick={() => onSelect(ticket)}
            >
              <td>
                <button className="ticket-link" type="button" onClick={() => onSelect(ticket)}>
                  <strong>{ticket.title}</strong>
                  <span>#{ticket.id.slice(0, 8)}</span>
                </button>
              </td>
              <td>
                <span className={`pill status-${ticket.status.toLowerCase()}`}>
                  {formatLabel(ticket.status)}
                </span>
              </td>
              <td>{ticket.predictedCategory ? formatLabel(ticket.predictedCategory) : "Pending"}</td>
              <td>
                {ticket.predictedPriority ? (
                  <span className={`priority priority-${ticket.predictedPriority.toLowerCase()}`}>
                    {formatLabel(ticket.predictedPriority)}
                  </span>
                ) : (
                  "—"
                )}
              </td>
              <td>
                <Confidence ticket={ticket} />
              </td>
              <td>{new Date(ticket.createdAt).toLocaleString()}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
