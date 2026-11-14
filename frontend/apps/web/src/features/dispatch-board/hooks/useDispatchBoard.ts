/**
 * useDispatchBoard — TanStack Query hook for the dispatch board
 *
 * Location: apps/web/src/features/dispatch-board/hooks/useDispatchBoard.ts
 *
 * GET /api/v1/scheduling/dispatch-board?start_date=&end_date=
 * Backend requires ISO 8601 datetime format for both params.
 *
 * Real API returns: { techs: DispatchBoardTechGroup[], unassigned: DispatchBoardJobEntry[] }
 * This hook normalizes to { techs: DispatchBoardTech[], jobs: DispatchBoardJob[] }
 * that the component tree expects.
 *
 * Per batch-fe-b4-design.md §A.2.7
 * Updated per batch-beta-v1-fixes-b5-design.md — added endDate parameter
 * to support 4-Day, Week, and Month multi-day views.
 */

import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@pilot/shared-api";
import type {
  DispatchBoardResponse,
  DispatchBoardJob,
  DispatchBoardTech,
} from "../types-stub";

/** Convert a YYYY-MM-DD date string to ISO 8601 datetime (start or end of day UTC) */
function toIsoDatetime(dateStr: string, endOfDay = false): string {
  const suffix = endOfDay ? "T23:59:59Z" : "T00:00:00Z";
  return `${dateStr}${suffix}`;
}

// ─── Raw API shapes (real backend response) ───────────────────────────────────

interface RawJobEntry {
  id: string;
  tenant_id: string;
  customer_id: string;
  site_id: string;
  status_id: string;
  scheduled_start_at: string | null;
  scheduled_end_at: string | null;
  estimated_duration_minutes: number | null;
  external_calendar_event_id: string | null;
  is_active: boolean;
  eta_minutes?: number | null;
  // DISPATCH-B1 enrichment fields (present in board response, absent in pre-B1)
  customer_name?: string | null;
  title?: string | null;
  job_number?: string | null;
  site_address?: string | null;
  // DISPATCH-B1.5: site_name from Part A backend enrichment (e.g. "Main Office").
  // Optional — boards from pre-B1.5 backends will omit this field; normalizeJob
  // gracefully falls back to null so no display breaks.
  site_name?: string | null;
  primary_assignment_id?: string | null;
  version?: number;
  assignment_version?: number | null;
  // DISPATCH-B1.25: role of this placement in the context it's returned
  assignment_role?: string | null;
  // DISPATCH-B3: real classification fields from CLASS-B1 backend enrichment
  priority?: string | null;
  customer_type?: string | null;
  site_type?: string | null;
  job_type_code?: string | null;
  job_type_label?: string | null;
}

interface RawTechGroup {
  tech_id: string;
  id: string;
  name: string;
  display_color: string | null;
  avatar_url: string | null;
  jobs: RawJobEntry[];
  eta_minutes_to_first_job?: number | null;
  // DISPATCH-B1.25: non-primary assignments for this tech
  additional_job_commitments?: RawJobEntry[];
}

interface RawDispatchBoardResponse {
  start_date: string;
  end_date: string;
  techs: RawTechGroup[];
  unassigned: RawJobEntry[];
}

// ─── Normalization helpers ────────────────────────────────────────────────────

/**
 * Normalized job shape that carries through DISPATCH-B1 server-side fields.
 * The extra fields (primary_assignment_id, version, assignment_version) are not
 * on DispatchBoardJob but are needed by DispatchBoardPage for staleness checks
 * and the unassigned-tray filter. They are accessed via type-cast at usage sites.
 *
 * DISPATCH-B1.25: also carries assignment_role for badge display.
 */
type NormalizedJob = DispatchBoardJob & {
  primary_assignment_id: string | null;
  version: number;
  assignment_version: number | null;
  assignment_role: string | null;
};

function normalizeJob(
  raw: RawJobEntry,
  techId: string | null,
  techColor: string | null = null,
): NormalizedJob {
  // DISPATCH-B1: customer_name, title, and job_number are now returned directly
  // in the board response for both assigned (tech.jobs) and unassigned entries.
  // Prefer job_number for display label (matches existing enrichJob pattern).
  const title = raw.job_number ? `Job #${raw.job_number}` : (raw.title ?? "");
  const customer_name = raw.customer_name ?? "";

  return {
    id: raw.id,
    title,
    customer_name,
    // DISPATCH-B1: site_address is returned directly by the board response.
    // Fallback to "" keeps display safe when the board pre-dates B1.
    site_address: raw.site_address ?? "",
    // DISPATCH-B1.5: site_name from Part A backend enrichment.
    // Fallback to null when the board pre-dates B1.5 (field absent in older responses).
    site_name: raw.site_name ?? null,
    scheduled_start_at: raw.scheduled_start_at ?? "",
    scheduled_end_at: raw.scheduled_end_at ?? "",
    tech_id: techId,
    status: techId
      ? raw.scheduled_start_at
        ? "scheduled"
        : "unassigned"
      : "unassigned",
    // DISPATCH-B3: read real values from CLASS-B1 enriched board response.
    // "standard" is the null-safety fallback only — every real job now has a value.
    priority:
      (raw.priority as "standard" | "urgent" | "emergency") ?? "standard",
    customer_type: (raw.customer_type as "person" | "company") ?? null,
    site_type:
      (raw.site_type as "commercial" | "residential" | "industrial") ?? null,
    job_type_code: raw.job_type_code ?? null,
    job_type_label: raw.job_type_label ?? null,
    updated_at: raw.scheduled_start_at ?? new Date().toISOString(),
    display_color: techColor ?? undefined,
    // Pass through B1 version fields for staleness check and unassigned detection
    primary_assignment_id: raw.primary_assignment_id ?? null,
    version: raw.version ?? 1,
    assignment_version: raw.assignment_version ?? null,
    // DISPATCH-B1.25: carry assignment_role for badge display
    assignment_role: raw.assignment_role ?? null,
  };
}

