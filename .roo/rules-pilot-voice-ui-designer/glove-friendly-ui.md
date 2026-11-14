# 🧤 Glove-Friendly & Field-Ready UI: Design Rules

> **Design-time agent rule** — written to steer the AI agents during the build and published as last used. Where it differs from the as-built system, [`PROVENANCE.md`](../../PROVENANCE.md) and [`dev-docs/diligence/`](../../dev-docs/diligence/README.md) are correct.

## 1. The "Working Hands" Mandate

The primary goal is to enable **hands-free or single-tap operation** for users wearing work gloves or handling tools. The UI must prioritize voice interactions while providing "oversized" touch targets for manual overrides.

## 2. Touch Target & Layout Constraints

To account for the lack of precision when wearing gloves, all interactive elements must follow these strict sizing rules:

* **Minimum Touch Target**: No button or interactive element shall be smaller than **44x44 points**.
* **Safe Spacing**: Maintain at least **12 points** of margin between adjacent buttons to prevent accidental "fat-finger" taps.
* **Persistent Voice Trigger**: The "Voice Button" must be centrally located and accessible from **every screen** in the application.

## 3. High-Contrast & Visual Logic

Electrical work often happens in basements, attics, or outdoors in direct sunlight. The UI must be readable in all conditions:

* **Contrast Ratio**: Adhere to **WCAG AAA** standards (at least 7:1) for all text and critical iconography.
* **Job Health Indicators**: Use "Stoplight" color logic for real-time profitability:
* **Green**: Job is within budget/on track.
* **Yellow**: Approaching budget threshold (e.g., 80% used).
* **Red**: Budget overrun or critical code warning.


* **Font Weights**: Use **bold or heavy weights** for critical numerical data like total quote price or voltage drop results.

## 4. Voice Interaction Feedback

Since the user may not be looking at the screen, visual and haptic feedback for voice is mandatory:

* **Listening State**: Provide a clear, high-contrast visual wave or "pulsing" animation when the app is actively transcribing via Whisper.
* **Confirmation Cues**: Flash a **green success border** or "check" icon upon successful execution of a voice command (e.g., "Added 100ft copper wire").
* **Ambient Noise Tolerance**: If background noise exceeds **70dB**, display a persistent warning and suggest using the "push-to-talk" mode instead of continuous listening.

## 5. Offline & Field Reliability

* **Local UI State**: The interface must reflect the current state even if the connection to the FastAPI backend is lost, utilizing local caching.
* **Photo Documentation**: The camera interface must allow for **voice-triggered shutters** (e.g., "Take photo") to document job site conditions hands-free.
