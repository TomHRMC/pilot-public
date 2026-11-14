/**
 * Auth route group layout — mobile
 *
 * Location: apps/mobile/app/(auth)/_layout.tsx
 *
 * FE-B2: New Expo Router (auth) group for login and password-reset screens.
 * Stack presentation for login; password-reset is presented as a modal.
 */

import { Stack } from "expo-router";

export default function AuthLayout() {
  return (
    <Stack screenOptions={{ headerShown: false }}>
      <Stack.Screen name="login" options={{ headerShown: false }} />
      <Stack.Screen
        name="password-reset"
        options={{
          presentation: "modal",
          headerShown: true,
          title: "Reset Password",
          headerLeft: () => null, // Back button handled by PasswordResetFlow
        }}
      />
    </Stack>
  );
}
