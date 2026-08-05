import { afterEach, vi } from "vitest";

import { ApiError, askKnowledge, listTickets } from "./api";
import { clearSession, loadSession, storeSession } from "./auth";

afterEach(() => {
  vi.unstubAllGlobals();
  clearSession();
});

test("uses RFC 7807 detail when an API request fails", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          title: "Validation failed",
          detail: "One or more request fields are invalid",
        }),
        {
          status: 400,
          headers: { "Content-Type": "application/problem+json" },
        },
      ),
    ),
  );

  await expect(listTickets()).rejects.toEqual(
    new ApiError("One or more request fields are invalid", 400),
  );
});

test("falls back to the HTTP status for a non-JSON error", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue(new Response("Unavailable", { status: 503 })),
  );

  await expect(listTickets()).rejects.toMatchObject({
    message: "Request failed with status 503",
    status: 503,
  });
});

test("adds the session bearer token to authenticated requests", async () => {
  storeSession({
    accessToken: "signed-token",
    tokenType: "Bearer",
    expiresIn: 900,
    expiresAt: "2099-08-01T10:15:00Z",
    user: { username: "operator", role: "OPERATOR" },
  });
  const fetchMock = vi.fn().mockResolvedValue(
    new Response("[]", { status: 200, headers: { "Content-Type": "application/json" } }),
  );
  vi.stubGlobal("fetch", fetchMock);

  await listTickets();

  expect(fetchMock).toHaveBeenCalledWith(
    "/api/tickets",
    expect.objectContaining({
      headers: expect.objectContaining({ Authorization: "Bearer signed-token" }),
    }),
  );
});

test("clears the session after an authenticated 401 response", async () => {
  storeSession({
    accessToken: "expired-token",
    tokenType: "Bearer",
    expiresIn: 900,
    expiresAt: "2099-08-01T10:15:00Z",
    user: { username: "operator", role: "OPERATOR" },
  });
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ detail: "A valid bearer token is required" }), {
        status: 401,
        headers: { "Content-Type": "application/problem+json" },
      }),
    ),
  );

  await expect(listTickets()).rejects.toMatchObject({ status: 401 });
  expect(loadSession()).toBeNull();
});

test("discards a stored session with an invalid expiration", () => {
  storeSession({
    accessToken: "signed-token",
    tokenType: "Bearer",
    expiresIn: 900,
    expiresAt: "not-a-timestamp",
    user: { username: "operator", role: "OPERATOR" },
  });

  expect(loadSession()).toBeNull();
});

test("sends knowledge questions through the authenticated same-origin route", async () => {
  storeSession({
    accessToken: "signed-token",
    tokenType: "Bearer",
    expiresIn: 900,
    expiresAt: "2099-08-01T10:15:00Z",
    user: { username: "viewer", role: "VIEWER" },
  });
  const fetchMock = vi.fn().mockResolvedValue(
    new Response(
      JSON.stringify({
        answer: "Grounded answer [1]",
        grounded: true,
        citations: [],
        indexVersion: "tfidf-extractive-1-abc123",
      }),
      { status: 200, headers: { "Content-Type": "application/json" } },
    ),
  );
  vi.stubGlobal("fetch", fetchMock);

  await askKnowledge("How should I triage an API error?");

  expect(fetchMock).toHaveBeenCalledWith(
    "/assistant/ask",
    expect.objectContaining({
      method: "POST",
      body: JSON.stringify({ question: "How should I triage an API error?" }),
      headers: expect.objectContaining({ Authorization: "Bearer signed-token" }),
    }),
  );
});
