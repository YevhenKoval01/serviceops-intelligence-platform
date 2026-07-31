import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";

import { createTicket } from "../api";
import type { Ticket } from "../types";
import { CreateTicketForm } from "./CreateTicketForm";

vi.mock("../api", () => ({
  createTicket: vi.fn(),
}));

test("shows client-side validation errors for an incomplete ticket", async () => {
  const user = userEvent.setup();
  render(<CreateTicketForm onCreated={vi.fn()} />);

  await user.click(screen.getByRole("button", { name: "Create ticket" }));

  expect(screen.getByText("Use at least 5 characters.")).toBeInTheDocument();
  expect(screen.getByText("Use at least 10 characters.")).toBeInTheDocument();
});

test("trims valid input, creates a ticket, and announces success", async () => {
  const user = userEvent.setup();
  const ticket = {
    id: "8db2ea90-b132-4ea8-92ad-8d95b2cc53e0",
    title: "VPN access fails",
    description: "The employee cannot connect to the corporate VPN.",
    status: "OPEN",
    reportedPriority: "HIGH",
    predictedPriority: null,
    predictedCategory: null,
    predictionConfidence: null,
    modelVersion: null,
    createdAt: "2026-07-30T10:00:00Z",
    updatedAt: "2026-07-30T10:00:00Z",
    version: 0,
  } satisfies Ticket;
  vi.mocked(createTicket).mockResolvedValue(ticket);
  const onCreated = vi.fn();
  render(<CreateTicketForm onCreated={onCreated} />);

  await user.type(screen.getByLabelText("Title"), "  VPN access fails  ");
  await user.type(
    screen.getByLabelText("Description"),
    "  The employee cannot connect to the corporate VPN.  ",
  );
  await user.selectOptions(screen.getByLabelText("Reported priority"), "HIGH");
  await user.click(screen.getByRole("button", { name: "Create ticket" }));

  expect(await screen.findByText("Ticket created. Prediction is now in progress.")).toBeInTheDocument();
  expect(createTicket).toHaveBeenCalledWith({
    title: "VPN access fails",
    description: "The employee cannot connect to the corporate VPN.",
    reportedPriority: "HIGH",
  });
  expect(onCreated).toHaveBeenCalledWith(ticket);
  expect(screen.getByLabelText("Title")).toHaveFocus();
});

test("renders a server error without clearing the entered request", async () => {
  const user = userEvent.setup();
  vi.mocked(createTicket).mockRejectedValue(new Error("Backend unavailable"));
  render(<CreateTicketForm onCreated={vi.fn()} />);

  await user.type(screen.getByLabelText("Title"), "VPN access fails");
  await user.type(
    screen.getByLabelText("Description"),
    "The employee cannot connect to the corporate VPN.",
  );
  await user.click(screen.getByRole("button", { name: "Create ticket" }));

  expect(await screen.findByRole("alert")).toHaveTextContent("Backend unavailable");
  expect(screen.getByLabelText("Title")).toHaveValue("VPN access fails");
});
