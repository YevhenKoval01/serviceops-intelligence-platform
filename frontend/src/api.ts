import type { CreateTicketInput, Ticket, TicketStatus } from "./types";

export class ApiError extends Error {
  constructor(
    message: string,
    public readonly status: number,
  ) {
    super(message);
  }
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(path, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...options?.headers,
    },
  });
  if (!response.ok) {
    let message = `Request failed with status ${response.status}`;
    try {
      const problem = (await response.json()) as { detail?: string; title?: string };
      message = problem.detail ?? problem.title ?? message;
    } catch {
      // The HTTP status remains useful when the response is not JSON.
    }
    throw new ApiError(message, response.status);
  }
  return response.json() as Promise<T>;
}

export function listTickets(): Promise<Ticket[]> {
  return request<Ticket[]>("/api/tickets");
}

export function getTicket(id: string): Promise<Ticket> {
  return request<Ticket>(`/api/tickets/${id}`);
}

export function createTicket(input: CreateTicketInput): Promise<Ticket> {
  return request<Ticket>("/api/tickets", {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export function updateTicketStatus(id: string, status: TicketStatus): Promise<Ticket> {
  return request<Ticket>(`/api/tickets/${id}/status`, {
    method: "PATCH",
    body: JSON.stringify({ status }),
  });
}
