import { redirect } from "next/navigation";

export default function SyncPage() {
  redirect("/settings/sync-storage/background-sync");
}
