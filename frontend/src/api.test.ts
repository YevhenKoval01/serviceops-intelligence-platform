import { afterEach, vi } from "vitest";

import { ApiError, listTickets } from "./api";

afterEach(() => {
  vi.unstubAllGlobals();
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
