/**
 * TEAM-INVITE-1 MSW Handlers
 *
 * Location: apps/web/src/mocks/handlers/teamInviteHandlers.ts
 *
 * Mocks the 5 Part A endpoints:
 *  - GET  /api/v1/users/invites (list)
 *  - POST /api/v1/users/invites (create)
 *  - POST /api/v1/users/invites/:inviteId/resend
 *  - POST /api/v1/users/invites/:inviteId/revoke
 *  - GET  /api/v1/invites/:token (public landing lookup)
 *
 * Fixture: ≥4 varied rows covering the status-chip matrix:
 *  - pending technician (future expiry)
 *  - pending office_staff (expiring soon)
 *  - accepted (accepted_at set)
 *  - expired (past expiry)
 */

import { http, HttpResponse } from "msw";

// ── Fixture: varied invite rows ──────────────────────────────────────────────

const now = new Date();
const futureExpiry = new Date(
  now.getTime() + 7 * 24 * 60 * 60 * 1000,
).toISOString();
const soonExpiry = new Date(
  now.getTime() + 1 * 24 * 60 * 60 * 1000,
).toISOString();
const pastExpiry = new Date(
  now.getTime() - 2 * 24 * 60 * 60 * 1000,
).toISOString();
const acceptedAt = new Date(
  now.getTime() - 3 * 24 * 60 * 60 * 1000,
).toISOString();

interface MockInvite {
  id: string;
  email: string;
  role_code: string;
  invited_by: string | null;
  created_at: string;
  expires_at: string;
  accepted_at: string | null;
  is_active: boolean;
  status: string;
}

const INVITES: MockInvite[] = [
  {
    id: "invite-001",
    email: "newguy@pilot.local",
    role_code: "technician",
    invited_by: "user-001",
    created_at: new Date(now.getTime() - 1 * 24 * 60 * 60 * 1000).toISOString(),
    expires_at: futureExpiry,
    accepted_at: null,
    is_active: true,
    status: "pending",
  },
  {
    id: "invite-002",
    email: "sarah-office@pilot.local",
    role_code: "office_staff",
    invited_by: "user-001",
    created_at: new Date(now.getTime() - 6 * 24 * 60 * 60 * 1000).toISOString(),
    expires_at: soonExpiry,
    accepted_at: null,
    is_active: true,
    status: "pending",
  },
  {
    id: "invite-003",
    email: "accepted-user@pilot.local",
    role_code: "technician",
    invited_by: "user-001",
    created_at: new Date(
      now.getTime() - 10 * 24 * 60 * 60 * 1000,
    ).toISOString(),
    expires_at: futureExpiry,
    accepted_at: acceptedAt,
    is_active: true,
    status: "accepted",
  },
  {
    id: "invite-004",
    email: "expired-invite@pilot.local",
    role_code: "accountant",
    invited_by: "user-001",
    created_at: new Date(
      now.getTime() - 14 * 24 * 60 * 60 * 1000,
    ).toISOString(),
    expires_at: pastExpiry,
    accepted_at: null,
    is_active: true,
    status: "expired",
  },
];

// Known tokens for the public landing dev fixtures (TEAM-INVITE-2)
const DEV_TOKEN = "dev-invite-token-0001"; // technician
const DEV_TOKEN_OFFICE = "dev-invite-token-0002"; // office_staff

// ── RFC 7807 error helper ────────────────────────────────────────────────────
// PLP-FIX-7: Mirrors the real FastAPI nested envelope shape:
//   body = {"detail": {type, title, status, detail, invite_id?}}
// getApiProblem (the house helper) unwraps this Shape A. The previous
// flat top-level shape caused the FE parser to read data.type (undefined)
// and pass data.detail (the object) as a string → React crash (INV-BUG-1).

function rfc7807(
  type: string,
  title: string,
  status: number,
  detail: string,
  extra?: Record<string, unknown>,
) {
  return HttpResponse.json(
    {
      detail: {
        type: `https://errors.pilotfortrades.com/${type}`,
        title,
        status,
        detail,
        ...extra,
      },
    },
    { status },
  );
}

// ── Handlers ────────────────────────────────────────────────────────────────

