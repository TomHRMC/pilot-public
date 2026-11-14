import { InvoiceBuilderPage } from "@/features/invoices/components/InvoiceBuilderPage";

interface PageProps {
  searchParams: { job_id?: string };
}

export default function InvoicesNewPage({ searchParams }: PageProps) {
  return <InvoiceBuilderPage jobId={searchParams.job_id ?? null} />;
}
