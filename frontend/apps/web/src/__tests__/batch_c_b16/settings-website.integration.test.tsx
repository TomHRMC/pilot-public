/**
 * C-B16 Integration Test — Settings > Website Page
 *
 * Location: apps/web/src/__tests__/batch_c_b16/settings-website.integration.test.tsx
 *
 * Tests:
 * 1. Page renders (not 404) — primary heading visible with MSW mock
 * 2. RBAC — owner sees the form area
 * 3. RBAC — tech role is blocked (RoleGate hides form)
 * 4. Pre-fill from GET payload (defaults populate form fields)
 * 5. Publish happy path → success state + dialog closes
 * 6. Publish 409 path → dialog switches to overwrite variant → confirm → re-POST
 * 7. Unpublish → warning surfaced
 *
 * RULE 14: retry: false QueryClient. RULE 15: server.resetHandlers in afterEach.
 */

import React from "react";
import {
  describe,
  it,
  expect,
  vi,
  beforeAll,
  afterEach,
  afterAll,
} from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { setupServer } from "msw/node";
import { http, HttpResponse } from "msw";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { AuthContext } from "@pilot/ui/auth";
import type { AuthContextValue, PilotUser, PilotRole } from "@pilot/ui/auth";
import { NotificationQueueProvider } from "@pilot/ui";

import { TenantSiteSettingsForm } from "@/features/tenant-site/components/TenantSiteSettingsForm";

// ── Navigation mocks ──────────────────────────────────────────────────────────

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), back: vi.fn(), replace: vi.fn() }),
  usePathname: () => "/settings/website",
  useSearchParams: () => new URLSearchParams(),
}));
vi.mock("next/link", () => ({
  default: ({
    href,
    children,
    ...rest
  }: {
    href: string;
    children: React.ReactNode;
    [key: string]: unknown;
  }) => React.createElement("a", { href, ...rest }, children),
}));

// ── Mock data ─────────────────────────────────────────────────────────────────

const MOCK_DEFAULTS = {
  display_name: "Lang Electric",
  display_name_source: "tenant_override",
  public_email: "office@langelectric.example",
  public_email_source: "tenant_override",
  public_phone: "+15551234567",
  public_phone_source: "tenant_override",
  public_city: "Richmond",
  public_city_source: "tenant_override",
  public_state: "VA",
  public_state_source: "tenant_override",
};

const MOCK_UNCONFIGURED = {
  configured: false,
  site: null,
  defaults: MOCK_DEFAULTS,
};

const MOCK_CONFIGURED_DRAFT = {
  configured: true,
  site: {
    id: "00000000-0000-0000-0000-000000000001",
    tenant_id: "00000000-0000-0000-0000-0000000000a1",
    slug: "lang-electric",
    site_kind: "hosted_compliance",
    status: "draft",
    display_name: "Lang Electric",
    tagline: "Residential & commercial electrical",
    public_email: "office@langelectric.example",
    public_phone: "+15551234567",
    public_city: "Richmond",
    public_state: "VA",
    public_address_line1: null,
    public_postal_code: null,
    show_full_address: false,
    template_version: "v1",
    published_at: null,
    unpublished_at: null,
    kit_sent_at: null,
    website_auto_populated: false,
    idempotency_key: null,
    site_url: null,
    requirements_emailed_at: null,
  },
  defaults: MOCK_DEFAULTS,
};

const MOCK_PUBLISHED = {
  configured: true,
  site: {
    ...MOCK_CONFIGURED_DRAFT.site,
    status: "published",
    published_at: "2026-08-14T01:23:45Z",
    site_url: "https://lang-electric.p4tsites.com",
    website_auto_populated: true,
  },
  defaults: MOCK_DEFAULTS,
};

// Track publish requests for assertion
let publishRequestBody: Record<string, unknown> | null = null;
let publishRequestCount = 0;

// ── MSW server ────────────────────────────────────────────────────────────────

const server = setupServer(
  // GET /api/v1/tenant-site — default: unconfigured
  http.get("/api/v1/tenant-site", () => HttpResponse.json(MOCK_UNCONFIGURED)),

  // PUT /api/v1/tenant-site
  http.put("/api/v1/tenant-site", async ({ request }) => {
    const body = (await request.json().catch(() => ({}))) as Record<
      string,
      unknown
    >;
    return HttpResponse.json({
      ...MOCK_CONFIGURED_DRAFT.site,
      ...body,
      status: "draft",
    });
  }),

  // GET /api/v1/tenant-site/slug-availability
  http.get("/api/v1/tenant-site/slug-availability", ({ request }) => {
    const url = new URL(request.url);
    const slug = url.searchParams.get("slug") ?? "";
    if (slug === "taken") {
      return HttpResponse.json({
        available: false,
        reason: "taken",
        suggestion: "taken-2",
      });
    }
    if (slug === "admin" || slug === "www") {
      return HttpResponse.json({
        available: false,
        reason: "reserved",
        suggestion: null,
      });
    }
    if (!/^[a-z0-9]([a-z0-9-]{1,61}[a-z0-9])?$/.test(slug)) {
      return HttpResponse.json({
        available: false,
        reason: "invalid",
        suggestion: null,
      });
    }
    return HttpResponse.json({
      available: true,
      reason: null,
      suggestion: null,
    });
  }),

  // POST /api/v1/tenant-site/publish — default: success
  http.post("/api/v1/tenant-site/publish", async ({ request }) => {
    publishRequestCount++;
    publishRequestBody = (await request.json().catch(() => ({}))) as Record<
      string,
      unknown
    >;
    return HttpResponse.json({
      ...MOCK_CONFIGURED_DRAFT.site,
      status: "published",
      published_at: new Date().toISOString(),
      website_auto_populated: true,
      site_url: "https://lang-electric.p4tsites.com",
    });
  }),

  // POST /api/v1/tenant-site/unpublish
  http.post("/api/v1/tenant-site/unpublish", () =>
    HttpResponse.json({
      ...MOCK_CONFIGURED_DRAFT.site,
      status: "unpublished",
      unpublished_at: new Date().toISOString(),
      warning:
        "The URL on your 10DLC profile was NOT cleared. If your brand is live, the carrier may still check this URL.",
    }),
  ),
);

