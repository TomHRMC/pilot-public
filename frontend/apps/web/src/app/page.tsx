/**
 * Root page — redirects to /dashboard (authenticated) or /login (unauthenticated)
 *
 * This is a server component. Client-side auth redirect is handled by
 * (authed)/layout.tsx RequireAuth. This page redirects directly to /dashboard
 * which will then redirect to /login if the user is not authenticated.
 */

import { redirect } from "next/navigation";

export default function RootPage() {
  redirect("/dashboard");
}