function normalizeTech(
  raw: RawTechGroup,
  commitments: NormalizedJob[],
): DispatchBoardTech {
  return {
    id: raw.id,
    tech_id: raw.tech_id,
    name: raw.name,
    display_color: raw.display_color,
    avatar_url: raw.avatar_url,
    eta_minutes_to_first_job: raw.eta_minutes_to_first_job,
    // DISPATCH-B1.25: non-primary commitments carried per tech (not flattened into jobs[])
    commitments,
  };
}

interface RawJobListItem {
  id: string;
  customer_name: string | null;
  job_number: string | null;
  status_code: string | null;
}

interface PaginatedJobListResponse {
  items: RawJobListItem[];
  total: number;
  limit: number;
  offset: number;
}

async function fetchDispatchBoard(
  startDate: string,
  endDate: string,
): Promise<DispatchBoardResponse> {
  const startDateIso = toIsoDatetime(startDate);
  const endDateIso = toIsoDatetime(endDate, true);

  // Fetch board and job metadata in parallel.
  // The secondary /api/v1/jobs/ call is a legacy fallback for pre-DISPATCH-B1
  // board responses that do not carry customer_name/job_number inline.
  // For multi-day ranges (week view) we omit the scheduled_date filter so all
  // jobs in the date window are eligible for enrichment regardless of day.
  const [boardRes, jobsRes] = await Promise.all([
    apiClient.get<RawDispatchBoardResponse>(
      `/api/v1/scheduling/dispatch-board?start_date=${encodeURIComponent(startDateIso)}&end_date=${encodeURIComponent(endDateIso)}`,
    ),
    apiClient
      .get<PaginatedJobListResponse>(
        `/api/v1/jobs/?scheduled_from=${encodeURIComponent(startDateIso)}&scheduled_to=${encodeURIComponent(endDateIso)}&limit=200`,
      )
      .catch(() => ({
        data: {
          items: [],
          total: 0,
          limit: 200,
          offset: 0,
        } as PaginatedJobListResponse,
      })), // non-blocking — board renders even if secondary metadata fails
  ]);

  const raw = boardRes.data;

  // Build a lookup map from job metadata for legacy enrichment fallback.
  // Guard handles both paginated shape { items: [...] } and legacy plain array.
  const jobMeta = new Map<string, RawJobListItem>();
  const jobItems: RawJobListItem[] = Array.isArray(jobsRes.data)
    ? jobsRes.data
    : (jobsRes.data?.items ?? []);
  for (const j of jobItems) {
    jobMeta.set(j.id, j);
  }

  // enrichJob fills customer_name/title from the secondary jobs list ONLY when
  // normalizeJob() couldn't populate them from inline B1 fields (i.e. title is
  // still empty after normalization — covers pre-B1 board endpoints).
  function enrichJob(job: NormalizedJob): NormalizedJob {
    if (job.title && job.customer_name) return job; // B1 fields already present
    const meta = jobMeta.get(job.id);
    if (!meta) return job;
    return {
      ...job,
      title: meta.job_number ? `Job #${meta.job_number}` : job.title,
      customer_name: meta.customer_name ?? job.customer_name,
    };
  }

  // DISPATCH-B1.25: Build commitment chips per tech (non-primary assignments).
  // Do NOT add these to jobs[] — jobs[] stays primary-only (lane/month/week-lane flatten it).
  const commitmentsByTechId = new Map<string, NormalizedJob[]>();
  for (const group of raw.techs ?? []) {
    const techCommitments = (group.additional_job_commitments ?? []).map(
      (job) => enrichJob(normalizeJob(job, group.id, group.display_color)),
    );
    commitmentsByTechId.set(group.id, techCommitments);
  }

  // Normalize techs — pass commitments so DispatchGridDayView can render chips
  const techs: DispatchBoardTech[] = (raw.techs ?? []).map((group) =>
    normalizeTech(group, commitmentsByTechId.get(group.id) ?? []),
  );

  // Flatten assigned jobs from each tech group, enriched with display metadata.
  // PRIMARY jobs only — commitments are NOT flattened here.
  const assignedJobs: NormalizedJob[] = (raw.techs ?? []).flatMap((group) =>
    (group.jobs ?? []).map((job) =>
      enrichJob(normalizeJob(job, group.id, group.display_color)),
    ),
  );

  // Flatten unassigned jobs, enriched with display metadata
  const unassignedJobs: NormalizedJob[] = (raw.unassigned ?? []).map((job) =>
    enrichJob(normalizeJob(job, null)),
  );

  return {
    date: startDate,
    techs,
    jobs: [...assignedJobs, ...unassignedJobs] as DispatchBoardJob[],
  };
}

export const DISPATCH_BOARD_QUERY_KEY = (startDate: string, endDate: string) =>
  ["dispatch-board", startDate, endDate] as const;

export function useDispatchBoard(startDate: string, endDate: string) {
  return useQuery({
    queryKey: DISPATCH_BOARD_QUERY_KEY(startDate, endDate),
    queryFn: () => fetchDispatchBoard(startDate, endDate),
    staleTime: 30_000, // 30s — SSE handles live updates; this prevents over-fetching
    refetchOnWindowFocus: true,
  });
}
