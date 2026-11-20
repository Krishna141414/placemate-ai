import { NextResponse, type NextRequest } from "next/server";

// Optimistic check only: no session cookie means "go to login". The real
// checks (a valid token, the right role) happen in the backend on every API
// call, and the app shell shows a 403 page when the role does not fit.

const SESSION_COOKIE = "pm_session";
const APP_ROUTES = [
  "/dashboard",
  "/ask",
  "/eligibility",
  "/resume",
  "/agent",
  "/applications",
  "/documents",
  "/analytics",
  "/evaluation",
  "/security",
];

export function proxy(request: NextRequest) {
  const { pathname, search } = request.nextUrl;
  const protectedRoute = APP_ROUTES.some((route) => pathname === route || pathname.startsWith(`${route}/`));
  if (protectedRoute && !request.cookies.has(SESSION_COOKIE)) {
    const url = new URL("/login", request.url);
    url.searchParams.set("next", `${pathname}${search}`);
    return NextResponse.redirect(url);
  }
  return NextResponse.next();
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico|.*\\.(?:png|svg|jpg|json|ico|webp)$).*)"],
};