beforeAll(() => server.listen({ onUnhandledRequest: "bypass" }));
afterEach(() => {
  server.resetHandlers();
  publishRequestBody = null;
  publishRequestCount = 0;
});
afterAll(() => server.close());

// ── Auth helpers ──────────────────────────────────────────────────────────────

function makeAuthValue(role: PilotRole = "owner"): AuthContextValue {
  const user: PilotUser = {
    id: "u-cb16-test",
    email: "test@pilot.example.com",
    role,
    tenantId: "t-cb16-test",
    displayName: "Test User",
    accessToken: "mock-token",
  };
  return {
    user,
    isAuthenticated: true,
    role,
    signIn: vi.fn(),
    confirmMfaChallenge: vi.fn(),
    signOut: vi.fn(),
    refreshSession: vi.fn().mockResolvedValue("mock-token"),
  };
}

function renderForm(role: PilotRole = "owner") {
  const qc = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
  return render(
    <AuthContext.Provider value={makeAuthValue(role)}>
      <QueryClientProvider client={qc}>
        <NotificationQueueProvider>
          <TenantSiteSettingsForm />
        </NotificationQueueProvider>
      </QueryClientProvider>
    </AuthContext.Provider>,
  );
}

// ── Tests ─────────────────────────────────────────────────────────────────────

