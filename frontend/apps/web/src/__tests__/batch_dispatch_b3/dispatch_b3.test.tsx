/**
 * DISPATCH-B3 Tests — Filter Data Fix + Panel Classification Chips
 *
 * Location: apps/web/src/__tests__/batch_dispatch_b3/dispatch_b3.test.tsx
 *
 * Covers:
 * 1. Priority filter works (Emergency pill hides Standard jobs, shows Emergency)
 * 2. Customer Type filter works (Company shows only company-customer jobs)
 * 3. Job Type filter works (selecting a specific job type filters correctly)
 * 4. normalizeJob carries real values through (no hardcoded override)
 * 5. Panel chips render with all four; omit Site Type + Job Type when null
 * 6. FilterBar labels: Standard/Urgent/Emergency; Person/Company
 *
 * Per batch-fe-dispatch-b3-react-engr-prompt.md §Test Requirements
 */

import React from "react";
import {
  describe,
  it,
  expect,
  vi,
  afterEach,
  beforeAll,
  afterAll,
} from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderHook } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";

import { FilterBar } from "../../features/dispatch-board/components/FilterBar";
import type { FilterBarProps } from "../../features/dispatch-board/components/FilterBar";
import { JobPropertiesPanel } from "../../features/dispatch-board/components/JobPropertiesPanel";
import { useDispatchBoard } from "../../features/dispatch-board/hooks/useDispatchBoard";
import type {
  DispatchBoardJob,
  DispatchBoardTech,
} from "../../features/dispatch-board/types-stub";
import type { DispatchBoardFilters } from "../../features/dispatch-board/store";
import type { ScheduledJob } from "../../features/dispatch-board/components/DispatchBoardLanes";

// ─── Mock next/navigation ─────────────────────────────────────────────────────

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), back: vi.fn(), replace: vi.fn() }),
  usePathname: () => "/schedule",
  useSearchParams: () => new URLSearchParams(),
}));

// ─── Mock TechAssignmentSection (avoid full jobs feature mount) ────────────────

vi.mock("../../features/jobs/components/TechAssignmentSection", () => ({
  TechAssignmentSection: () => null,
}));

// ─── MSW server for hook tests ────────────────────────────────────────────────

const TODAY = new Date().toISOString().slice(0, 10);

