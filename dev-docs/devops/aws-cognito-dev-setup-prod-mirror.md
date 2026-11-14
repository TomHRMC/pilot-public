# AWS Cognito Setup — Pilot for Trades Dev Environment

**Last updated**: June 22, 2026  
**Status**: ✅ Verified working — web (`dev@pilot.local`) and mobile (Expo Go + `USER_PASSWORD_AUTH`) both confirmed  
**Update (2026-11-14)**: both Cognito user pools (`pilot-dev` and `pilot - prod`) and all their users were deleted for the public snapshot. Test-user passwords below are placeholders; choose your own when recreating the pools.  
**Region**: `us-east-1` (US East — N. Virginia)

---

## Table of Contents

1. [Overview & Architecture](#1-overview--architecture)
2. [User Pool Configuration](#2-user-pool-configuration)
3. [App Client Configuration](#3-app-client-configuration)
4. [Test Users](#4-test-users)
5. [Frontend Integration — Web](#5-frontend-integration--web)
6. [Frontend Integration — Mobile](#6-frontend-integration--mobile)
7. [Backend Integration](#7-backend-integration)
8. [Environment Variable Reference](#8-environment-variable-reference)
9. [Password Reset / Maintenance](#9-password-reset--maintenance)
10. [Lessons Learned — Setup Gotchas](#10-lessons-learned--setup-gotchas)

---

## 1. Overview & Architecture

### How Authentication Works

Pilot for Trades uses **AWS Cognito User Pools** with **AWS Amplify** authentication. The flow:

```
User enters email + password on /login
       ↓
AuthProvider.tsx calls signIn(email, password)
       ↓
aws-amplify/auth calls Cognito User Pool API
  - Web:    USER_SRP_AUTH  (default — uses client-side crypto)
  - Mobile: USER_PASSWORD_AUTH  (required for Expo Go — see §10 Gotcha 2)
       ↓
Cognito returns RS256-signed JWT (ID token + access token)
       ↓
apiClient.ts attaches ID token to all API requests via fetchAuthSession()
       ↓
FastAPI backend: verify_cognito_jwt() verifies JWT against Cognito JWKS endpoint
       ↓
Backend looks up user by email in DB → returns AuthenticatedUser
```

### Why SPA (not "Traditional Web Application")

The Cognito "Traditional web application" type generates a **client secret**. AWS Amplify running in the browser is a **public client** — it cannot securely store a client secret. Using a Traditional Web App client causes the error:

> `Client X is configured with secret but SECRET_HASH was not received`

The **Single-page application** type creates a public client (no secret), which is what Amplify requires.

---

## 2. User Pool Configuration

### Active User Pool

| Setting | Value |
|---|---|
| **User Pool Name** | `pilot-dev` (renamed from `User pool - ngxowp` — display name only; ID unchanged) |
| **User Pool ID** | `us-east-1_XXXXXXXXX` |
| **Region** | `us-east-1` |
| **Created via** | "Single-page application" app type wizard |
| **JWKS URL** | `https://cognito-idp.us-east-1.amazonaws.com/us-east-1_XXXXXXXXX/.well-known/jwks.json` |

### User Pool Settings

| Setting | Value | Notes |
|---|---|---|
| Sign-in method | **Email** | CITEXT (case-insensitive) |
| Self-service sign-up | **Disabled** | Account creation via our signup endpoint only |
| Password policy | Min 12 chars, uppercase + lowercase + numbers + symbols | Per mvp-arch.md §4.1 |
| MFA | **Disabled** (dev) | Can be enabled per-tenant via app settings |
| Account recovery | **Email only** | |
| Temporary password validity | 7 days | |
| Email delivery | **Cognito default** (free, up to 50/day) | Sufficient for dev |
| Required attributes | **email** only | First/last name stored in our DB, not Cognito |

---

## 3. App Client Configuration

### Active App Client

| Setting | Value |
|---|---|
| **App Client ID** | `xxxxxxxxxxxxxxxxxxxxxxxxxx` |
| **App Client Name** | `pilot-web-dev` (created as SPA type) |
| **Client Secret** | **None** — public client, no secret |
| **App Type** | Single-page application |

### Authentication Flows Enabled

| Flow | Enabled | Used By |
|---|---|---|
| `ALLOW_USER_SRP_AUTH` | ✅ | Web (Next.js) — uses browser native `crypto.getRandomValues()` |
| `ALLOW_USER_PASSWORD_AUTH` | ✅ | Mobile (Expo Go) — required because `@aws-amplify/react-native` cannot be linked in Expo Go |
| `ALLOW_REFRESH_TOKEN_AUTH` | ✅ | Both — required for session refresh |
| `ALLOW_ADMIN_USER_PASSWORD_AUTH` | ❌ | Server-side only, not needed |
| `ALLOW_CUSTOM_AUTH` | ❌ | Not needed |

> **Important**: Both `USER_SRP_AUTH` and `USER_PASSWORD_AUTH` must be enabled on the App Client. The mobile app's `AuthProvider.tsx` auto-selects `USER_PASSWORD_AUTH` when `navigator.product === 'ReactNative'`.

### Token Expiration

| Token | Expiration |
|---|---|
| Access token | 60 minutes |
| ID token | 60 minutes |
| Refresh token | **30 days** |

> The refresh token must be 30 days per architecture spec (mvp-arch.md §4.1) to support mobile offline scenarios.

---

## 4. Test Users

Three dev/QA test users are created in the User Pool. These users must also exist in the `pilot_dev` PostgreSQL database (seeded by `seed_test_tenant.py`).

| Email | Role | UUID in DB |
|---|---|---|
| `dev@pilot.local` | Owner (full access) | `00000000-0000-0000-0000-000000000002` |
| `tech@pilot.local` | Technician (field ops) | `00000000-0000-0000-0000-000000000003` |
| `office@pilot.local` | Office Staff | `00000000-0000-0000-0000-000000000004` |

### Passwords

| User | Password |
|---|---|
| `dev@pilot.local` | `<test-user-password>` |
| `tech@pilot.local` | `<test-user-password>` |
| `office@pilot.local` | `<test-user-password>` |

### User Account Status

All users must have **Confirmed** status (not `FORCE_CHANGE_PASSWORD`). See §9 for how to set permanent passwords.

---

## 5. Frontend Integration — Web

### Files Changed

| File | Purpose |
|---|---|
| [`frontend/apps/web/src/lib/amplify-config.ts`](../../frontend/apps/web/src/lib/amplify-config.ts) | Calls `Amplify.configure()` at module load — imported first in `providers.tsx` |
| [`frontend/apps/web/src/app/providers.tsx`](../../frontend/apps/web/src/app/providers.tsx) | `import "../lib/amplify-config"` as first import |
| `frontend/apps/web/.env.local` _(private)_ | Cognito IDs + `NEXT_PUBLIC_USE_MOCK_AUTH=false` |

### Web `.env.local`

```
NEXT_PUBLIC_API_URL=http://127.0.0.1:8000
NEXT_PUBLIC_USE_MOCK_AUTH=false
NEXT_PUBLIC_USE_MSW_MOCKS=false
NEXT_PUBLIC_COGNITO_USER_POOL_ID=us-east-1_XXXXXXXXX
NEXT_PUBLIC_COGNITO_APP_CLIENT_ID=xxxxxxxxxxxxxxxxxxxxxxxxxx
```

### Web Mock Auth (for local UI dev without Cognito)

```
NEXT_PUBLIC_USE_MOCK_AUTH=true
NEXT_PUBLIC_USE_MSW_MOCKS=true
NEXT_PUBLIC_MOCK_USER_ROLE=owner
```

When `NEXT_PUBLIC_USE_MOCK_AUTH=true`, `Amplify.configure()` is skipped entirely and a mock user is injected into `AuthProvider`. MSW intercepts all API calls.

---

## 6. Frontend Integration — Mobile

The mobile app uses a different auth setup from the web app. Key differences:

| Concern | Web | Mobile |
|---|---|---|
| Env var prefix | `NEXT_PUBLIC_` | `EXPO_PUBLIC_` |
| Auth flow | `USER_SRP_AUTH` (default) | `USER_PASSWORD_AUTH` (required for Expo Go) |
| Token storage | Browser memory/sessionStorage | `@react-native-async-storage/async-storage` |
| Amplify config file | `apps/web/src/lib/amplify-config.ts` | `apps/mobile/lib/amplify-config.ts` |

### Files Changed

| File | Purpose |
|---|---|
| [`frontend/apps/mobile/lib/amplify-config.ts`](../../frontend/apps/mobile/lib/amplify-config.ts) | NEW — configures Amplify for native. Skipped on web. Uses AsyncStorage for token persistence. |
| [`frontend/apps/mobile/app/_layout.tsx`](../../frontend/apps/mobile/app/_layout.tsx) | Imports `react-native-get-random-values` and `../lib/amplify-config` as very first imports |
| [`frontend/packages/ui/src/auth/AuthProvider.tsx`](../../frontend/packages/ui/src/auth/AuthProvider.tsx) | Auto-selects `USER_PASSWORD_AUTH` on React Native via `navigator.product === 'ReactNative'` |
| `frontend/apps/mobile/.env` _(private)_ | Cognito IDs with `EXPO_PUBLIC_` prefix |

### Mobile `.env`

```
EXPO_PUBLIC_API_URL=http://192.168.1.50:8000   # Your Mac's local Wi-Fi IP
EXPO_PUBLIC_USE_MOCK_AUTH=true                   # Web-only: enables MSW on localhost:8081
EXPO_PUBLIC_MOCK_USER_ROLE=owner                 # Web-only: role for mock user
EXPO_PUBLIC_COGNITO_USER_POOL_ID=us-east-1_XXXXXXXXX
EXPO_PUBLIC_COGNITO_APP_CLIENT_ID=xxxxxxxxxxxxxxxxxxxxxxxxxx
EXPO_PUBLIC_COGNITO_REGION=us-east-1
```

> **Critical**: Variables in `.env` for the mobile app MUST use `EXPO_PUBLIC_` prefix. Expo Metro ignores `NEXT_PUBLIC_` variables — they resolve as empty strings and `Amplify.configure()` is silently skipped, causing `"An unknown error has occurred."` on sign-in.

### Platform-Split Auth

`EXPO_PUBLIC_USE_MOCK_AUTH=true` is interpreted differently by platform:

| Platform | Mock auth active? | Behavior |
|---|---|---|
| Browser (`localhost:8081`) | ✅ Yes | Mock user auto-login, MSW intercepts API calls |
| iPhone/Android (Expo Go) | ❌ No | Real Cognito login screen, real JWT, real FastAPI |

This allows both to run from the **same `npx expo start` session** and the same `.env`.

### Why `USER_PASSWORD_AUTH` on Mobile

Amplify's default `USER_SRP_AUTH` requires `@aws-amplify/react-native` — a native module that needs `pod install` and a **custom dev client** (`expo-dev-client`) or production EAS build. Expo Go cannot link native modules. Using SRP in Expo Go causes:

> `@aws-amplify/react-native doesn't seem to be linked... You are not using Expo Go`

`USER_PASSWORD_AUTH` sends credentials over TLS without client-side crypto — it works in Expo Go out of the box.

When building a **production EAS build** with `expo-dev-client`, you can optionally switch back to `USER_SRP_AUTH` by removing the `authFlowType` override in `AuthProvider.tsx`.

### Token Persistence

Without `AsyncStorage` as Amplify's storage backend, tokens are stored in JavaScript memory only. This means `fetchAuthSession()` in `apiClient.ts`'s Axios interceptor returns empty tokens on subsequent API calls after login, causing 401s.

`apps/mobile/lib/amplify-config.ts` configures AsyncStorage explicitly:
```ts
Amplify.configure(authConfig, { Storage: AsyncStorage });
```

---

## 7. Backend Integration

The backend (`backend/core/auth.py`) validates JWTs by fetching the JWKS from Cognito:

```
COGNITO_REGION=us-east-1
COGNITO_USER_POOL_ID=us-east-1_XXXXXXXXX
```

The `verify_cognito_jwt()` function constructs the JWKS URL:
```
https://cognito-idp.us-east-1.amazonaws.com/us-east-1_XXXXXXXXX/.well-known/jwks.json
```

After JWT validation, `get_current_user()` looks up the user in the DB by the `email` claim from the token.

> **Important**: If you change the Cognito User Pool (e.g., when migrating regions), you MUST update `COGNITO_REGION` and `COGNITO_USER_POOL_ID` in `backend/.env` AND restart FastAPI. A mismatch causes 401 Unauthorized on all authenticated endpoints — the JWT is valid but signed by a different pool's private key.

---

## 8. Environment Variable Reference

### Backend (`backend/.env`)

```
COGNITO_REGION=us-east-1
COGNITO_USER_POOL_ID=us-east-1_XXXXXXXXX
```

### Web Frontend (`frontend/apps/web/.env.local`)

```
NEXT_PUBLIC_API_URL=http://127.0.0.1:8000
NEXT_PUBLIC_USE_MOCK_AUTH=false
NEXT_PUBLIC_USE_MSW_MOCKS=false
NEXT_PUBLIC_COGNITO_USER_POOL_ID=us-east-1_XXXXXXXXX
NEXT_PUBLIC_COGNITO_APP_CLIENT_ID=xxxxxxxxxxxxxxxxxxxxxxxxxx
```

### Mobile Frontend (`frontend/apps/mobile/.env`)

```
EXPO_PUBLIC_API_URL=http://<YOUR_MAC_WIFI_IP>:8000
EXPO_PUBLIC_USE_MOCK_AUTH=true
EXPO_PUBLIC_MOCK_USER_ROLE=owner
EXPO_PUBLIC_COGNITO_USER_POOL_ID=us-east-1_XXXXXXXXX
EXPO_PUBLIC_COGNITO_APP_CLIENT_ID=xxxxxxxxxxxxxxxxxxxxxxxxxx
EXPO_PUBLIC_COGNITO_REGION=us-east-1
```

---

## 9. Password Reset / Maintenance

The Cognito console does not expose a "Set permanent password" button in the new UI. Use the AWS CLI.

### Install AWS CLI

```bash
brew install awscli
aws configure
# Enter: Access Key ID, Secret Access Key, region=us-east-1, output=json
```

Get credentials from: AWS Console → IAM → Users → your user → Security credentials → Create access key → CLI option.

### Set Permanent Passwords

Admin-created users start with `FORCE_CHANGE_PASSWORD` status. Run these to confirm them:

*DEV User Pool - pilot - dev*

```bash
aws cognito-idp admin-set-user-password \
  --user-pool-id us-east-1_XXXXXXXXX \
  --username dev@pilot.local \
  --password '<test-user-password>' \
  --permanent \
  --region us-east-1

aws cognito-idp admin-set-user-password \
  --user-pool-id us-east-1_XXXXXXXXX \
  --username tech@pilot.local \
  --password '<test-user-password>' \
  --permanent \
  --region us-east-1

aws cognito-idp admin-set-user-password \
  --user-pool-id us-east-1_XXXXXXXXX \
  --username office@pilot.local \
  --password '<test-user-password>' \
  --permanent \
  --region us-east-1
```

*PROD User Pool - pilot - prod*

```bash
aws cognito-idp admin-set-user-password \
  --user-pool-id us-east-1_XXXXXXXXX \
  --username dev@pilot.local \
  --password '<test-user-password>' \
  --permanent \
  --region us-east-1

aws cognito-idp admin-set-user-password \
  --user-pool-id us-east-1_XXXXXXXXX \
  --username tech@pilot.local \
  --password '<test-user-password>' \
  --permanent \
  --region us-east-1

aws cognito-idp admin-set-user-password \
  --user-pool-id us-east-1_XXXXXXXXX \
  --username office@pilot.local \
  --password '<test-user-password>' \
  --permanent \
  --region us-east-1
```

> **zsh note**: Use **single quotes** around passwords containing `!` or `@`. Double quotes cause `zsh: event not found: @` errors.

No output = success. The user's status changes from `Force change password` → `Confirmed`.

### Add a New Test User

```bash
# 1. Create in Cognito (verified email, no invitation)
aws cognito-idp admin-create-user \
  --user-pool-id us-east-1_XXXXXXXXX \
  --username newuser@pilot.local \
  --message-action SUPPRESS \
  --user-attributes Name=email,Value=newuser@pilot.local Name=email_verified,Value=true \
  --region us-east-1

# 2. Set permanent password
aws cognito-idp admin-set-user-password \
  --user-pool-id us-east-1_XXXXXXXXX \
  --username newuser@pilot.local \
  --password 'NewPassword2026!@' \
  --permanent \
  --region us-east-1
```

Then run `seed_test_tenant.py` to create the matching DB record.

---

## 10. Lessons Learned — Setup Gotchas

### Gotcha 1: App Type determines User Pool type — SPA required for Amplify

When creating a new Cognito resource, the **App type selection creates a different kind of User Pool**. Selecting "Traditional web application" generates a client secret, which Amplify (browser/public client) cannot use. You must select **"Single-page application"** to get a public client with no secret.

Error symptom: `Client X is configured with secret but SECRET_HASH was not received`

### Gotcha 2: Expo Go cannot use SRP — use `USER_PASSWORD_AUTH`

`USER_SRP_AUTH` (Amplify's default) requires `@aws-amplify/react-native`, a native module that needs `pod install` and a custom Expo dev client or production EAS build. **Expo Go cannot link native modules at all.**

The fix: set `authFlowType: 'USER_PASSWORD_AUTH'` in the `signIn()` call when `navigator.product === 'ReactNative'`. `USER_PASSWORD_AUTH` must be enabled on the App Client ("Username and password" flow in the AWS Console).

Error symptom: `@aws-amplify/react-native doesn't seem to be linked... You are not using Expo Go`

### Gotcha 3: Mobile env vars MUST use `EXPO_PUBLIC_` prefix

Expo Metro only injects variables prefixed with `EXPO_PUBLIC_` into the JavaScript bundle. `NEXT_PUBLIC_` variables are silently ignored — they resolve as `undefined` in the app. If Amplify receives empty pool ID / client ID, `Amplify.configure()` runs but the sign-in attempt fails with a generic error.

Error symptom: `Sign-in failed: Unknown. An unknown error has occurred.`

### Gotcha 4: AsyncStorage required for mobile token persistence

Without explicitly setting `Storage: AsyncStorage` in `Amplify.configure()`, Amplify stores tokens in JS memory only. The Axios request interceptor calls `fetchAuthSession()` on the next async tick after login — by then tokens may be gone from memory, causing 401s on every API call after successful login.

Error symptom: Login succeeds but all API calls immediately return 401

### Gotcha 5: Backend must match frontend's Cognito pool

When changing Cognito User Pools (e.g., region migration), both the frontend **and** backend env vars must be updated. FastAPI verifies JWTs against the JWKS from `COGNITO_USER_POOL_ID` in `backend/.env`. A mismatch causes 401s even when the JWT is valid — it's signed by a different pool.

Error symptom: Mobile login succeeds, JWT is attached (`[apiClient] JWT attached — token prefix: eyJ…`), but all API calls return 401

### Gotcha 6: `Amplify.configure()` must be called before any auth usage

`AuthProvider.tsx` lazily imports `aws-amplify/auth`, but Amplify must be configured at module evaluation time before any component mounts. Place `Amplify.configure()` in a dedicated config file imported as the **first import** in the root layout.

Error symptom: `Amplify has not been configured. Please call Amplify.configure() before using this service.`

### Gotcha 7: Admin-created users require permanent password set via CLI

The new Cognito console (2026) removed the "Set password" UI option for users in `FORCE_CHANGE_PASSWORD` status. The AWS CLI is required:
```bash
aws cognito-idp admin-set-user-password --permanent
```

Error symptom: `Sign-in requires additional steps. Please contact support.` (maps to `CONFIRM_SIGN_IN_WITH_NEW_PASSWORD_REQUIRED` nextStep)

### Gotcha 8: zsh `!` in passwords

The `!` character in zsh double-quoted strings is interpreted as a history event. Always use **single quotes** around passwords in CLI commands:
```bash
# ❌ zsh: event not found: @
aws ... --password "<test-user-password>"

# ✅ works correctly
aws ... --password '<test-user-password>'
```
