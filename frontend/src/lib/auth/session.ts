import "server-only";

import { redirect } from "next/navigation";
import { cache } from "react";

import { ApiError, apiFetch } from "@/lib/api/client";
import type { CurrentUser, Role } from "@/lib/api/types";

/** The signed-in user, fetched once per request and shared by every server component. */
export const getCurrentUser = cache(async (): Promise<CurrentUser | null> => {
  try {
    return await apiFetch<CurrentUser>("/auth/me");
  } catch (error) {
    if (error instanceof ApiError && error.status === 401) return null;
    throw error;
  }
});

export async function requireUser(): Promise<CurrentUser> {
  const user = await getCurrentUser();
  // Via /logout so an expired cookie is cleared rather than bouncing between pages.
  if (!user) redirect("/logout");
  return user;
}

/**
 * UX-level route guard. The API re-checks every request, so this only spares users a
 * screen they can't use; it is not the security boundary.
 */
export async function requireRole(...roles: Role[]): Promise<CurrentUser> {
  const user = await requireUser();
  if (!roles.includes(user.role)) redirect("/dashboard?denied=1");
  return user;
}
