export type TicketStatus = "OPEN" | "IN_PROGRESS" | "RESOLVED";
export type Priority = "LOW" | "MEDIUM" | "HIGH";
export type UserRole = "VIEWER" | "OPERATOR";

export interface AuthenticatedUser {
  username: string;
  role: UserRole;
}

export interface LoginResponse {
  accessToken: string;
  tokenType: "Bearer";
  expiresIn: number;
  expiresAt: string;
  user: AuthenticatedUser;
}

export interface AuthSession {
  accessToken: string;
  expiresAt: string;
  user: AuthenticatedUser;
}

export interface Ticket {
  id: string;
  title: string;
  description: string;
  status: TicketStatus;
  reportedPriority: Priority | null;
  predictedPriority: Priority | null;
  predictedCategory: string | null;
  predictionConfidence: number | null;
  modelVersion: string | null;
  createdAt: string;
  updatedAt: string;
  version: number;
}

export interface CreateTicketInput {
  title: string;
  description: string;
  reportedPriority: Priority | null;
}
