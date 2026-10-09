"use server";

import { cookies } from "next/headers";
import { redirect } from "next/navigation";

import { ApiError, apiFetch, SESSION_COOKIE } from "@/lib/api/client";
import type { ActionResult } from "@/lib/api/types";
import { PERSONAS } from "@/lib/demo-personas";

interface TokenResponse {
  access_token: string;
  expires_in: number;
}

export interface LoginState {
  error?: string;
  email?: string;
}

async function setSession(token: TokenResponse): Promise<void> {
  (await cookies()).set(SESSION_COOKIE, token.access_token, {
    httpOnly: true,
    sameSite: "lax",
    secure: process.env.NODE_ENV === "production",
    path: "/",
    maxAge: token.expires_in,
  });
}

export async function loginAction(_: LoginState, formData: FormData): Promise<LoginState> {
  const demo = String(formData.get("demo") ?? "");
  // Persona buttons sign in server-side; only seeded demo emails may use DEMO_PASSWORD.
  if (demo && !(process.env.DEMO_PASSWORD && PERSONAS.some((p) => p.email === demo))) {
    return { error: "Demo sign-in is not configured." };
  }
  const email = demo || String(formData.get("email") ?? "").trim();
  const password = demo ? process.env.DEMO_PASSWORD! : String(formData.get("password") ?? "");
  if (!email || !password) return { error: "Enter your email and password.", email };

  try {
    const token = await apiFetch<TokenResponse>("/auth/login", {
      method: "POST",
      body: { email, password },
      anonymous: true,
    });
    await setSession(token);
  } catch (error) {
    const message =
      error instanceof ApiError && error.status === 401
        ? "Invalid email or password."
        : "Sign-in is temporarily unavailable. Please try again.";
    return { error: message, email };
  }
  redirect("/dashboard");
}

export async function changePasswordAction(input: {
  currentPassword: string;
  newPassword: string;
}): Promise<ActionResult> {
  try {
    // The API signs out every older session, including this one, and returns a fresh token.
    const token = await apiFetch<TokenResponse>("/auth/password", {
      method: "POST",
      body: { current_password: input.currentPassword, new_password: input.newPassword },
    });
    await setSession(token);
    return {
      ok: true,
      message: "Your password has been changed. Other devices have been signed out.",
    };
  } catch (error) {
    if (error instanceof ApiError) return { ok: false, error: error.message };
    return { ok: false, error: "Something went wrong. Please try again." };
  }
}

export async function logoutAction(): Promise<void> {
  (await cookies()).delete(SESSION_COOKIE);
  redirect("/login");
}
