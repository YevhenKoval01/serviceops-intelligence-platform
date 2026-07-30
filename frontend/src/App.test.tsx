import { render, screen } from "@testing-library/react";
import { beforeEach, vi } from "vitest";

import App from "./App";
import { listTickets } from "./api";

vi.mock("./api", () => ({
  listTickets: vi.fn(),
  getTicket: vi.fn(),
  createTicket: vi.fn(),
  updateTicketStatus: vi.fn(),
}));

const mockedListTickets = vi.mocked(listTickets);

beforeEach(() => {
  mockedListTickets.mockReset();
});

test("renders the API error state", async () => {
  mockedListTickets.mockRejectedValue(new Error("Backend unavailable"));

  render(<App />);

  expect(await screen.findByText("Could not load tickets")).toBeInTheDocument();
  expect(screen.getByText("Backend unavailable")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Try again" })).toBeInTheDocument();
});
