/**
 * useCreateCustomer — POST mutation hook
 *
 * Location: apps/web/src/features/customers/hooks/useCreateCustomer.ts
 *
 * RULE: Uses apiClient (never raw fetch).
 * RULE: onSuccess invalidates ["customers"] query family.
 */

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient, getApiProblem, type ApiProblem } from "@pilot/shared-api";
import type { CustomerResponse } from "./useCustomer";

export interface CustomerCreateRequest {
  type?: string;
  display_name: string;
  first_name?: string | null;
  last_name?: string | null;
  company_name?: string | null;
  email?: string | null;
  mobile_phone?: string | null;
  taxability_code?: string | null;
  // DLC-1: SMS offline consent attestation
  sms_attestation_checked?: boolean;
  sms_consent_ip_address?: string | null;
}

export interface UseCreateCustomerOptions {
  onError?: (problem: ApiProblem) => void;
}

export function useCreateCustomer(options?: UseCreateCustomerOptions) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (
      data: CustomerCreateRequest,
    ): Promise<CustomerResponse> => {
      const res = await apiClient.post("/api/v1/customers/", data);
      return res.data as CustomerResponse;
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["customers"] });
    },
    onError: (error) => {
      const problem = getApiProblem(error);
      options?.onError?.(problem);
    },
  });
}
