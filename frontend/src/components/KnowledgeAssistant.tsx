import { FormEvent, useState } from "react";

import { askKnowledge } from "../api";
import type { KnowledgeAnswer } from "../types";

export function KnowledgeAssistant() {
  const [question, setQuestion] = useState("");
  const [result, setResult] = useState<KnowledgeAnswer | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const normalized = question.trim();
    if (normalized.length < 5) {
      return;
    }
    setLoading(true);
    setError(null);
    try {
      setResult(await askKnowledge(normalized));
    } catch (requestError) {
      setResult(null);
      setError(
        requestError instanceof Error
          ? requestError.message
          : "The knowledge assistant is unavailable.",
      );
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="knowledge-panel" aria-labelledby="knowledge-heading">
      <div className="section-heading">
        <div>
          <p className="eyebrow">Grounded guidance</p>
          <h2 id="knowledge-heading">Knowledge assistant</h2>
        </div>
        <span className="citation-note">Citations required</span>
      </div>
      <p className="knowledge-intro">
        Ask about supported access, billing, delivery, API, performance, or incident
        procedures. The assistant answers only from the bundled ServiceOps runbooks.
      </p>
      <form onSubmit={(event) => void handleSubmit(event)}>
        <div className="form-field knowledge-question">
          <label htmlFor="knowledge-question">What do you need help with?</label>
          <textarea
            id="knowledge-question"
            maxLength={500}
            value={question}
            placeholder="For example: What should I capture when multiple customers receive HTTP 500 errors?"
            onChange={(event) => setQuestion(event.target.value)}
          />
          <span className="character-count">{question.length}/500</span>
        </div>
        <button
          className="primary-button"
          type="submit"
          disabled={loading || question.trim().length < 5}
        >
          {loading ? "Searching…" : "Find grounded answer"}
        </button>
      </form>

      {error && (
        <div className="inline-error knowledge-message" role="alert">
          {error}
        </div>
      )}

      {result && (
        <div className={`knowledge-result ${result.grounded ? "" : "knowledge-abstention"}`}>
          <h3>{result.grounded ? "Source-backed answer" : "Human review needed"}</h3>
          <p className="knowledge-answer">{result.answer}</p>
          {result.citations.length > 0 && (
            <div className="knowledge-sources">
              <h3>Sources</h3>
              <ol>
                {result.citations.map((citation) => (
                  <li key={`${citation.documentId}-${citation.section}`}>
                    <strong>{citation.title}</strong>
                    <span>
                      {citation.section} · revision {citation.revision}
                    </span>
                    <p>{citation.excerpt}</p>
                  </li>
                ))}
              </ol>
            </div>
          )}
        </div>
      )}
    </section>
  );
}
