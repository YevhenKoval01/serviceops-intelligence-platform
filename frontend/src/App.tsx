import { useCallback, useEffect, useState } from "react";

import { getTicket, listTickets } from "./api";
import { CreateTicketForm } from "./components/CreateTicketForm";
import { TicketDetail } from "./components/TicketDetail";
import { TicketTable } from "./components/TicketTable";
import type { Ticket } from "./types";

const POLL_ATTEMPTS = 30;
const POLL_INTERVAL_MS = 1000;

export default function App() {
  const [tickets, setTickets] = useState<Ticket[]>([]);
  const [selected, setSelected] = useState<Ticket | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadTickets = useCallback(async () => {
    try {
      const result = await listTickets();
      setTickets(result);
      setError(null);
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "The ticket queue is unavailable.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadTickets();
  }, [loadTickets]);

  function mergeTicket(updated: Ticket) {
    setTickets((current) => {
      const exists = current.some((ticket) => ticket.id === updated.id);
      if (!exists) {
        return [updated, ...current];
      }
      return current.map((ticket) => (ticket.id === updated.id ? updated : ticket));
    });
    setSelected((current) => (current?.id === updated.id ? updated : current));
  }

  async function pollForPrediction(ticketId: string) {
    for (let attempt = 0; attempt < POLL_ATTEMPTS; attempt += 1) {
      await new Promise((resolve) => window.setTimeout(resolve, POLL_INTERVAL_MS));
      try {
        const updated = await getTicket(ticketId);
        mergeTicket(updated);
        if (updated.predictedCategory && updated.predictedPriority) {
          return;
        }
      } catch {
        // A later attempt can recover from a brief service or network interruption.
      }
    }
  }

  function handleCreated(ticket: Ticket) {
    mergeTicket(ticket);
    setSelected(ticket);
    void pollForPrediction(ticket.id);
  }

  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="brand">
          <span className="brand-mark">SO</span>
          <div>
            <strong>ServiceOps Intelligence</strong>
            <span>Operator workspace</span>
          </div>
        </div>
        <div className="system-state">
          <span className="state-dot" aria-hidden="true" />
          Event pipeline active
        </div>
      </header>

      <main>
        <section className="intro">
          <div>
            <p className="eyebrow">Operations queue</p>
            <h1>Turn incoming issues into clear priorities.</h1>
            <p>
              Tickets are stored immediately, then classified through the Kafka prediction
              pipeline without blocking the operator.
            </p>
          </div>
          <div className="queue-stat" aria-label={`${tickets.length} tickets in queue`}>
            <span>Queue volume</span>
            <strong>{tickets.length.toString().padStart(2, "0")}</strong>
          </div>
        </section>

        <CreateTicketForm onCreated={handleCreated} />

        <section className="queue-panel" aria-labelledby="ticket-queue-heading">
          <div className="section-heading">
            <div>
              <p className="eyebrow">Live queue</p>
              <h2 id="ticket-queue-heading">Support tickets</h2>
            </div>
            <button className="secondary-button" type="button" onClick={() => void loadTickets()}>
              Refresh
            </button>
          </div>

          {loading ? (
            <div className="loading-state" role="status">
              Loading ticket queue…
            </div>
          ) : error ? (
            <div className="error-state" role="alert">
              <strong>Could not load tickets</strong>
              <span>{error}</span>
              <button className="secondary-button" type="button" onClick={() => void loadTickets()}>
                Try again
              </button>
            </div>
          ) : (
            <TicketTable
              tickets={tickets}
              selectedId={selected?.id ?? null}
              onSelect={setSelected}
            />
          )}
        </section>
      </main>

      {selected && (
        <TicketDetail
          ticket={selected}
          onUpdated={mergeTicket}
          onClose={() => setSelected(null)}
        />
      )}
    </div>
  );
}
