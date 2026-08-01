import type { AuthSession, LoginResponse } from "./types";

const SESSION_KEY = "serviceops.auth.session";
export const AUTH_EXPIRED_EVENT = "serviceops:auth-expired";

export function loadSession(): AuthSession | null {
  const value = window.sessionStorage.getItem(SESSION_KEY);
  if (!value) {
    return null;
  }
  try {
    const session = JSON.parse(value) as Partial<AuthSession>;
    const expiration = typeof session.expiresAt === "string" ? Date.parse(session.expiresAt) : NaN;
    if (
      typeof session.accessToken !== "string" ||
      typeof session.expiresAt !== "string" ||
      typeof session.user?.username !== "string" ||
      !["VIEWER", "OPERATOR"].includes(session.user.role ?? "") ||
      !Number.isFinite(expiration) ||
      expiration <= Date.now()
    ) {
      clearSession();
      return null;
    }
    return session as AuthSession;
  } catch {
    clearSession();
    return null;
  }
}

export function storeSession(response: LoginResponse): AuthSession {
  const session: AuthSession = {
    accessToken: response.accessToken,
    expiresAt: response.expiresAt,
    user: response.user,
  };
  window.sessionStorage.setItem(SESSION_KEY, JSON.stringify(session));
  return session;
}

export function clearSession(): void {
  window.sessionStorage.removeItem(SESSION_KEY);
}

export function expireSession(): void {
  clearSession();
  window.dispatchEvent(new Event(AUTH_EXPIRED_EVENT));
}
