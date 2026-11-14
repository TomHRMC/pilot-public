import type { Config } from "tailwindcss";
import { pilotPreset } from "@pilot/ui/tailwind.preset";

export default {
  presets: [pilotPreset],
  content: ["./src/**/*.{ts,tsx}", "../../packages/ui/src/**/*.{ts,tsx}"],
} satisfies Config;
