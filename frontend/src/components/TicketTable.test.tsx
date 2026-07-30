import { render, screen } from "@testing-library/react";
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
