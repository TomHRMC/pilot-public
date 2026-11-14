// LAUNCH-DRAFT COPY — written for a launch that never happened; Pilot for Trades
// was never released. See PROVENANCE.md and frontend/apps/marketing/README.md.
import { redirect } from "next/navigation";

export default function EarlyAccessPage() {
  // 308 permanent redirect to /charter — preserves inbound link equity (GTM §9.2).
  // The route is kept because inbound links exist; the content lives at /charter now.
  redirect("/charter");
}
