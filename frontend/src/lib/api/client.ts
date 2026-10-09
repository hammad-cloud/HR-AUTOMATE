import "server-only";

import { cookies } from "next/headers";

import type { ApiErrorBody } from "./types";

export const SESSION_COOKIE = "hrc_session";

const API_BASE_URL = process.env.API_BASE_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    public readonly code: string,
    message: string,
    public readonly requestId: string | null = null,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

type FetchOptions = Omit<RequestInit, "body"> & {
  body?: unknown;
  query?: Record<string, string | number | undefined | null>;
  /** Skip attaching the session token (used by login). */
  anonymous?: boolean;
};

/**
 * Server-side API client (Backend-for-Frontend pattern).
 *
 * The JWT lives in an httpOnly cookie that browser JavaScript can't read. Only server
 * components and Server Actions attach it when calling the FastAPI backend.
 */
export async function apiFetch<T>(path: string, options: FetchOptions = {}): Promise<T> {
  const { body, query, anonymous, headers, ...init } = options;

  const url = new URL(`/api/v1${path}`, API_BASE_URL);
  for (const [key, value] of Object.entries(query ?? {})) {
    if (value !== undefined && value !== null && value !== "") {
      url.searchParams.set(key, String(value));
    }
  }

  const requestHeaders = new Headers(headers);
  requestHeaders.set("Accept", "application/json");
  if (body !== undefined) requestHeaders.set("Content-Type", "application/json");
  if (!anonymous) {
    const token = (await cookies()).get(SESSION_COOKIE)?.value;
    if (token) requestHeaders.set("Authorization", `Bearer ${token}`);
  }

  let response: Response;
  try {
    response = await fetch(url, {
      ...init,
      headers: requestHeaders,
      body: body === undefined ? undefined : JSON.stringify(body),
      cache: "no-store",
    });
  } catch {
    throw new ApiError(503, "SERVICE_UNAVAILABLE", "The HR service is unreachable. Please try again.");
  }

  if (!response.ok) {
    const payload = (await response.json().catch(() => null)) as ApiErrorBody | null;
    throw new ApiError(
      response.status,
      payload?.error.code ?? "UNKNOWN_ERROR",
      payload?.error.message ?? "Unexpected error",
      payload?.error.request_id ?? null,
    );
  }
  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}
