/**
 * useCustomer — single customer fetch
 *
 * Location: apps/web/src/features/customers/hooks/useCustomer.ts
 *
 * RULE: Uses apiClient (never raw fetch).
 * RULE: Query key is ["customer", customerId].
 * RULE: enabled: !!customerId — do not fetch if undefined.
 */

import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@pilot/shared-api";

export interface CustomerResponse {
  id: string;
  tenant_id: string;
  type: string;
  display_name: string;
  first_name: string | null;
  last_name: string | null;
  company_name: string | null;
  email: string | null;
  mobile_phone: string | null;
  is_active: boolean;
  taxability_code: string | null;
  sms_opted_out: boolean;
  sms_opt_out_at: string | null;
  sms_opt_in_consent: boolean;
  sms_opt_in_at: string | null;
  sms_opt_in_source: string | null;
}

export const CUSTOMER_QUERY_KEY = (customerId: string | undefined) =>
  ["customer", customerId] as const;

export function useCustomer(customerId: string | undefined) {
  return useQuery({
    queryKey: CUSTOMER_QUERY_KEY(customerId),
    queryFn: async (): Promise<CustomerResponse> => {
      const res = await apiClient.get(`/api/v1/customers/${customerId!}`);
      return res.data as CustomerResponse;
    },
    enabled: !!customerId,
    staleTime: 60_000,
  });
}
