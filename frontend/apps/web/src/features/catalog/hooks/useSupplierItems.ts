/**
 * useSupplierItems — TanStack Query hook for supplier item list (read-only)
 *
 * Location: apps/web/src/features/catalog/hooks/useSupplierItems.ts
 *
 * Endpoint: GET /api/v1/catalog/supplier-items
 * Query key: ['catalog-supplier-items']
 * Read-only — no mutations. Supplier items are synced by background process (Celery).
 */

import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@pilot/shared-api";

export interface SupplierItem {
  id: string;
  tenant_id: string | null;
  supplier_id: string;
  sku: string;
  name: string;
  description: string | null;
  uom_id: string;
  is_active: boolean;
}

export const SUPPLIER_ITEMS_QUERY_KEY = ["catalog-supplier-items"] as const;

export function useSupplierItems(search?: string) {
  return useQuery({
    queryKey: [...SUPPLIER_ITEMS_QUERY_KEY, search ?? ""] as const,
    queryFn: async (): Promise<SupplierItem[]> => {
      const params: Record<string, unknown> = {};
      if (search?.trim()) {
        params.search = search.trim();
      }
      const res = await apiClient.get("/api/v1/catalog/supplier-items", {
        params,
      });
      return res.data as SupplierItem[];
    },
    staleTime: 60_000,
  });
}
