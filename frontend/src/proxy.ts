import { NextResponse, type NextRequest } from "next/server";

const SESSION_COOKIE = "hrc_session";
const PUBLIC_PATHS = ["/login"];

/**
 * Optimistic redirect only: checks that a session cookie exists, not that it is valid.
 * Real verification happens in the API on every request.
 */
export function proxy(request: NextRequest) {
  const { pathname } = request.nextUrl;
  const hasSession = request.cookies.has(SESSION_COOKIE);
  const isPublic = PUBLIC_PATHS.some((p) => pathname.startsWith(p));

  if (pathname === "/logout") return NextResponse.next();
  if (!hasSession && !isPublic) {
    return NextResponse.redirect(new URL("/login", request.url));
  }
  if (hasSession && isPublic) {
    return NextResponse.redirect(new URL("/dashboard", request.url));
  }
  return NextResponse.next();
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|ico)$).*)"],
};