/** Board fixture with varied classification values to prove filters work */
const BOARD_FIXTURE = {
  start_date: `${TODAY}T00:00:00Z`,
  end_date: `${TODAY}T23:59:59Z`,
  techs: [
    {
      tech_id: "tech-b3-001",
      id: "tech-b3-001",
      name: "Jake Rivera",
      display_color: "#3B82F6",
      avatar_url: null,
      eta_minutes_to_first_job: null,
      additional_job_commitments: [],
      jobs: [
        {
          id: "job-b3-001",
          tenant_id: "t-001",
          customer_id: "c-001",
          site_id: "s-001",
          status_id: "st-001",
          scheduled_start_at: `${TODAY}T09:00:00.000Z`,
          scheduled_end_at: `${TODAY}T12:00:00.000Z`,
          estimated_duration_minutes: 180,
          external_calendar_event_id: null,
          is_active: true,
          eta_minutes: null,
          version: 1,
          primary_assignment_id: "a-001",
          assignment_version: 1,
          job_number: "JOB-B3-001",
          customer_name: "Riverside Office Park",
          site_address: "123 Main St",
          site_name: "HQ",
          title: null,
          assignment_role: "primary",
          // Emergency priority, company customer — the discriminating job
          priority: "emergency",
          customer_type: "company",
          site_type: "commercial",
          job_type_code: "panel_upgrade",
          job_type_label: "Panel Upgrade",
        },
      ],
    },
    {
      tech_id: "tech-b3-002",
      id: "tech-b3-002",
      name: "Maria Santos",
      display_color: "#10B981",
      avatar_url: null,
      eta_minutes_to_first_job: null,
      additional_job_commitments: [],
      jobs: [
        {
          id: "job-b3-002",
          tenant_id: "t-001",
          customer_id: "c-002",
          site_id: "s-002",
          status_id: "st-001",
          scheduled_start_at: `${TODAY}T13:00:00.000Z`,
          scheduled_end_at: `${TODAY}T15:00:00.000Z`,
          estimated_duration_minutes: 120,
          external_calendar_event_id: null,
          is_active: true,
          eta_minutes: null,
          version: 1,
          primary_assignment_id: "a-002",
          assignment_version: 1,
          job_number: "JOB-B3-002",
          customer_name: "Johnson Residence",
          site_address: "456 Oak Ave",
          site_name: null,
          title: null,
          assignment_role: "primary",
          // Standard priority, person customer — standard job
          priority: "standard",
          customer_type: "person",
          site_type: "residential",
          job_type_code: "service_call",
          job_type_label: "Service Call",
        },
        {
          id: "job-b3-003",
          tenant_id: "t-001",
          customer_id: "c-003",
          site_id: "s-003",
          status_id: "st-001",
          scheduled_start_at: `${TODAY}T15:30:00.000Z`,
          scheduled_end_at: `${TODAY}T17:30:00.000Z`,
          estimated_duration_minutes: 120,
          external_calendar_event_id: null,
          is_active: true,
          eta_minutes: null,
          version: 1,
          primary_assignment_id: "a-003",
          assignment_version: 1,
          job_number: "JOB-B3-003",
          customer_name: "Metro Comm Inc",
          site_address: "789 Central Ave",
          site_name: null,
          title: null,
          assignment_role: "primary",
          // Urgent priority, company customer
          priority: "urgent",
          customer_type: "company",
          site_type: "industrial",
          job_type_code: "panel_upgrade",
          job_type_label: "Panel Upgrade",
        },
      ],
    },
  ],
  unassigned: [],
};

const server = setupServer(
  http.get("/api/v1/scheduling/dispatch-board", () =>
    HttpResponse.json(BOARD_FIXTURE),
  ),
  http.get("/api/v1/jobs/", () =>
    HttpResponse.json({ items: [], total: 0, limit: 200, offset: 0 }),
  ),
  http.get("/api/v1/users/", () => HttpResponse.json({ items: [], total: 0 })),
);

