import { expireSession, loadSession } from "./auth";
import type {
  AuthenticatedUser,
  CreateTicketInput,
  LoginResponse,
  KnowledgeAnswer,
  Ticket,
  TicketStatus,
} from "./types";

export class ApiError extends Error {
  constructor(
    message: string,
    public readonly status: number,
  ) {
    super(message);
  }
}

async function request<T>(
  path: string,
  options?: RequestInit,
  authenticated = true,
): Promise<T> {
  const session = authenticated ? loadSession() : null;
  const response = await fetch(path, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(session ? { Authorization: `Bearer ${session.accessToken}` } : {}),
      ...options?.headers,
    },
  });
  if (!response.ok) {
    if (authenticated && response.status === 401) {
      expireSession();
    }
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

export function login(username: string, password: string): Promise<LoginResponse> {
  return request<LoginResponse>(
    "/api/auth/login",
    {
      method: "POST",
      body: JSON.stringify({ username, password }),
    },
    false,
  );
}

export function getCurrentUser(): Promise<AuthenticatedUser> {
  return request<AuthenticatedUser>("/api/auth/me");
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

export function askKnowledge(question: string): Promise<KnowledgeAnswer> {
  return request<KnowledgeAnswer>("/assistant/ask", {
    method: "POST",
    body: JSON.stringify({ question }),
  });
}
