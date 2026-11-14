/**
 * useUpdateCustomer — PATCH mutation hook
 *
 * Location: apps/web/src/features/customers/hooks/useUpdateCustomer.ts
 *
 * RULE: Uses apiClient (never raw fetch).
 * RULE: onSuccess invalidates ["customer", customerId] AND ["customers"].
 */

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@pilot/shared-api";
import type { CustomerResponse } from "./useCustomer";
import type { CustomerCreateRequest } from "./useCreateCustomer";

// PATCH uses the same shape as CustomerCreate (backend uses CustomerCreate for both)
export type CustomerUpdateRequest = Partial<CustomerCreateRequest>;

export function useUpdateCustomer(customerId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (
      data: CustomerUpdateRequest,
    ): Promise<CustomerResponse> => {
      const res = await apiClient.patch(
        `/api/v1/customers/${customerId}`,
        data,
      );
      return res.data as CustomerResponse;
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey: ["customer", customerId],
      });
      void queryClient.invalidateQueries({ queryKey: ["customers"] });
    },
  });
}
