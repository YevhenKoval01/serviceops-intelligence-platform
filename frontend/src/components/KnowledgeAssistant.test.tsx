import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";

import { askKnowledge } from "../api";
import { KnowledgeAssistant } from "./KnowledgeAssistant";

vi.mock("../api", () => ({ askKnowledge: vi.fn() }));

const mockedAskKnowledge = vi.mocked(askKnowledge);

test("renders a grounded answer and its citations", async () => {
  const user = userEvent.setup();
  mockedAskKnowledge.mockResolvedValue({
    answer: "The ServiceOps knowledge base recommends:\n- Capture one correlation ID. [1]",
    grounded: true,
    indexVersion: "tfidf-extractive-1-abc123",
    citations: [
      {
        documentId: "technical-api-errors",
        title: "API error triage",
        section: "Safe diagnostics",
        revision: "2026-08-05",
        sourcePath: "knowledge/technical-api-errors.md",
        excerpt: "Capture one correlation ID.",
        relevance: 0.61,
      },
    ],
  });

  render(<KnowledgeAssistant />);
  await user.type(
    screen.getByLabelText("What do you need help with?"),
    "How should I investigate repeated API errors?",
  );
  await user.click(screen.getByRole("button", { name: "Find grounded answer" }));

  expect(await screen.findByText("Source-backed answer")).toBeInTheDocument();
  expect(screen.getByText("API error triage")).toBeInTheDocument();
  expect(screen.getByText(/Safe diagnostics/)).toBeInTheDocument();
  expect(mockedAskKnowledge).toHaveBeenCalledWith(
    "How should I investigate repeated API errors?",
  );
});
