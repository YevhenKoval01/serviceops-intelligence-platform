import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";

import type { Ticket } from "../types";
import { TicketTable } from "./TicketTable";

const ticket: Ticket = {
  id: "8db2ea90-b132-4ea8-92ad-8d95b2cc53e0",
  title: "Production API unavailable",
  description: "All requests return server errors.",
  status: "OPEN",
  reportedPriority: "HIGH",
  predictedPriority: "HIGH",
  predictedCategory: "TECHNICAL",
  predictionConfidence: 0.91,
  modelVersion: "baseline-1",
  createdAt: "2026-07-30T10:00:00Z",
  updatedAt: "2026-07-30T10:00:01Z",
  version: 1,
};

test("renders ticket prediction fields in the queue", () => {
  render(<TicketTable tickets={[ticket]} selectedId={null} onSelect={vi.fn()} />);

  expect(screen.getByText("Production API unavailable")).toBeInTheDocument();
  expect(screen.getByText("Technical")).toBeInTheDocument();
  expect(screen.getByText("High")).toBeInTheDocument();
  expect(screen.getByText("91%")).toBeInTheDocument();
});

test("opens a ticket from a keyboard-accessible button", async () => {
  const user = userEvent.setup();
  const onSelect = vi.fn();
  render(<TicketTable tickets={[ticket]} selectedId={null} onSelect={onSelect} />);

  await user.click(screen.getByRole("button", { name: /Production API unavailable/ }));

  expect(onSelect).toHaveBeenCalledWith(ticket);
});

test("renders empty and delayed-prediction states", () => {
  const { rerender } = render(
    <TicketTable tickets={[]} selectedId={null} onSelect={vi.fn()} />,
  );
  expect(screen.getByRole("status")).toHaveTextContent("No tickets in the queue");

  rerender(
    <TicketTable
      tickets={[
        {
          ...ticket,
          predictedCategory: null,
          predictedPriority: null,
          predictionConfidence: null,
          modelVersion: null,
        },
      ]}
      selectedId={null}
      onSelect={vi.fn()}
      delayedPredictionIds={new Set([ticket.id])}
    />,
  );
  expect(screen.getByText("Delayed")).toBeInTheDocument();
});
