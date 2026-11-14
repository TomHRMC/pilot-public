# 📱 Pilot Mobile Field App

This is the Expo (React Native) mobile application for **Pilot For Trades AI**.

## 🎯 Purpose & Persona

This application is designed specifically for **"Mike", the field technician**. It is optimized for use on job sites, often with poor cell service or while wearing work gloves. Its primary functions include:

- Voice-driven commands (Voice AI) for hands-free operation.
- High-contrast, large-hit-target UI for easy tapping.
- Offline-first data entry (Job Time, Expenses, Photos).
- On-site NEC code calculations via AI.

## 🛠️ Tech Stack

- **Framework**: Expo (React Native) + Expo Router
- **Language**: TypeScript
- **Styling & UI**: `gluestack-ui` (v2 - Tailwind CSS powered)
- **Offline Sync**: WatermelonDB + JSI SQLite
- **Data Fetching**: `@pilot/shared-api` (Axios + TanStack Query)
- **Audio/Voice**: `expo-av`

## 🚀 Running Locally

Because this app is part of a Turborepo workspace, you should ideally run it from the root `frontend/` directory.

To start _only_ the mobile application:

```bash
# Run from the root pilot/frontend/ directory
pnpm run dev --filter mobile
```

Once the Metro bundler starts, press:

- `i` to open the iOS Simulator (Requires Xcode).
- `a` to open the Android Emulator (Requires Android Studio).
- Or scan the QR code using the **Expo Go** app on a physical device.

## 🌐 Environment Variables

The mobile app requires a `.env` file in the `apps/mobile/` directory:

```env
# Change this to your computer's local Wi-Fi IP if testing on a physical device!
EXPO_PUBLIC_API_URL=http://127.0.0.1:8000
```

## 🔌 Using Shared Types and APIs

Do not define local API interfaces here. This app consumes the auto-generated database schema from the backend:

```typescript
import { checkApiHealth } from "@pilot/shared-api";
import type { components } from "@pilot/shared-types";
```
