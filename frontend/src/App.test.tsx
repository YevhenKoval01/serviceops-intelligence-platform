import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, vi } from "vitest";

import App from "./App";
import { listTickets, login } from "./api";
import { clearSession, storeSession } from "./auth";
import type { LoginResponse } from "./types";

vi.mock("./api", () => ({
  listTickets: vi.fn(),
  getTicket: vi.fn(),
  createTicket: vi.fn(),
  updateTicketStatus: vi.fn(),
  login: vi.fn(),
}));

const mockedListTickets = vi.mocked(listTickets);
const mockedLogin = vi.mocked(login);
const operatorLogin: LoginResponse = {
  accessToken: "signed-token",
  tokenType: "Bearer",
  expiresIn: 900,
  expiresAt: "2099-08-01T10:15:00Z",
  user: { username: "operator", role: "OPERATOR" },
};

beforeEach(() => {
  clearSession();
  storeSession(operatorLogin);
  mockedListTickets.mockReset();
  mockedLogin.mockReset();
});

test("renders the API error state", async () => {
  mockedListTickets.mockRejectedValue(new Error("Backend unavailable"));

  render(<App />);

  expect(await screen.findByText("Could not load tickets")).toBeInTheDocument();
  expect(screen.getByText("Backend unavailable")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Try again" })).toBeInTheDocument();
});

test("signs in and opens the role-aware operator workspace", async () => {
  const user = userEvent.setup();
  clearSession();
  mockedLogin.mockResolvedValue(operatorLogin);
  mockedListTickets.mockResolvedValue([]);

  render(<App />);

  expect(screen.getByRole("heading", { name: "Sign in to ServiceOps" })).toBeInTheDocument();
  await user.type(screen.getByLabelText("Username"), " operator ");
  await user.type(screen.getByLabelText("Password"), "operator_dev_2026");
  await user.click(screen.getByRole("button", { name: "Sign in" }));

  expect(await screen.findByRole("heading", { name: "Support tickets" })).toBeInTheDocument();
  expect(screen.getByText("operator")).toBeInTheDocument();
  expect(screen.getByText("Operator")).toBeInTheDocument();
  expect(mockedLogin).toHaveBeenCalledWith("operator", "operator_dev_2026");
});

test("shows a read-only workspace for viewers", async () => {
  clearSession();
  storeSession({
    ...operatorLogin,
    user: { username: "viewer", role: "VIEWER" },
  });
  mockedListTickets.mockResolvedValue([]);

  render(<App />);

  expect(await screen.findByText("Viewer access")).toBeInTheDocument();
  expect(screen.queryByRole("heading", { name: "Create a support ticket" })).not.toBeInTheDocument();
});
