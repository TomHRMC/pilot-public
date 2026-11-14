/**
 * /signup/verify — Email verification step (PUBLIC — no JWT)
 *
 * Location: apps/web/src/app/signup/verify/page.tsx
 *
 * SIGNUP-GA-1 (ADR-0011): renders the VerifyEmailStep component which
 * confirms the Cognito verification code, auto-signs-in, then POSTs
 * /api/v1/signup (resolve-or-attach) and routes to /signup/legal.
 *
 * RULE 3: Lives outside (authed) group — no JWT guard (pre-login).
 */

"use client";

import { Suspense } from "react";
import { VerifyEmailStep } from "@/features/signup/components/VerifyEmailStep";

export default function SignupVerifyPage() {
  return (
    <Suspense fallback={null}>
      <VerifyEmailStep />
    </Suspense>
  );
}
