import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";

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
