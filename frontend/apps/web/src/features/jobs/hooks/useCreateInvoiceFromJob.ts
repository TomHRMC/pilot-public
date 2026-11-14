/**
 * useCreateInvoiceFromJob — TanStack mutation to create an invoice from a job
 *
 * Location: apps/web/src/features/jobs/hooks/useCreateInvoiceFromJob.ts
 *
 * POST /api/v1/invoices/ with { job_id }
 * Verified: InvoiceCreate has no required fields — job_id alone is sufficient.
 * onSuccess: navigate to /invoices/{id}
 */

import { useMutation } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { apiClient } from "@pilot/shared-api";

interface InvoiceCreateResponse {
  id: string;
  invoice_number: string;
  status_code: string;
  job_id: string | null;
  [key: string]: unknown;
}

export function useCreateInvoiceFromJob(jobId: string) {
  const router = useRouter();

  return useMutation({
    mutationFn: async (): Promise<InvoiceCreateResponse> => {
      const res = await apiClient.post("/api/v1/invoices/", {
        job_id: jobId,
      });
      return res.data as InvoiceCreateResponse;
    },
    onSuccess: (data) => {
      router.push(`/invoices/${data.id}`);
    },
  });
}