beforeAll(() => server.listen({ onUnhandledRequest: "bypass" }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

// ─── QueryClient factory (retry: false per Rule 14) ──────────────────────────

function makeQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
}

function makeWrapper() {
  const qc = makeQueryClient();
  const Wrapper = ({ children }: { children: React.ReactNode }) =>
    React.createElement(QueryClientProvider, { client: qc }, children);
  return Wrapper;
}

// ─── 1. normalizeJob carries real values through ──────────────────────────────

describe("DISPATCH-B3 — useDispatchBoard normalizeJob", () => {
  it("carries priority:emergency through without hardcoded override", async () => {
    const { result } = renderHook(() => useDispatchBoard(TODAY, TODAY), {
      wrapper: makeWrapper(),
    });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    const emergencyJob = result.current.data!.jobs.find(
      (j) => j.id === "job-b3-001",
    );
    expect(emergencyJob).toBeDefined();
    expect(emergencyJob!.priority).toBe("emergency");
  });

  it("carries customer_type:company through without hardcoded override", async () => {
    const { result } = renderHook(() => useDispatchBoard(TODAY, TODAY), {
      wrapper: makeWrapper(),
    });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    const companyJob = result.current.data!.jobs.find(
      (j) => j.id === "job-b3-001",
    );
    expect(companyJob!.customer_type).toBe("company");
  });

  it("carries site_type:industrial through correctly", async () => {
    const { result } = renderHook(() => useDispatchBoard(TODAY, TODAY), {
      wrapper: makeWrapper(),
    });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    const industrialJob = result.current.data!.jobs.find(
      (j) => j.id === "job-b3-003",
    );
    expect(industrialJob!.site_type).toBe("industrial");
  });

  it("carries job_type_label:'Panel Upgrade' through correctly", async () => {
    const { result } = renderHook(() => useDispatchBoard(TODAY, TODAY), {
      wrapper: makeWrapper(),
    });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    const panelJob = result.current.data!.jobs.find(
      (j) => j.id === "job-b3-001",
    );
    expect(panelJob!.job_type_label).toBe("Panel Upgrade");
    expect(panelJob!.job_type_code).toBe("panel_upgrade");
  });

  it("standard job retains priority:standard (not overridden to 'standard' from hardcode)", async () => {
    const { result } = renderHook(() => useDispatchBoard(TODAY, TODAY), {
      wrapper: makeWrapper(),
    });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    const standardJob = result.current.data!.jobs.find(
      (j) => j.id === "job-b3-002",
    );
    expect(standardJob!.priority).toBe("standard");
    expect(standardJob!.customer_type).toBe("person");
  });
});

// ─── 2. FilterBar labels: Standard/Urgent/Emergency; Person/Company ──────────

const DEFAULT_FILTERS: DispatchBoardFilters = {
  techIds: [],
  statuses: [],
  customerTypes: [],
  jobTypes: [],
  priorities: [],
};

const MOCK_TECHS: DispatchBoardTech[] = [];

const MIXED_JOBS: DispatchBoardJob[] = [
  {
    id: "job-b3-001",
    title: "JOB-B3-001",
    customer_name: "Riverside Office Park",
    site_address: "123 Main St",
    scheduled_start_at: `${TODAY}T09:00:00Z`,
    scheduled_end_at: `${TODAY}T12:00:00Z`,
    tech_id: "tech-b3-001",
    status: "scheduled",
    priority: "emergency",
    customer_type: "company",
    site_type: "commercial",
    job_type_code: "panel_upgrade",
    job_type_label: "Panel Upgrade",
    updated_at: new Date().toISOString(),
  },
  {
    id: "job-b3-002",
    title: "JOB-B3-002",
    customer_name: "Johnson Residence",
    site_address: "456 Oak Ave",
    scheduled_start_at: `${TODAY}T13:00:00Z`,
    scheduled_end_at: `${TODAY}T15:00:00Z`,
    tech_id: "tech-b3-002",
    status: "scheduled",
    priority: "standard",
    customer_type: "person",
    site_type: "residential",
    job_type_code: "service_call",
    job_type_label: "Service Call",
    updated_at: new Date().toISOString(),
  },
  {
    id: "job-b3-003",
    title: "JOB-B3-003",
    customer_name: "Metro Comm Inc",
    site_address: "789 Central Ave",
    scheduled_start_at: `${TODAY}T15:30:00Z`,
    scheduled_end_at: `${TODAY}T17:30:00Z`,
    tech_id: "tech-b3-002",
    status: "in_progress",
    priority: "urgent",
    customer_type: "company",
    site_type: "industrial",
    job_type_code: "panel_upgrade",
    job_type_label: "Panel Upgrade",
    updated_at: new Date().toISOString(),
  },
];

function makeFilterBarProps(
  overrides: Partial<FilterBarProps> = {},
): FilterBarProps {
  return {
    techs: MOCK_TECHS,
    jobs: MIXED_JOBS,
    filters: DEFAULT_FILTERS,
    collapsed: false,
    onToggleCollapsed: vi.fn(),
    onToggleTech: vi.fn(),
    onToggleStatus: vi.fn(),
    onToggleCustomerType: vi.fn(),
    onToggleJobType: vi.fn(),
    onTogglePriority: vi.fn(),
    onResetStatus: vi.fn(),
    onClearAll: vi.fn(),
    ...overrides,
  };
}

describe("DISPATCH-B3 — FilterBar labels", () => {
  it("priority pills are Standard/Urgent/Emergency (not Rush/Warranty)", () => {
    render(<FilterBar {...makeFilterBarProps()} />);
    expect(
      screen.getByRole("button", { name: /^standard$/i }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /^urgent$/i }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /^emergency$/i }),
    ).toBeInTheDocument();
    // Old values must not exist
    expect(
      screen.queryByRole("button", { name: /^rush$/i }),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: /^warranty$/i }),
    ).not.toBeInTheDocument();
  });

  it("customer type pills are Person/Company (not Commercial/Residential)", () => {
    render(<FilterBar {...makeFilterBarProps()} />);
    expect(
      screen.getByRole("button", { name: /^person$/i }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /^company$/i }),
    ).toBeInTheDocument();
    // Old values must not exist
    expect(
      screen.queryByRole("button", { name: /^commercial$/i }),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: /^residential$/i }),
    ).not.toBeInTheDocument();
  });
});

