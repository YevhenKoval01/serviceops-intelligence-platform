import type { Ticket } from "../types";
import { formatLabel } from "../format";

interface TicketTableProps {
  tickets: Ticket[];
  selectedId: string | null;
  onSelect: (ticket: Ticket) => void;
  delayedPredictionIds?: Set<string>;
}

function Confidence({ ticket, delayed }: { ticket: Ticket; delayed: boolean }) {
  if (ticket.predictionConfidence === null) {
    return (
      <span className={delayed ? "delayed-prediction" : "pending-prediction"} aria-live="polite">
        {delayed ? "Delayed" : "Analyzing…"}
      </span>
    );
  }
  return <span>{Math.round(ticket.predictionConfidence * 100)}%</span>;
}

export function TicketTable({
  tickets,
  selectedId,
  onSelect,
  delayedPredictionIds = new Set(),
}: TicketTableProps) {
  if (tickets.length === 0) {
    return (
      <div className="empty-state" role="status">
        <div className="empty-mark">0</div>
        <h3>No tickets in the queue</h3>
        <p>Create the first request to watch the event-driven prediction flow.</p>
      </div>
    );
  }

  return (
    <div className="table-scroll">
      <table>
        <caption className="visually-hidden">
          Support tickets with current status and machine-learning prediction
        </caption>
        <thead>
          <tr>
            <th scope="col">Ticket</th>
            <th scope="col">Status</th>
            <th scope="col">Category</th>
            <th scope="col">Priority</th>
            <th scope="col">Confidence</th>
            <th scope="col">Created</th>
          </tr>
        </thead>
        <tbody>
          {tickets.map((ticket) => (
            <tr
              key={ticket.id}
              className={ticket.id === selectedId ? "selected-row" : undefined}
            >
              <td>
                <button
                  className="ticket-link"
                  type="button"
                  aria-pressed={ticket.id === selectedId}
                  onClick={() => onSelect(ticket)}
                >
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
                <Confidence ticket={ticket} delayed={delayedPredictionIds.has(ticket.id)} />
              </td>
              <td>
                <time dateTime={ticket.createdAt}>{new Date(ticket.createdAt).toLocaleString()}</time>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
