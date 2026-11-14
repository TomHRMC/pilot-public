/**
 * useCreateCustomer — TanStack Query mutation for creating a new customer
 *
 * Location: apps/mobile/features/customers/hooks/useCreateCustomer.ts
 *
 * API: POST /api/v1/customers/
 * Body: { type, display_name, mobile_phone?, email? }
 * On success: invalidate customers query
 *
 * Per batch-mob-b7-design.md §F.2
 */

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@pilot/shared-api";

export interface CreateCustomerInput {
  type: "person" | "company";
  display_name: string;
  mobile_phone?: string;
  email?: string;
}

export interface CreatedCustomer {
  id: string;
  tenant_id: string;
  type: string;
  display_name: string;
  mobile_phone: string | null;
  email: string | null;
  is_active: boolean;
  created_at: string;
}

export function useCreateCustomer() {
  const queryClient = useQueryClient();

  return useMutation<CreatedCustomer, Error, CreateCustomerInput>({
    mutationFn: async (input: CreateCustomerInput) => {
      const { data } = await apiClient.post<CreatedCustomer>(
        "/api/v1/customers/",
        input,
      );
      return data;
    },
    onSuccess: () => {
      // Invalidate customers list so the new customer appears
      void queryClient.invalidateQueries({ queryKey: ["customers"] });
    },
  });
}
