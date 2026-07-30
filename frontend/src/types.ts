export type TicketStatus = "OPEN" | "IN_PROGRESS" | "RESOLVED";
export type Priority = "LOW" | "MEDIUM" | "HIGH";

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