// ─── 3. Priority filter invokes correct callback values ───────────────────────

describe("DISPATCH-B3 — Priority filter callbacks", () => {
  it("clicking Emergency pill calls onTogglePriority('emergency')", () => {
    const onTogglePriority = vi.fn();
    render(<FilterBar {...makeFilterBarProps({ onTogglePriority })} />);
    fireEvent.click(screen.getByRole("button", { name: /^emergency$/i }));
    expect(onTogglePriority).toHaveBeenCalledWith("emergency");
  });

  it("clicking Urgent pill calls onTogglePriority('urgent')", () => {
    const onTogglePriority = vi.fn();
    render(<FilterBar {...makeFilterBarProps({ onTogglePriority })} />);
    fireEvent.click(screen.getByRole("button", { name: /^urgent$/i }));
    expect(onTogglePriority).toHaveBeenCalledWith("urgent");
  });
});

// ─── 4. Customer Type filter callbacks ───────────────────────────────────────

describe("DISPATCH-B3 — Customer Type filter callbacks", () => {
  it("clicking Company pill calls onToggleCustomerType('company')", () => {
    const onToggleCustomerType = vi.fn();
    render(<FilterBar {...makeFilterBarProps({ onToggleCustomerType })} />);
    fireEvent.click(screen.getByRole("button", { name: /^company$/i }));
    expect(onToggleCustomerType).toHaveBeenCalledWith("company");
  });

  it("clicking Person pill calls onToggleCustomerType('person')", () => {
    const onToggleCustomerType = vi.fn();
    render(<FilterBar {...makeFilterBarProps({ onToggleCustomerType })} />);
    fireEvent.click(screen.getByRole("button", { name: /^person$/i }));
    expect(onToggleCustomerType).toHaveBeenCalledWith("person");
  });
});

// ─── 5. Job Type filter uses job_type_code as filter value ────────────────────

describe("DISPATCH-B3 — Job Type filter", () => {
  it("job type pills use job_type_label as display and job_type_code for callbacks", () => {
    const onToggleJobType = vi.fn();
    render(<FilterBar {...makeFilterBarProps({ onToggleJobType })} />);
    // "Panel Upgrade" is the label (from job_type_label)
    expect(
      screen.getByRole("button", { name: /panel upgrade/i }),
    ).toBeInTheDocument();
    // Service Call is the other unique type
    expect(
      screen.getByRole("button", { name: /service call/i }),
    ).toBeInTheDocument();
    // Clicking Panel Upgrade passes the code (panel_upgrade), not label
    fireEvent.click(screen.getByRole("button", { name: /panel upgrade/i }));
    expect(onToggleJobType).toHaveBeenCalledWith("panel_upgrade");
  });
});

// ─── 6. JobPropertiesPanel classification chips ───────────────────────────────

function makeScheduledJob(
  overrides: Record<string, unknown> = {},
): ScheduledJob {
  return {
    id: "job-panel-001",
    title: "JOB-001",
    customer_name: "Riverside Office Park",
    site_address: "123 Main St",
    site_name: "Main Office",
    scheduled_start_at: `${TODAY}T09:00:00Z`,
    scheduled_end_at: `${TODAY}T12:00:00Z`,
    tech_id: "tech-001",
    status: "scheduled",
    priority: "emergency",
    customer_type: "company",
    site_type: "commercial",
    job_type_code: "panel_upgrade",
    job_type_label: "Panel Upgrade",
    updated_at: new Date().toISOString(),
    ...overrides,
  } as unknown as ScheduledJob;
}

