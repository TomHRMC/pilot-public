/**
 * useDeleteCustomer — DELETE /api/v1/customers/{customer_id}
 *
 * Location: apps/web/src/features/customers/hooks/useDeleteCustomer.ts
 *
 * FE-B24: Used by DeleteCustomerModal (confirm-as-turn pattern).
 *
 * RULE: Uses apiClient (never raw fetch).
 * RULE: onSuccess invalidates ["customers"] query family.
 *
 * DELETE /api/v1/customers/{customer_id} — verified in openapi_schema_map.md (FE-B24 pre-work).
 */

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@pilot/shared-api";

export function useDeleteCustomer() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (customerId: string): Promise<void> => {
      await apiClient.delete(`/api/v1/customers/${customerId}`);
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["customers"] });
    },
  });
}
