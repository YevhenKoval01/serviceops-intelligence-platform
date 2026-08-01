import { useState } from "react";

import { login } from "../api";
import { storeSession } from "../auth";
import type { AuthSession } from "../types";

interface LoginFormProps {
  onAuthenticated: (session: AuthSession) => void;
}

export function LoginForm({ onAuthenticated }: LoginFormProps) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      const response = await login(username.trim(), password);
      onAuthenticated(storeSession(response));
    } catch (loginError) {
      setError(loginError instanceof Error ? loginError.message : "Could not sign in.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="login-page">
      <section className="login-card" aria-labelledby="sign-in-heading">
        <div className="login-brand" aria-hidden="true">
          SO
        </div>
        <p className="eyebrow">Protected operator workspace</p>
        <h1 id="sign-in-heading">Sign in to ServiceOps</h1>
        <p>Use your assigned account to access the live support queue.</p>

        <form onSubmit={handleSubmit} aria-busy={submitting}>
          <div className="form-field">
            <label htmlFor="username">Username</label>
            <input
              id="username"
              name="username"
              autoComplete="username"
              required
              maxLength={64}
              value={username}
              onChange={(event) => setUsername(event.target.value)}
            />
          </div>
          <div className="form-field">
            <label htmlFor="password">Password</label>
            <input
              id="password"
              name="password"
              type="password"
              autoComplete="current-password"
              required
              maxLength={200}
              value={password}
              onChange={(event) => setPassword(event.target.value)}
            />
          </div>
          {error && (
            <div className="inline-error" role="alert">
              {error}
            </div>
          )}
          <button className="primary-button login-button" type="submit" disabled={submitting}>
            {submitting ? "Signing in…" : "Sign in"}
          </button>
        </form>
      </section>
    </main>
  );
}