describe("DISPATCH-B3 — JobPropertiesPanel classification chips", () => {
  it("shows Priority chip with 'Emergency' for emergency job", () => {
    const job = makeScheduledJob();
    render(
      <QueryClientProvider client={makeQueryClient()}>
        <JobPropertiesPanel
          job={job}
          onClose={vi.fn()}
          onJobUpdated={vi.fn()}
        />
      </QueryClientProvider>,
    );
    // Emergency chip should be present
    expect(screen.getByLabelText(/priority: emergency/i)).toBeInTheDocument();
  });

  it("shows Customer Type chip for company job", () => {
    const job = makeScheduledJob();
    render(
      <QueryClientProvider client={makeQueryClient()}>
        <JobPropertiesPanel
          job={job}
          onClose={vi.fn()}
          onJobUpdated={vi.fn()}
        />
      </QueryClientProvider>,
    );
    expect(
      screen.getByLabelText(/customer type: company/i),
    ).toBeInTheDocument();
  });

  it("shows Site Type chip when site_type is present", () => {
    const job = makeScheduledJob({ site_type: "commercial" });
    render(
      <QueryClientProvider client={makeQueryClient()}>
        <JobPropertiesPanel
          job={job}
          onClose={vi.fn()}
          onJobUpdated={vi.fn()}
        />
      </QueryClientProvider>,
    );
    expect(screen.getByLabelText(/site type: commercial/i)).toBeInTheDocument();
  });

  it("omits Site Type chip when site_type is null", () => {
    const job = makeScheduledJob({ site_type: null });
    render(
      <QueryClientProvider client={makeQueryClient()}>
        <JobPropertiesPanel
          job={job}
          onClose={vi.fn()}
          onJobUpdated={vi.fn()}
        />
      </QueryClientProvider>,
    );
    expect(screen.queryByLabelText(/site type/i)).not.toBeInTheDocument();
  });

  it("shows Job Type chip when job_type_label is present", () => {
    const job = makeScheduledJob({ job_type_label: "Panel Upgrade" });
    render(
      <QueryClientProvider client={makeQueryClient()}>
        <JobPropertiesPanel
          job={job}
          onClose={vi.fn()}
          onJobUpdated={vi.fn()}
        />
      </QueryClientProvider>,
    );
    expect(
      screen.getByLabelText(/job type: panel upgrade/i),
    ).toBeInTheDocument();
  });

  it("omits Job Type chip when job_type_label is null", () => {
    const job = makeScheduledJob({ job_type_label: null, job_type_code: null });
    render(
      <QueryClientProvider client={makeQueryClient()}>
        <JobPropertiesPanel
          job={job}
          onClose={vi.fn()}
          onJobUpdated={vi.fn()}
        />
      </QueryClientProvider>,
    );
    expect(screen.queryByLabelText(/job type/i)).not.toBeInTheDocument();
  });

  it("shows Urgent chip using alert token styling class", () => {
    const job = makeScheduledJob({ priority: "urgent" });
    render(
      <QueryClientProvider client={makeQueryClient()}>
        <JobPropertiesPanel
          job={job}
          onClose={vi.fn()}
          onJobUpdated={vi.fn()}
        />
      </QueryClientProvider>,
    );
    const urgentChip = screen.getByLabelText(/priority: urgent/i);
    expect(urgentChip.className).toMatch(/alert/);
  });

  it("shows Standard chip using neutral styling class", () => {
    const job = makeScheduledJob({ priority: "standard" });
    render(
      <QueryClientProvider client={makeQueryClient()}>
        <JobPropertiesPanel
          job={job}
          onClose={vi.fn()}
          onJobUpdated={vi.fn()}
        />
      </QueryClientProvider>,
    );
    const standardChip = screen.getByLabelText(/priority: standard/i);
    expect(standardChip.className).toMatch(/neutral/);
  });
});
