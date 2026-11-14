/**
 * /signup — Entry redirect to /signup/account
 * Location: apps/web/src/app/signup/page.tsx
 */

import { redirect } from "next/navigation";

export default function SignupPage() {
  redirect("/signup/account");
}
