/**
 * useHelpArticle — TanStack Query — FE-B16
 *
 * Location: apps/web/src/features/help/hooks/useHelpArticle.ts
 *
 * GET /api/v1/help/articles/{article_id}
 */

import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@pilot/shared-api";
import type { HelpArticleResponse } from "../types";

async function fetchHelpArticle(
  articleId: string,
): Promise<HelpArticleResponse> {
  const res = await apiClient.get<HelpArticleResponse>(
    `/api/v1/help/articles/${articleId}`,
  );
  return res.data;
}

export function useHelpArticle(articleId: string | null) {
  return useQuery({
    queryKey: ["help", "articles", articleId],
    queryFn: () => fetchHelpArticle(articleId!),
    enabled: !!articleId,
    staleTime: 10 * 60 * 1000, // 10 minutes — articles update infrequently
  });
}
