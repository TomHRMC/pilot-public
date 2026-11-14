# Pilot for Trades Design System — Pass 4, Tier 2 #7: Account Settings

**Version**: 1.0
**Status**: Locked
**Date**: April 27, 2026
**Author**: Tom (Founder) with Claude
**Scope**: User-personal account settings — profile, password, MFA (multi-method with self-service), active sessions, data export request. Tenant-required MFA policy with grace period enforcement. Closes Tier 2.
**Depends On**: Settings IA framework · Tier 2 #4 (Mockup A) · `mvp-arch.md` §4 Authentication & Authorization · §4.5 Multi-Factor Authentication · §15.10 Offline hard limit
**Backend additions**: A68 (tenant MFA policy + grace period enforcement), A69 (multi-method MFA enrollment + method management + recovery codes), A70 (active sessions list + revoke), A71 (data export request)
**Deliverable shape**: Shape A (Full flow spec) per Pass 4 framework doc — though the IA shape is closer to Shape C (Settings IA + per-setting spec), the MFA flow has full-flow-spec depth so this surface uses Shape A framing
**Note**: Integrations management (originally listed in Pass 4 framework Tier 2 #7 scope) lives at `Settings > Integrations` per Settings IA framework Decision 1 web tree and is already covered by Flow 6 (Calendar) and Tier 1 #2 (QuickBooks) specs. This spec does not duplicate that work.

---

## Purpose

Tier 2 #7 is the user-personal scope counterpart to #4–#6's tenant-shared scope. Where #4–#6 were "what does the tenant configure," this is "what does each user manage about their own account." Five sub-surfaces: profile (name, photo, contact info), password change, MFA (the substantive design problem), active sessions, data export.

The MFA flow is the genuine design work in this spec. Three methods supported (TOTP, SMS, Email) with self-service multi-method enrollment to prevent the "lost my phone, locked out" support ticket. Tenant-required MFA is owner-controlled at `Settings > Users & Roles > Security policy` with a 7-day grace period and login-time enforcement. Login-time method selection lets users pick which enrolled method to use per login.

Profile, password, active sessions, and data export are smaller deliverables — straightforward CRUD with familiar patterns. They earn their place in the spec because Tier 2 closes here and these are the last user-personal pieces to lock.

## Strategic direction

### MFA self-service is the lockout-prevention strategy

Mature SaaS apps shed customers when the "lost my phone, can't get into my account" support ticket happens. Pilot's answer: support three MFA methods (TOTP, SMS, Email) with self-service multi-method enrollment encouraged at first setup. A user who enrolls all three has redundancy — phone with authenticator dies, SMS to the same phone unavailable, but email recovery still works. Even with all three lost, recovery codes provide the ultimate fallback.

The trade-off is enrollment friction. Encouraging all three takes 3–5 extra minutes at first enrollment versus single-method. The friction is worth it because users do this once and never have to think about lockouts again — and Tom's support inbox doesn't fill with "I lost my phone" tickets.

### Tenant policy + grace period + login-trigger enforcement

Tenant-required MFA isn't binary "on or off" enforcement. It's a policy with a 7-day grace period and login-trigger enforcement, balancing security intent with operational reality:

- Owner enables MFA-required for the tenant at `Settings > Users & Roles > Security policy`
- All tenant users have 7 days to enroll at least one MFA method
- During grace period: warning banner on login; reminder push notification daily; users with valid sessions continue working
- After grace period: login-trigger enforcement — next login by an unenrolled user forces enrollment before any other action
- Users currently logged in can keep working until they next log in (preserves in-flight tech work; same logic as Edge Case 2 in our scoping discussion)

### Surface security trade-offs at method enrollment, don't hide them

Each MFA method card surfaces its security profile honestly. TOTP is "Most secure. Recommended." SMS and Email are "Convenient but less secure than authenticator apps." This isn't gating choice — users can pick any combination — but it makes the trade-off visible so security-conscious tenants and users make informed decisions.

### Owner can reset MFA for any user — recovery without lockout

Even with multi-method enrollment, lockout edge cases happen. Owners can reset MFA for any user, removing all enrolled methods. The user re-enrolls on next login. This is the support escape hatch for the rare cases where a user genuinely loses access to all enrolled methods and recovery codes simultaneously.

### Self-service for owner — owner enrolls all three, manages own MFA

Owners enroll all three methods at first MFA enrollment and pick at login time which method to use. If they lose one method, they can remove it from `My Account > Security > MFA methods` and add a replacement. This means the owner doesn't need someone to reset their MFA for them — they have multiple methods enrolled and can self-service.

## Locked design decisions

### 1. My Account IA — six sub-pages

**Decision**: `My Account` (per Settings IA framework Decision 3, top-level peer of Users & Roles) has six sub-pages:

| Sub-page | Purpose |
| :--- | :--- |
| **Profile** | Name, photo, contact info, phone number, language preference, time zone |
| **Password** | Password change with old-password verification |
| **Security > MFA methods** | Enrolled MFA methods, add/remove methods, regenerate recovery codes |
| **Security > Active sessions** | List of currently-logged-in devices, revoke individual sessions, "Revoke all other sessions" affordance |
| **Data export** | Request a full data export (background job; download link via email when ready) |
| **Sign out** | (mobile only; just a destructive action, not a sub-page on web) |

The web sidebar groups these as: `My Account > Profile | Password | Security | Data export`, with Security having two sub-routes for MFA methods and Active sessions.

Mobile renders these as cards on a single `My Account` screen, tappable into each sub-page.

**Rationale**: six sub-pages is the right granularity. Profile and password are universal. Security with two routes (MFA methods and active sessions) groups the security-relevant settings together for a user who's thinking "secure my account." Data export deserves its own sub-page because the action is a one-time request with associated UX (background processing + email delivery) rather than an editable setting.

### 2. Profile sub-page

**Decision**: Single-page form with these fields:

| Field | Editor | Save |
| :--- | :--- | :--- |
| Display name | Text input | Save-on-blur |
| Profile photo | Upload + crop with avatar preview | Explicit save (cropping is multi-step) |
| Phone number | E.164-formatted text input with validation | Save-on-blur (used for SMS MFA per Decision 5; required when SMS MFA is enrolled) |
| Email address | Read-only display (changing email is account migration; Phase 2) | n/a |
| Language preference | Single-select (English only in MVP) | Save-on-blur |
| Time zone | Single-select with auto-detected default | Save-on-blur |

**Rationale**: most fields are save-on-blur per Settings IA framework Decision 5. Profile photo is the one explicit-save case because cropping needs to commit as a single atomic operation. Email is read-only in MVP because changing email requires re-verification and account migration logic that's not in scope. Phone number changes have downstream effects on SMS MFA — if the phone changes, the SMS MFA method needs re-verification (Decision 5 covers this).

**Phase 2 deferrals for this sub-page**: email change with re-verification, multi-language UI, custom avatar uploads beyond standard crop.

### 3. Password sub-page

**Decision**: Three-field form: current password, new password, confirm new password. Standard pattern; nothing notable.

**Validation rules** (enforced server-side via Cognito policy):
- Minimum 12 characters
- Mix of uppercase, lowercase, number, special character
- Cannot match current password
- Cannot match any of last 5 passwords (Cognito's password history)
- Confirm-new must match new

**Submit behavior**: explicit Save button. On success, all sessions other than the current one are revoked (consistent with the security pattern from active sessions in Decision 6). User sees toast: "Password changed. You're still logged in here, but you'll need to log in again on other devices."

**Rationale**: password change is a real security action, not save-on-blur. Explicit Save makes the multi-step intent clear. Auto-revoking other sessions on password change is a security best practice — the password change might be a response to suspected compromise.

**Phase 2 deferrals**: passkey support, password strength indicator with real-time feedback, breached-password detection via HaveIBeenPwned API.

### 4. MFA methods sub-page — the central design problem

**Decision**: This sub-page lists enrolled methods, allows adding new methods, allows removing methods (with safeguards), and shows recovery codes status.

#### Layout

```
┌────────────────────────────────────────────────────────────────────────────┐
│ MFA methods                                                                │
│ ──────────                                                                 │
│                                                                            │
│ Multiple methods help you avoid lockouts. We recommend enrolling all three.│
│                                                                            │
│ ┌────────────────────────────────────────────────────────────────────────┐ │
│ │ 🔐 Authenticator app (TOTP)                                            │ │
│ │ Most secure. Recommended.                                              │ │
│ │                                                                        │ │
│ │ Enrolled: ✓ Yes (Google Authenticator on iPhone)                      │ │
│ │ Last used: 2 days ago                                                  │ │
│ │                                                                        │ │
│ │ [Remove this method]                                                   │ │
│ └────────────────────────────────────────────────────────────────────────┘ │
│                                                                            │
│ ┌────────────────────────────────────────────────────────────────────────┐ │
│ │ 📱 SMS                                                                 │ │
│ │ Convenient but less secure than authenticator apps.                   │ │
│ │                                                                        │ │
│ │ Enrolled: ✓ Yes (***-***-1234)                                        │ │
│ │ Last used: 1 week ago                                                  │ │
│ │                                                                        │ │
│ │ [Remove this method]                                                   │ │
│ └────────────────────────────────────────────────────────────────────────┘ │
│                                                                            │
│ ┌────────────────────────────────────────────────────────────────────────┐ │
│ │ ✉️  Email                                                              │ │
│ │ Convenient but less secure than authenticator apps.                   │ │
│ │                                                                        │ │
│ │ Enrolled: ◯ Not yet                                                    │ │
│ │                                                                        │ │
│ │ [Add this method]                                                      │ │
│ └────────────────────────────────────────────────────────────────────────┘ │
│                                                                            │
│ ─────────────────                                                          │
│                                                                            │
│ Recovery codes                                                             │
│ Generated on Apr 15, 2026. 8 of 10 codes remaining.                        │
│                                                                            │
│ [Show recovery codes]   [Regenerate codes]                                 │
│                                                                            │
└────────────────────────────────────────────────────────────────────────────┘
```

#### First-time MFA enrollment flow (encourage-all-three)

When a user has zero methods enrolled (first-time enrollment, or after owner reset), the flow is:

1. **Welcome screen**: "Set up MFA — pick at least one method, enroll all three for the strongest lockout protection."
2. **Method 1 (TOTP)**: QR code + manual-entry code. User scans with authenticator app. Enters first 6-digit code from app to confirm enrollment. "Skip TOTP" option visible but discouraged with copy: "We recommend authenticator apps as your primary method."
3. **Method 2 (SMS)**: Phone number entry (defaults to user's profile phone). "Send code" button → 6-digit code arrives via SMS. User enters code to confirm. "Skip SMS" option visible.
4. **Method 3 (Email)**: Email is the user's account email (not editable here). "Send code" button → 6-digit code arrives via email. User enters code to confirm. "Skip Email" option visible.
5. **Recovery codes**: 10 single-use codes generated and displayed once. User must download or copy them. Strong encouragement: "Save these somewhere safe. They're your last resort if you lose access to your other methods." Continue button is enabled only after the user clicks "I've saved my recovery codes."
6. **Done screen**: summary of enrolled methods + reminder that they can manage methods anytime at `My Account > Security > MFA methods`.

If the user skips all three methods, the flow can't complete — at least one is required. The flow loops back to Method 1 with a stronger prompt: "MFA requires at least one method. Pick one to continue."

#### Adding a method post-enrollment

User clicks "Add this method" on a method card. Flow is the same as the corresponding step from first-time enrollment (TOTP QR + verify, SMS phone + verify, Email + verify). On success, the method appears as enrolled.

#### Removing a method post-enrollment

User clicks "Remove this method" on an enrolled method card. Confirmation:
- If this is the last enrolled method (and tenant requires MFA), removal is **blocked** with explainer: "You can't remove your last MFA method while your tenant requires MFA. Add another method first, or contact your owner."
- If this is the last enrolled method (and tenant does NOT require MFA), removal is allowed with confirmation: "This will turn off MFA for your account. You'll be able to log in with just your password. Are you sure?"
- If other methods remain enrolled, removal is allowed with simple confirmation: "Remove [TOTP / SMS / Email] from your MFA methods?"

After removal, the user re-confirms via one of their other enrolled methods (proves the removal isn't an attacker action) for the cases where multiple methods remain. For the "last method" case (no MFA required), password re-confirmation suffices.

#### Recovery codes

10 single-use codes generated at first enrollment. Displayed once with strong save-them-somewhere prompt. Each code, when used, decrements from the "X of 10 remaining" count. Regenerable on demand with explicit confirmation: "Regenerating will invalidate any unused codes. Continue?" After regeneration, the new 10 codes display once with the same save-them prompt.

If the user is at <3 codes remaining, a banner appears at the top of the MFA methods page: "You're running low on recovery codes (2 left). Regenerate now to ensure you have backup access."

### 5. Login-time MFA method selection

**Decision**: When a user logs in (password verified) and the system determines MFA is needed, they see a method selection screen showing only their **enrolled** methods:

```
┌──────────────────────────────────────────────────────────────────┐
│ Confirm with MFA                                                 │
│ ─────────────────                                                │
│                                                                  │
│ Choose how you want to verify:                                   │
│                                                                  │
│   ┌──────────────────────────────────────────────────────────┐  │
│   │ 🔐 Use authenticator app                                 │  │
│   └──────────────────────────────────────────────────────────┘  │
│                                                                  │
│   ┌──────────────────────────────────────────────────────────┐  │
│   │ 📱 Send code via SMS to ***-***-1234                     │  │
│   └──────────────────────────────────────────────────────────┘  │
│                                                                  │
│   ┌──────────────────────────────────────────────────────────┐  │
│   │ ✉️  Send code via email to mike@***.com                  │  │
│   └──────────────────────────────────────────────────────────┘  │
│                                                                  │
│   [Use a recovery code instead]                                  │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

User picks a method → enters the 6-digit code → on success, login completes.

**Single-method case**: if the user enrolled only one method, the selection screen is skipped — they go directly to the code entry for their single method.

**Recovery code path**: "Use a recovery code instead" is always available regardless of enrolled methods. User enters one of their 10 single-use codes; code is consumed; login completes.

**Wrong code handling**: 5 wrong attempts on a single method → that login attempt is locked for 15 minutes; user can try a different method or wait. After 3 lockouts in 24 hours, the account is flagged for owner review (Phase 2 — for MVP, just locks for 15 min).

**Rationale**: showing only enrolled methods avoids confusion. Single-method users skip the selection screen entirely. Recovery code path is always present as the lockout escape hatch. Wrong-code lockout is per-method to allow legitimate users with one bad attempt on TOTP to switch to SMS rather than being fully locked out.

### 6. Active sessions sub-page

**Decision**: List of currently-logged-in sessions for the user with revoke affordances.

#### Layout

```
┌────────────────────────────────────────────────────────────────────────┐
│ Active sessions                                                        │
│ ───────────────                                                        │
│                                                                        │
│ Devices currently logged into your account.                            │
│                                                                        │
│ ┌──────────────────────────────────────────────────────────────────┐  │
│ │ 💻 Chrome on macOS · This device                                 │  │
│ │ San Francisco, CA · Last active: now                             │  │
│ │ Logged in: 2 hours ago                                           │  │
│ │                                                                  │  │
│ │ (current session)                                                │  │
│ └──────────────────────────────────────────────────────────────────┘  │
│                                                                        │
│ ┌──────────────────────────────────────────────────────────────────┐  │
│ │ 📱 Pilot mobile on iPhone                                        │  │
│ │ San Francisco, CA · Last active: 2 days ago                      │  │
│ │ Logged in: 12 days ago                                           │  │
│ │                                                                  │  │
│ │ [Revoke this session]                                            │  │
│ └──────────────────────────────────────────────────────────────────┘  │
│                                                                        │
│ ┌──────────────────────────────────────────────────────────────────┐  │
│ │ 📱 Pilot mobile on Android                                       │  │
│ │ Sacramento, CA · Last active: 1 month ago                        │  │
│ │ Logged in: 90 days ago                                           │  │
│ │                                                                  │  │
│ │ [Revoke this session]                                            │  │
│ └──────────────────────────────────────────────────────────────────┘  │
│                                                                        │
│ ─────────────────                                                      │
│                                                                        │
│ [Revoke all other sessions]                                            │
│                                                                        │
└────────────────────────────────────────────────────────────────────────┘
```

#### Per-session display

| Field | Source |
| :--- | :--- |
| Device + browser/app | User-Agent parsing on login |
| Location | IP geolocation (city/state); flagged with "(approximate)" annotation |
| Last active | Last API request timestamp from this session |
| Logged in | Session creation timestamp |

#### Revoke individual session

Confirmation: "Revoke this session? You'll be logged out on [device] and need to log in again." On confirm, the session's refresh token is invalidated immediately. Next API request from that session returns 401, forcing re-login.

#### "Revoke all other sessions" affordance

Prominent button at the bottom of the list. Confirmation: "Revoke all sessions except this one? You'll be logged out on all your other devices and need to log in again." On confirm, all sessions except the current one are revoked.

This affordance is the user's primary self-service security action when they suspect compromise. It's intentionally prominent.

**Rationale**: active sessions list is a real security tool, not a vanity surface. The "Revoke all other sessions" is the primary action — most users will never need it but when they do (lost phone, suspect compromise) it's the right tool. Per-session revoke handles the "I logged in on a friend's computer" case.

### 7. Data export sub-page

**Decision**: Single-action page where the user requests a full export of their tenant's data they have access to. Background job compiles the export; download link emailed to the user when ready.

#### Layout

```
┌──────────────────────────────────────────────────────────────────┐
│ Data export                                                      │
│ ──────────                                                       │
│                                                                  │
│ Download a copy of your tenant's data. The export includes       │
│ customers, jobs, quotes, invoices, time entries, expenses,       │
│ and customer communications you have access to.                  │
│                                                                  │
│ Format: ZIP archive with CSV files per data type.                │
│ Time to prepare: typically 5–15 minutes.                         │
│ Download link: emailed to mike@***.com when ready.               │
│                                                                  │
│ [Request export]                                                 │
│                                                                  │
│ ─────────────────                                                │
│                                                                  │
│ Recent exports                                                   │
│                                                                  │
│ • Apr 25, 2026 · Ready · [Download] (expires in 5 days)          │
│ • Mar 10, 2026 · Expired                                         │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

#### Request flow

User clicks "Request export." Confirmation modal: "Request an export of your data? You'll get an email with a download link in 5–15 minutes. The link expires after 7 days for security." On confirm, background job is queued.

While job is in progress, the page shows: "Export in progress... ~10 minutes remaining. We'll email you when it's ready."

When job completes, email arrives with a signed download URL valid for 7 days. User can also download from the "Recent exports" list on this page.

#### Export contents

Scope: data the requesting user has access to (per RBAC). For owners, this is the full tenant data. For technicians, this is only their jobs, time entries, expenses, and communications.

Format: ZIP archive containing CSV files per data type plus a `MANIFEST.json` with metadata (export request time, requesting user, tenant_id, data scope).

#### Frequency limit

Maximum one export per user per 24 hours (prevents abuse / accidental over-requesting). UI shows: "You can request your next export in 14 hours."

**Rationale**: data export is a real feature for compliance scenarios (user wants their data; tenant wants to back up before churn; auditor needs records). Background processing avoids tying up the API. Email delivery means user doesn't have to keep the page open. 7-day expiration on the download link is a security best practice (signed URL with time bound).

**Phase 2 deferrals**: incremental exports (only data changed since last export), JSON / Excel format options, scheduled recurring exports, export filtered by date range or scope.

### 8. Tenant MFA policy — owner-controlled at Settings > Users & Roles > Security policy

**Decision**: A new sub-surface at `Settings > Users & Roles > Security policy` (owner-only) lets the owner enable tenant-required MFA. This is **separate from** `My Account > Security` (user-personal) — same noun "security" but different scope.

#### Layout

```
┌──────────────────────────────────────────────────────────────────┐
│ Security policy                                                  │
│ ──────────────                                                   │
│                                                                  │
│ Tenant-wide security settings that apply to all team members.    │
│                                                                  │
│ Require MFA for all users          [ ◯ off ]                     │
│   When on, all team members must enroll at least one MFA method  │
│   to access Pilot. Existing users have a 7-day grace period      │
│   from when this setting is enabled.                             │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

When toggled on, a confirmation dialog: "Require MFA for everyone? Your team has 7 days to enroll. Users who don't enroll within 7 days will be required to enroll at next login. You can turn this off later if needed." On confirm, the setting commits and the grace period starts.

When toggled off later, a confirmation dialog: "Stop requiring MFA? Existing users with MFA enrolled keep their methods. New users won't be required to enroll. Continue?"

#### Tenant setting

`tenant_mfa_required` (boolean; default `false`). When toggled on, also sets `tenant_mfa_required_grace_period_starts_at` to current timestamp. The 7-day grace window is computed from this timestamp.

#### Owner-side enrollment

When the owner toggles MFA-required on for the first time, they themselves enter the grace period like any other user. The owner doesn't get a special exemption. This means at next login (or 7 days after toggle, whichever first), the owner is forced into MFA enrollment.

If the owner hasn't enrolled MFA themselves, the toggle still completes (no special validation requiring owner enrollment first) — the system trusts the owner to manage their own enrollment within the grace period.

**Rationale**: tenant MFA policy is an owner decision separate from any individual user's enrollment. The grace period gives the team time to enroll without forcing immediate enrollment for users actively in the field. Confirmation dialogs surface the consequence clearly. Owner-self-included keeps the policy simple — no exemption complexity.

### 9. Grace period UX — login-trigger enforcement with reminders

**Decision**: When tenant MFA is required and a user hasn't enrolled, the enforcement is login-trigger with daily reminders during the grace period.

#### Day 0 — Owner enables MFA-required

Tenant policy stored. `tenant_mfa_required_grace_period_starts_at` recorded. Email + push notification to all tenant users: "Your team is now requiring MFA. You have 7 days to enroll. [Enroll now]" Web notification banner appears at the top of the app for any active user without MFA enrolled: "Your team requires MFA. Enroll within 7 days to keep your account active. [Enroll now]"

#### During grace period (days 0–7)

- **At login**: warning banner appears at top of app: "MFA required in [X] days. [Enroll now]"
- **Daily reminder**: push notification at 9 AM tenant local time: "MFA required in [X] days." Reminders escalate in urgency:
  - Days 0–3: gentle nudge
  - Days 4–6: more urgent
  - Day 7: final reminder before enforcement
- **In-app banner**: persistent banner on every page until the user enrolls or grace period ends

#### Active user behavior during grace period

User can keep working with their existing session. Banners and reminders surface but don't block.

#### After grace period (day 7+)

**Login-trigger enforcement**: next login by any unenrolled user forces them into the MFA enrollment flow before any other action. Login screen: "Your team requires MFA. Enroll a method to continue." User is taken through the first-time enrollment flow (Decision 4) and then completes login.

**Currently-logged-in users without MFA**: their existing sessions continue to work. The next time they log in (e.g., session expired, manual logout, refresh token expiry), they'll be forced through enrollment. This is per Edge Case 2 from our scoping — preserves in-flight work without sacrificing eventual enforcement.

**During grace period if user logs back in**: the moment a user logs in (whether mid-grace or post-grace), enrollment becomes required for that session. So a user who logs in on day 3 still gets forced into enrollment immediately even though grace technically extends to day 7. This is per your direction in our scoping discussion.

#### Edge case: owner disables MFA-required during grace period

If the owner toggles MFA-required off mid-grace, all the grace-period enforcement stops. Users who haven't enrolled don't need to. Users who did enroll keep their methods.

**Rationale**: login-trigger enforcement is the friendliest model that still achieves security policy intent. Banners + push reminders during grace keep the requirement visible. Mid-grace login forces enrollment to align with your direction (any login during grace period activates the requirement immediately for that session). After grace period, every login forces enrollment.

### 10. Owner reset of user MFA — support escape hatch

**Decision**: A new affordance at `Settings > Users & Roles > [user detail] > Reset MFA` (owner-only) removes all MFA methods and recovery codes for the user. Next time the user logs in, they go through first-time MFA enrollment.

#### UX

Owner views user list at `Settings > Users & Roles`. Clicks a user to see detail. In the user detail surface, a "Security" section shows enrolled MFA methods. Below that:

```
[Reset MFA for this user]
```

Click → confirmation modal: "Reset MFA for [User name]? This will remove all their MFA methods. They'll have to re-enroll on their next login. Use this only if they've lost access to all their methods. Continue?"

On confirm, all MFA methods + recovery codes for that user are deleted. User is notified via email + push: "Your MFA has been reset by [Owner name]. You'll need to enroll again on your next login."

If the user is currently logged in, their existing session continues working until they log out or session expires (consistent with the broader pattern). On next login, they go through first-time enrollment (Decision 4).

**Audit log entry** captures the reset: actor (owner), target (user), timestamp, reason field (optional free-text).

#### Owner self-reset

Owners can reset their own MFA at `My Account > Security > MFA methods > Reset all my MFA` if they've enrolled multiple methods and want to start fresh. Confirmation requires password re-verification. After reset, the owner goes through enrollment on next login.

In practice, owners with three methods enrolled rarely need this — they can remove individual methods from the MFA methods sub-page. The "Reset all my MFA" affordance exists for the case where the owner has enrolled multiple methods but lost access to all of them and has fresh access via password (e.g., logged in on a desktop with saved password but lost their phone).

**Rationale**: owner reset is the support escape hatch for the lockout edge case. It's deliberately a discrete action (separate confirmation, audit logged) so it's not casually used. Notifying the user when their MFA is reset is essential — it's a security-relevant event.

### 11. Profile photo handling

**Decision**: Photo upload uses S3 presigned URL (consistent with photo upload patterns from A41). Image is automatically resized to 256x256 for avatar display. Original retained at S3 path; avatar served from CDN.

UI provides a square crop tool with preview. User can adjust crop, then save. Save commits the crop to a 256x256 avatar.

Default avatar when no photo is uploaded: initials of the user's display name on a brand-tinted background.

**Phase 2 deferrals**: photo presets, multiple photo sizes, animated avatars, social media import.

### 12. Mobile parity

**Decision**: All six sub-pages exist on mobile under `Mobile > Settings > My Account` per Settings IA framework Decision 2. Mobile rendering follows web layout adapted for mobile:

| Sub-page | Mobile rendering |
| :--- | :--- |
| Profile | Vertical form; same fields; photo upload uses native camera/gallery picker |
| Password | Three-field form |
| Security > MFA methods | Three method cards stacked vertically; same enrollment flows |
| Security > Active sessions | Same list view; "current session" highlighted |
| Data export | Same single-action page (less common on mobile but supported) |
| Sign out | Action button (mobile-only sub-page; web has it in the sidebar) |

The MFA enrollment flow on mobile uses a stepped wizard pattern (one step per screen) rather than the all-on-one-page web layout. Steps: welcome → TOTP → SMS → Email → recovery codes → done. Each step has back/skip/continue affordances.

**Rationale**: full mobile parity is appropriate for user-personal settings. The tech needs to manage their own account from their device — most of these actions (password, MFA enrollment, session revoke) are exactly the kinds of things a tech might do mid-day.

### 13. Audit log captures all account actions

**Decision**: Per Settings IA framework Cross-Domain G, every action on My Account is audited. Captured events:

- Profile changes (name, photo, phone, language, time zone)
- Password change (no plaintext capture; just timestamp + actor)
- MFA method added (which method)
- MFA method removed (which method)
- Recovery codes regenerated
- Session revoked (which session_id; including "all other sessions" bulk action)
- Data export requested
- Owner reset of user MFA (actor: owner, target: user)
- Tenant MFA policy toggled

Existing audit_log infrastructure covers all of these; no new tables.

## UX patterns established (for inheritance / reuse)

| Pattern | This spec | Inherits from / extends |
| :--- | :--- | :--- |
| Multi-method MFA enrollment with self-service add/remove | **NEW** | — |
| Login-time method selection with recovery code fallback | **NEW** | — |
| Tenant policy + grace period + login-trigger enforcement | **NEW** | — |
| Active sessions list with per-session and bulk revoke | **NEW** | — |
| Daily-escalating reminder pattern during grace period | **NEW** | A35 notification rate limiting (extended) |
| Owner reset of user MFA as support escape hatch | **NEW** | — |
| Encourage-all-three with skippable individual methods | **NEW** | — |
| Surface security trade-offs honestly in method cards | **NEW** | — |
| Background job request with email-on-completion | **NEW** | Existing background processing |
| Avatar / photo upload with crop | **NEW** | A41 photo upload infrastructure |
| Save-on-blur for simple fields, explicit Save for multi-step | Reused | Settings IA framework Decision 5 |
| Personal-self-service vs tenant-policy two-page split | Reused | Tier 2 #5 (notification preferences), Tier 2 #6 (voice persona) |
| Audit log for all settings changes | Reused | Settings IA framework Cross-Domain G |

Ten new patterns, three reused. Tier 2 #7 introduces more new patterns than #4–#6 because the user-personal scope brings in security-specific patterns (MFA, sessions, account safety) that don't appear elsewhere in MVP.

## Cross-domain considerations

### A. Cognito MFA capability already exists

Per arch doc §4.5, Cognito supports TOTP, email OTP, and SMS OTP. The architectural capability is ready. What Tier 2 #7 surfaces is the policy mechanism (tenant-required toggle), the enforcement flow (grace period, login-trigger), the self-service multi-method UX, and the owner-reset escape hatch.

The arch doc §4.5 statement "MFA is **required for all tenant users**" needs a small touch-up at Pass 4 close — should read "MFA is **available for all tenant users; tenant policy controls whether it's required**." The architectural capability is unchanged; the policy mechanism is what's new in Tier 2 #7.

### B. Phone number changes affect SMS MFA

Per Decision 2, phone number changes save-on-blur. If a user changes their phone number while SMS MFA is enrolled, the SMS method needs re-verification. UX flow:
- User changes phone number on Profile sub-page → save-on-blur saves the new number
- Toast surface: "Phone number updated. Please re-verify your SMS MFA method."
- User goes to MFA methods sub-page; SMS card shows status "Verification needed — verify with new number"
- User clicks "Verify SMS" → code sent to new number → user enters code → SMS method active again

If the user doesn't re-verify within 7 days, the SMS method is automatically removed (with notification). This prevents stale SMS methods routing codes to old phone numbers.

### C. Email change is Phase 2

Email is read-only on the Profile sub-page in MVP. Email changes require re-verification of the new email + transferring email-based MFA to the new address + re-verifying recovery email touchpoints. This is significant work and not core to MVP. Phase 2.

If a user genuinely needs to change their email in MVP, Tom handles via support — same pattern as add-on Twilio numbers.

### D. Active sessions infrastructure leverages existing token model

Active sessions list reads from Cognito's session tracking + Pilot's refresh token tracking. No new infrastructure needed — existing token storage already captures enough metadata for the list display (creation time, last activity, device fingerprint via User-Agent).

Revoke action invalidates the refresh token + flushes any cached access tokens for that session. Next API request from that session returns 401.

### E. Data export is real backend work

A71 below covers the data export pipeline. The export job needs to:
- Query the requesting user's accessible data (RBAC-scoped)
- Stream large datasets to S3 without holding in memory
- Generate CSV files per entity type
- Bundle into ZIP with MANIFEST.json
- Generate signed download URL with 7-day expiration
- Email URL to requesting user

Estimated 4–5 days of backend work for a thorough implementation.

### F. Tenant MFA policy interacts with Tier 3 #10 onboarding

Tier 3 #10 (onboarding) walks new tenants through initial setup. Tenant MFA policy is one of the things owners might enable during onboarding. Tier 3 #10 will reference Tier 2 #7's tenant MFA policy mechanism but doesn't need to design it independently — Tier 2 #7 has it covered.

### G. Forced-minimum push for grace-period reminders

Per Tier 2 #5's notification preference matrix, MFA enrollment reminders fall under the "System announcements" category. Should they be forced-minimum push? Yes, but only for the day-7 final reminder. Days 0–6 reminders use standard notification preferences (user can mute push if they want). Day 7 final reminder is forced-minimum push as a critical-sub-trigger per Tier 2 #5 Decision 4.

This means a user can mute "System announcements" push to avoid daily nags but will still see the day-7 final reminder push.

### H. Mobile push permission flow integration

Tier 3 #11 handles the mobile push notification permission request flow. Tier 2 #7 assumes push permission has been granted — if the user has denied push, MFA reminders go via email and in-app banner only. The UX is degraded but functional.

## Deferred items (Phase 2 / for future iteration)

- **Email change with re-verification** — significant work; Phase 2
- **Passkey support** (FIDO2 / WebAuthn) — modern alternative to MFA; Phase 2
- **Tenant policy: disable specific MFA methods** — owner says "we only allow TOTP, no SMS/Email" — Phase 2
- **Per-user MFA method requirement** — owner says "this user must have at least 2 methods enrolled" — Phase 2
- **MFA enrollment analytics for owners** — see which users have MFA, which methods enrolled — Phase 2
- **Recovery codes via printed letter** — physical mail backup — Phase 2; out of scope for SaaS
- **SSO integration** (Google Workspace, Microsoft Entra) — Phase 2; depends on tenant scale
- **Account deletion / closure** — user-initiated tenant data removal request — Phase 2; complex (data retention policy, billing implications)
- **Profile fields**: title/role text, custom fields — Phase 2
- **Multi-language UI** — Phase 2
- **Account activity log visible to user** — "you logged in from Sacramento at 2:14 PM" timeline — Phase 2
- **Suspicious activity detection** — login from unusual location triggers extra verification — Phase 2
- **Trusted device** — "remember this device, skip MFA for 30 days" — Phase 2
- **Password strength meter with real-time feedback** — Phase 2
- **Breached-password detection** via HaveIBeenPwned — Phase 2

## Validation checklist

Before implementation begins:

- [ ] My Account IA committed: 6 sub-pages per Decision 1
- [ ] Profile sub-page form fields confirmed per Decision 2
- [ ] Password sub-page validation rules confirmed per Decision 3 (12 char min + complexity + history)
- [ ] MFA enrollment flow walked through with dev team per Decision 4 (encourage-all-three with skippable methods)
- [ ] Three method cards designed with security trade-off annotations
- [ ] Recovery codes UX (display once, regenerable, low-codes warning) implemented per Decision 4
- [ ] Login-time method selection screen tested with single-method and multi-method users per Decision 5
- [ ] Wrong-code lockout (5 attempts → 15 min lock per method) tested
- [ ] Recovery code path always accessible during MFA challenge per Decision 5
- [ ] Active sessions list with per-session and bulk revoke implemented per Decision 6
- [ ] Data export request flow with background job + email delivery per Decision 7
- [ ] Tenant MFA policy toggle at `Settings > Users & Roles > Security policy` per Decision 8
- [ ] Grace period state tracking (`tenant_mfa_required_grace_period_starts_at`) implemented per Decision 8
- [ ] Login-trigger enforcement during grace period (any login activates immediate enrollment) per Decision 9
- [ ] Daily reminder pattern with day-7 critical push per Decision 9
- [ ] Owner reset of user MFA (audit logged + user notified) per Decision 10
- [ ] Owner self-reset of own MFA (password re-verification) per Decision 10
- [ ] Profile photo upload + crop using S3 presigned URLs per Decision 11
- [ ] Mobile parity for all six sub-pages with stepped wizard for MFA enrollment per Decision 12
- [ ] All actions audit-logged per Decision 13
- [ ] Phone number change → SMS MFA re-verification flow per Cross-Domain B
- [ ] Backend additions A68, A69, A70, A71 specified

## Backend additions (new for Tier 2 #7)

### A68. Tenant MFA Policy + Grace Period Enforcement

**Triggered by**: Decisions 8, 9 — tenant policy toggle + grace period + login-trigger enforcement.

**Scope**:

**Schema**:
- New tenant settings:
  - `tenant_mfa_required` BOOLEAN DEFAULT false
  - `tenant_mfa_required_grace_period_starts_at` TIMESTAMPTZ NULL — set when policy toggles on; remains NULL when off
  - `tenant_mfa_grace_period_days` INTEGER DEFAULT 7 — tenant-overridable but standard
- Setting placement: `Settings > Users & Roles > Security policy` per Settings IA framework
- Owner-only edit per Settings IA framework Decision 8

**Login-trigger enforcement middleware**:
- New middleware in API request pipeline: after authentication, before route handling
- Check: if `tenant_mfa_required = true` AND user has no enrolled MFA methods AND request is a login event OR user is in grace period AND has logged in since grace started
- If check passes: redirect / 403 with `enrollment_required: true` payload that frontend uses to route to MFA enrollment flow
- Existing authenticated sessions: not affected by enforcement until next login (per Decision 9)

**Grace period tracking**:
- New table `mfa_grace_period_tracking`
  - `tenant_id` UUID
  - `user_id` UUID
  - `grace_started_at` TIMESTAMPTZ
  - `enrolled_at` TIMESTAMPTZ NULL
  - `enforcement_activated_at` TIMESTAMPTZ NULL — set when user logs in mid-grace, activating immediate enforcement
  - Unique constraint on (tenant_id, user_id)
- Created when user is in tenant during grace period; updated on enrollment or enforcement activation

**Daily reminder Celery task**:
- New task `notify_mfa_grace_period_reminders` runs daily at 9 AM tenant local time
- Identifies tenants with active grace period; for each tenant with unenrolled users, dispatches notification (push + email + in-app banner)
- Reminder copy escalates by day: gentle days 0–3, urgent days 4–6, critical day 7
- Day 7 reminder uses forced-minimum push per Tier 2 #5 critical sub-trigger

**APIs**:
- `PUT /api/v1/settings/tenant/mfa-required` — set tenant policy (RBAC: owner only)
- `GET /api/v1/users/me/mfa-status` — returns enrolled methods + tenant policy + grace period state for the requesting user
- Login endpoint (existing) extended to return `enrollment_required` flag when applicable

**Effort estimate**: Medium — 4–5 days. Schema + middleware + grace period state machine + Celery reminder task + API endpoints. The login-trigger logic with grace period state interaction is the cost driver.

### A69. Multi-Method MFA Enrollment + Method Management + Recovery Codes

**Triggered by**: Decisions 4, 5, 10 — three-method enrollment with self-service + login-time method selection + recovery codes + owner reset.

**Scope**:

**Schema**:
- New table `user_mfa_method`
  - `mfa_method_id` UUID PK
  - `tenant_id` UUID
  - `user_id` UUID
  - `method_type` TEXT (`totp | sms | email`)
  - `enrolled_at` TIMESTAMPTZ
  - `last_used_at` TIMESTAMPTZ NULL
  - `cognito_method_id` TEXT — Cognito's reference for this method
  - `verification_status` TEXT (`verified | needs_reverification`) — needs_reverification when phone changes per Cross-Domain B
  - `metadata` JSONB — method-specific (e.g., last 4 digits of phone for SMS display)
  - Unique constraint on (tenant_id, user_id, method_type) — one of each method per user max
- New table `user_mfa_recovery_code`
  - `code_id` UUID PK
  - `tenant_id` UUID
  - `user_id` UUID
  - `code_hash` TEXT — hashed recovery code (never stored plaintext after initial display)
  - `generated_at` TIMESTAMPTZ
  - `used_at` TIMESTAMPTZ NULL
  - `set_id` UUID — group of 10 codes generated together
- Recovery codes generated as cryptographically random 10-character codes; hashed via bcrypt before storage

**APIs**:
- `POST /api/v1/users/me/mfa/methods/{method_type}/enroll-start` — initiate enrollment for a method (returns QR code for TOTP, sends code for SMS/Email)
- `POST /api/v1/users/me/mfa/methods/{method_type}/enroll-confirm` — confirm enrollment with code; method becomes active
- `DELETE /api/v1/users/me/mfa/methods/{method_id}` — remove method (with safeguards from Decision 4)
- `POST /api/v1/users/me/mfa/recovery-codes/generate` — generate new set of 10 codes; return plaintext (only time they're visible); invalidate any unused codes from prior set
- `GET /api/v1/users/me/mfa/recovery-codes/status` — returns count of unused codes
- `POST /api/v1/users/me/mfa/login-challenge/initiate` — initiate MFA challenge after password verification; returns enrolled methods
- `POST /api/v1/users/me/mfa/login-challenge/verify` — verify code from chosen method; on success, completes login
- `POST /api/v1/admin/users/{user_id}/mfa/reset` — owner reset of user MFA (RBAC: owner only); deletes all methods + recovery codes; sends notification to user

**Cognito integration**:
- Each method type maps to Cognito's MFA configuration
- Cognito handles the actual code verification and challenge flow
- Pilot stores the metadata + tracks state; Cognito stores the cryptographic material

**Effort estimate**: Large — 7–9 days. Schema + Cognito integration for three method types + enrollment flows + login challenge flow + recovery codes + owner reset. The Cognito MFA integration for three methods is the cost driver — each method has slightly different Cognito API patterns.

### A70. Active Sessions List + Revoke

**Triggered by**: Decision 6 — active sessions UX.

**Scope**:

**Schema**:
- Existing Cognito session tracking + refresh token storage already captures most needed metadata
- New table `user_session_metadata` (extension of existing token storage)
  - `session_id` UUID PK
  - `tenant_id` UUID
  - `user_id` UUID
  - `device_fingerprint` TEXT — User-Agent + other characteristics
  - `display_label` TEXT — e.g., "Chrome on macOS" or "Pilot mobile on iPhone"
  - `ip_address` INET
  - `geolocation` TEXT — city/state from IP geolocation (approximate)
  - `created_at`, `last_active_at` TIMESTAMPTZ
  - `revoked_at` TIMESTAMPTZ NULL
- Populated on login from User-Agent parsing + IP geolocation lookup

**APIs**:
- `GET /api/v1/users/me/sessions` — list all active sessions for requesting user
- `DELETE /api/v1/users/me/sessions/{session_id}` — revoke a specific session (invalidate refresh token; clear access token cache)
- `POST /api/v1/users/me/sessions/revoke-others` — bulk revoke all sessions except the current one

**Geolocation provider**: existing Pilot infrastructure can use a lightweight IP-to-location service (MaxMind GeoLite2 free tier, or similar). City-level accuracy is adequate; this isn't security-critical, just informational.

**Effort estimate**: Small-Medium — 3 days (schema extension + APIs + geolocation lookup integration + User-Agent parsing).

### A71. Data Export Request Pipeline

**Triggered by**: Decision 7 — data export request flow.

**Scope**:

**Schema**:
- New table `data_export_request`
  - `export_id` UUID PK
  - `tenant_id` UUID
  - `user_id` UUID — the requesting user
  - `requested_at` TIMESTAMPTZ
  - `status` TEXT (`pending | processing | ready | expired | failed`)
  - `s3_path` TEXT NULL — set when ready
  - `signed_url` TEXT NULL — set when ready; signed S3 URL with 7-day expiration
  - `expires_at` TIMESTAMPTZ NULL — 7 days after ready
  - `data_scope` TEXT — `full_tenant` (owner) or `user_specific` (technician)
  - `failure_reason` TEXT NULL
- Frequency limit: max one pending or recent (within 24h) request per user

**Export pipeline** (`tasks/data_export_pipeline.py`):
- Celery task that processes pending exports
- Queries data per RBAC scope
- Streams to S3 in chunks (avoids in-memory bloat for large tenants)
- Generates CSV files per entity type: customers.csv, jobs.csv, quotes.csv, invoices.csv, time_entries.csv, expenses.csv, communications.csv, etc.
- Bundles into ZIP with MANIFEST.json containing metadata
- Generates signed S3 URL with 7-day expiration
- Sends email to requesting user with download link
- Updates `data_export_request.status` to `ready`

**APIs**:
- `POST /api/v1/users/me/data-exports` — request a new export (subject to 24h frequency limit)
- `GET /api/v1/users/me/data-exports` — list recent exports for the requesting user
- `GET /api/v1/users/me/data-exports/{export_id}` — get specific export status

**Email template**: new transactional email "Your data export is ready" with download link + expiration date.

**Effort estimate**: Medium — 4–5 days. The export pipeline itself is the cost driver — handling large datasets (some tenants may have years of data) without memory bloat requires careful streaming. Email integration uses existing notification infrastructure.

### Total Tier 2 #7 backend additions

A68 (4–5) + A69 (7–9) + A70 (3) + A71 (4–5) = **18–22 days**.

---

## What this surface does NOT cover

- Integrations management (QuickBooks, Calendar disconnect/reconnect) — covered at `Settings > Integrations` per Settings IA framework; existing Flow 6 / Tier 1 #2 specs cover the UI
- Email change flow — Phase 2
- Passkey / WebAuthn support — Phase 2
- SSO integrations — Phase 2
- Account deletion / closure flow — Phase 2
- Per-user MFA enforcement variations — Phase 2 (single tenant policy in MVP)
- Trusted device "remember me" — Phase 2
- Account activity timeline — Phase 2

## Cumulative effects on Pass 4 totals

**Backend additions ledger**: A68–A71 added (4 additions). Cumulative through Tier 2 #7: A1–A71.

**Backend day estimate update**:
- Pre-Tier-2-#7 cumulative remaining MVP: 187–249.5 days
- Tier 2 #7 additions: 18–22 days
- New cumulative remaining MVP: **205–271.5 days**

**Tier 2 closes here.** All four Tier 2 surfaces locked: #4 Configurable thresholds, #5 Notification preferences, #6 Voice persona tone, #7 Account settings. Plus the Settings IA framework prerequisite.

**Framework doc**: Tier 2 #7 status flips from `pending` to `locked`. Tier 2 in aggregate flips from `in progress` to `complete`. Tier 3 (states catalog + first-time-user states + onboarding flow + push permission) becomes the next phase.

**Arch doc touch-up needed at Pass 4 close**: §4.5 statement on MFA needs the small refinement noted in Cross-Domain A — change from "MFA is required for all tenant users" to "MFA is available for all tenant users; tenant policy controls whether it's required."

**PRD touch-up needed at Pass 4 close**: §3.5 (Identity, Access, Tenant) needs new feature rows for the multi-method MFA enrollment, tenant MFA policy with grace period, and the active sessions list.

## Next: Tier 3 — States Catalog + Onboarding

Tier 2 closes. Tier 3 begins with the states catalog (#8 + #9 paired per the Pass 4 framework). The states catalog is a Shape B deliverable — pattern guide + application matrix mapping every Pass 1–3 flow plus Pass 4 surfaces to their empty / loading / error state treatments. Estimated 250–350 lines.

After the states catalog, Tier 3 continues with #10 (onboarding) and #11 (mobile push permission). Tier 3 surfaces are different shapes than Tier 2 — closer to Pass 3's full flow specs in scope and depth.