export const teamInviteHandlers = [
  // GET /api/v1/users/invites — list all tenant invites
  http.get("/api/v1/users/invites", () => {
    return HttpResponse.json(INVITES);
  }),

  // POST /api/v1/users/invites — create + send invite
  http.post("/api/v1/users/invites", async ({ request }) => {
    const body = (await request.json()) as {
      email: string;
      role_code: string;
    };

    // Check for existing user (409 invite_user_exists)
    if (body.email === "existing@pilot.local") {
      return rfc7807(
        "invite_user_exists",
        "User already exists",
        409,
        "This person already has a Pilot account. Contact Pilot support for multi-business access.",
      );
    }

    // Check for pending invite (409 invite_pending_exists)
    const existingPending = INVITES.find(
      (i) =>
        i.email === body.email &&
        i.accepted_at === null &&
        i.is_active &&
        new Date(i.expires_at) > now &&
        i.status === "pending",
    );
    if (existingPending) {
      return rfc7807(
        "invite_pending_exists",
        "Invite already pending",
        409,
        "An active invite already exists for this email.",
        { invite_id: existingPending.id },
      );
    }

    // Success — create new invite
    const newInvite: MockInvite = {
      id: `invite-${Date.now()}`,
      email: body.email,
      role_code: body.role_code,
      invited_by: "user-001",
      created_at: now.toISOString(),
      expires_at: futureExpiry,
      accepted_at: null,
      is_active: true,
      status: "pending",
    };
    INVITES.push(newInvite);

    return HttpResponse.json(
      {
        id: newInvite.id,
        email: newInvite.email,
        role_code: newInvite.role_code,
        expires_at: newInvite.expires_at,
        created_at: newInvite.created_at,
      },
      { status: 201 },
    );
  }),

  // POST /api/v1/users/invites/:inviteId/resend
  http.post("/api/v1/users/invites/:inviteId/resend", async ({ params }) => {
    const invite = INVITES.find((i) => i.id === params.inviteId);
    if (!invite) {
      return rfc7807(
        "invite_not_found",
        "Invite not found",
        404,
        "The invite could not be found.",
      );
    }
    if (invite.accepted_at) {
      return rfc7807(
        "invite_already_accepted",
        "Invite already accepted",
        409,
        "This invite has already been accepted.",
      );
    }
    if (!invite.is_active) {
      return rfc7807(
        "invite_revoked",
        "Invite revoked",
        409,
        "This invite has been revoked.",
      );
    }

    // Rotate token + reset expiry
    invite.expires_at = new Date(
      now.getTime() + 7 * 24 * 60 * 60 * 1000,
    ).toISOString();

    return HttpResponse.json({
      id: invite.id,
      email: invite.email,
      expires_at: invite.expires_at,
    });
  }),

  // POST /api/v1/users/invites/:inviteId/revoke
  http.post("/api/v1/users/invites/:inviteId/revoke", async ({ params }) => {
    const invite = INVITES.find((i) => i.id === params.inviteId);
    if (!invite) {
      return rfc7807(
        "invite_not_found",
        "Invite not found",
        404,
        "The invite could not be found.",
      );
    }
    if (invite.accepted_at) {
      return rfc7807(
        "invite_already_accepted",
        "Invite already accepted",
        409,
        "This invite has already been accepted.",
      );
    }

    invite.is_active = false;
    invite.status = "revoked";

    return HttpResponse.json({
      id: invite.id,
      is_active: false,
    });
  }),

  // GET /api/v1/invites/:token — public landing lookup (no auth)
  // TEAM-INVITE-2: lookup over both dev tokens; uniform 404 for all others.
  http.get("/api/v1/invites/:token", ({ params }) => {
    if (params.token === DEV_TOKEN) {
      return HttpResponse.json({
        tenant_name: "Pilot Dev Tenant",
        email: "newguy@pilot.local",
        role_code: "technician",
        expires_at: futureExpiry,
      });
    }

    if (params.token === DEV_TOKEN_OFFICE) {
      return HttpResponse.json({
        tenant_name: "Pilot Dev Tenant",
        email: "sarah-office@pilot.local",
        role_code: "office_staff",
        expires_at: futureExpiry,
      });
    }

    return rfc7807(
      "invite_invalid",
      "Invite invalid",
      404,
      "This invite link is no longer valid.",
    );
  }),
];
