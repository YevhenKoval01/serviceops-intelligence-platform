import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";

import { updateTicketStatus } from "../api";
import type { Ticket } from "../types";
import { TicketDetail } from "./TicketDetail";

vi.mock("../api", () => ({
  updateTicketStatus: vi.fn(),
}));

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

test("updates status and announces success", async () => {
  const user = userEvent.setup();
  const updated = { ...ticket, status: "IN_PROGRESS" as const, version: 2 };
  vi.mocked(updateTicketStatus).mockResolvedValue(updated);
  const onUpdated = vi.fn();

  render(<TicketDetail ticket={ticket} onUpdated={onUpdated} onClose={vi.fn()} />);
  await user.selectOptions(screen.getByLabelText("Update status"), "IN_PROGRESS");

  expect(await screen.findByText("Status updated to In progress.")).toBeInTheDocument();
  expect(onUpdated).toHaveBeenCalledWith(updated);
});

test("closes the modal with Escape", async () => {
  const user = userEvent.setup();
  const onClose = vi.fn();

  render(<TicketDetail ticket={ticket} onUpdated={vi.fn()} onClose={onClose} />);
  await user.keyboard("{Escape}");

  expect(onClose).toHaveBeenCalledOnce();
});