describe("C-B16 — Settings > Website Integration", () => {
  it("1. page renders — primary heading visible", async () => {
    renderForm();
    await waitFor(() => {
      expect(screen.getByText("Website")).toBeInTheDocument();
    });
    expect(
      screen.getByText(/Satisfy TCR 10DLC website vetting/),
    ).toBeInTheDocument();
  });

  it("2. RBAC — owner sees the form area (option cards)", async () => {
    renderForm("owner");
    await waitFor(() => {
      expect(screen.getByText("Choose your approach")).toBeInTheDocument();
    });
    expect(
      screen.getByTestId("site-option-card-hosted_compliance"),
    ).toBeInTheDocument();
  });

  it("3. RBAC — tech sees option cards but NOT the form (RoleGate hides form)", async () => {
    // Override GET to return configured draft so the form section would show
    server.use(
      http.get("/api/v1/tenant-site", () =>
        HttpResponse.json(MOCK_CONFIGURED_DRAFT),
      ),
    );

    renderForm("technician");
    await waitFor(() => {
      expect(screen.getByText("Choose your approach")).toBeInTheDocument();
    });
    // The hosted form section is wrapped in RoleGate permission="settings.manage"
    // Tech role does not have settings.manage → form should NOT be in the DOM
    expect(screen.queryByTestId("tenant-site-form")).toBeNull();
  });

  it("4. pre-fill from GET payload — defaults populate form fields", async () => {
    server.use(
      http.get("/api/v1/tenant-site", () =>
        HttpResponse.json(MOCK_CONFIGURED_DRAFT),
      ),
    );

    renderForm("owner");
    await waitFor(() => {
      expect(screen.getByTestId("tenant-site-form")).toBeInTheDocument();
    });

    const displayNameInput = screen.getByTestId(
      "display-name-input",
    ) as HTMLInputElement;
    expect(displayNameInput.value).toBe("Lang Electric");

    const phoneInput = screen.getByTestId(
      "public-phone-input",
    ) as HTMLInputElement;
    // PLP-FIX-4: PhoneInput displays progressive format, not raw E.164
    expect(phoneInput.value).toBe("(555) 123-4567");

    const cityInput = screen.getByTestId(
      "public-city-input",
    ) as HTMLInputElement;
    expect(cityInput.value).toBe("Richmond");
  });

  it("5. publish happy path — dialog opens, confirm fires POST, dialog closes on success", async () => {
    server.use(
      http.get("/api/v1/tenant-site", () =>
        HttpResponse.json(MOCK_CONFIGURED_DRAFT),
      ),
    );

    renderForm("owner");
    await waitFor(() => {
      expect(screen.getByTestId("tenant-site-form")).toBeInTheDocument();
    });

    // Fill slug so publish button can be enabled
    const slugInput = screen.getByTestId("site-slug-input");
    fireEvent.change(slugInput, { target: { value: "lang-electric" } });

    // Wait for slug availability to resolve
    await waitFor(
      () => {
        expect(screen.getByText("Available")).toBeInTheDocument();
      },
      { timeout: 2000 },
    );

    // Click publish button
    const publishBtn = screen.getByTestId("publish-btn");
    fireEvent.click(publishBtn);

    // Dialog should open
    await waitFor(() => {
      expect(screen.getByTestId("publish-confirm-dialog")).toBeInTheDocument();
    });

    // Click confirm
    const confirmBtn = screen.getByTestId("publish-confirm-btn");
    fireEvent.click(confirmBtn);

    // Dialog should close on success
    await waitFor(() => {
      expect(screen.queryByTestId("publish-confirm-dialog")).toBeNull();
    });

    // Verify the POST was sent with confirm_website_overwrite: false
    expect(publishRequestCount).toBe(1);
    expect(publishRequestBody).toMatchObject({
      confirm_website_overwrite: false,
    });
  });

  it("6. publish 409 path — dialog switches to overwrite variant, confirm sends confirm_website_overwrite: true", async () => {
    server.use(
      http.get("/api/v1/tenant-site", () =>
        HttpResponse.json(MOCK_CONFIGURED_DRAFT),
      ),
      // First publish attempt → 409
      http.post("/api/v1/tenant-site/publish", async ({ request }) => {
        publishRequestCount++;
        publishRequestBody = (await request.json().catch(() => ({}))) as Record<
          string,
          unknown
        >;
        // Only return 409 on first attempt (no confirm flag)
        if (publishRequestBody.confirm_website_overwrite !== true) {
          return HttpResponse.json(
            {
              type: "https://errors.pilotfortrades.com/website-overwrite-requires-confirmation",
              title: "Website overwrite requires confirmation",
              status: 409,
              current_url: "https://old-site.example.com",
              new_url: "https://lang-electric.p4tsites.com",
              brand_status: "active",
              detail: "Confirm to replace the existing URL.",
            },
            { status: 409 },
          );
        }
        // Second attempt with confirm → success
        return HttpResponse.json({
          ...MOCK_CONFIGURED_DRAFT.site,
          status: "published",
          published_at: new Date().toISOString(),
          site_url: "https://lang-electric.p4tsites.com",
        });
      }),
    );

    renderForm("owner");
    await waitFor(() => {
      expect(screen.getByTestId("tenant-site-form")).toBeInTheDocument();
    });

    // Fill slug
    const slugInput = screen.getByTestId("site-slug-input");
    fireEvent.change(slugInput, { target: { value: "lang-electric" } });

    await waitFor(
      () => {
        expect(screen.getByText("Available")).toBeInTheDocument();
      },
      { timeout: 2000 },
    );

    // Click publish
    fireEvent.click(screen.getByTestId("publish-btn"));

    // Dialog opens (normal variant)
    await waitFor(() => {
      expect(screen.getByTestId("publish-confirm-dialog")).toBeInTheDocument();
    });

    // Click confirm (normal variant)
    fireEvent.click(screen.getByTestId("publish-confirm-btn"));

    // Dialog should switch to overwrite variant (409 received)
    await waitFor(() => {
      expect(
        screen.getByTestId("publish-overwrite-confirm-btn"),
      ).toBeInTheDocument();
    });

    // Verify the first POST was sent with confirm_website_overwrite: false
    expect(publishRequestBody).toMatchObject({
      confirm_website_overwrite: false,
    });

    // Check the checkbox to enable the overwrite confirm button
    fireEvent.click(screen.getByTestId("publish-overwrite-checkbox"));

    // Click the overwrite confirm button
    fireEvent.click(screen.getByTestId("publish-overwrite-confirm-btn"));

    // Dialog should close on success
    await waitFor(() => {
      expect(screen.queryByTestId("publish-confirm-dialog")).toBeNull();
    });

    // Verify the second POST was sent with confirm_website_overwrite: true
    expect(publishRequestCount).toBe(2);
    expect(publishRequestBody).toMatchObject({
      confirm_website_overwrite: true,
    });
  });

  it("7. unpublish — warning surfaced after unpublish", async () => {
    server.use(
      http.get("/api/v1/tenant-site", () => HttpResponse.json(MOCK_PUBLISHED)),
    );

    renderForm("owner");
    await waitFor(() => {
      expect(screen.getByTestId("tenant-site-form")).toBeInTheDocument();
    });

    // Unpublish button should be visible (status=published)
    const unpublishBtn = screen.getByTestId("unpublish-btn");
    expect(unpublishBtn).toBeInTheDocument();

    fireEvent.click(unpublishBtn);

    // Warning should appear
    await waitFor(() => {
      expect(screen.getByTestId("unpublish-warning")).toBeInTheDocument();
    });
    expect(screen.getByText(/NOT cleared/)).toBeInTheDocument();
  });
});
