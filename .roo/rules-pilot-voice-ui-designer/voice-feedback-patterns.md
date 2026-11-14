# 🔊 Voice Feedback Patterns: Ambient Noise & Interaction Rules

> **Design-time agent rule** — written to steer the AI agents during the build and published as last used. Where it differs from the as-built system, [`PROVENANCE.md`](../../PROVENANCE.md) and [`dev-docs/diligence/`](../../dev-docs/diligence/README.md) are correct.

## 1. The "No-Guessing" Mandate

In high-noise environments (70dB+), the user must never have to guess if the app is listening, processing, or has failed. The UI must provide immediate, high-contrast visual cues to supplement audio feedback.

## 2. Visual "Listening" States

The Voice UI Designer must implement a dedicated "Voice Status Bar" or overlay that reflects the real-time state of the **Whisper Large-v3** pipeline:

* **Idle State**: A subtle, neutral icon (e.g., a gray microphone) indicating the system is ready for a wake-word or tap.
* **Active Listening**: A high-contrast, pulsing animation (e.g., an electric blue waveform) that fluctuates based on detected input volume.
* **Processing (Thinking)**: A distinct "loading" state (e.g., a rotating amber ring) while the **Ollama Llama 3.1 8B** model is parsing intent.
* **Transcribed Text**: Display the "live" text of what the system is hearing at the bottom of the screen to allow for immediate visual correction by the user.

## 3. High-Noise Handling (70dB+)

When the ambient noise threshold is reached, the application must shift its behavior to maintain a < 2s latency target:

* **Noise Warning**: If the noise floor consistently hits **70dB**, display a persistent high-contrast banner suggesting the user move closer to the device or use the "Push-to-Talk" override.
* **Visual Confirmation**: Every successful command must trigger a full-screen "Flash" or a large green checkmark (100x100px) that persists for 1 second, confirming the action was executed (e.g., "Added 200 amp panel").
* **Haptic Feedback**: Use distinct vibration patterns for different outcomes:
* **Success**: One short, crisp vibration.
* **Failure/Retry**: Two long, heavy vibrations.



## 4. Multi-Turn Visual Context

To support the **Entity Resolution** logic, the UI must visually represent what the AI "remembers":

* **Active Entity Highlight**: If the user says "Create quote for Tom Johnson," the customer name should remain pinned to the Voice Status Bar as the active context for the next command.
* **Disambiguation Triggers**: If Ollama identifies multiple "Toms," the UI must present large, glove-friendly buttons for selection rather than relying solely on voice for resolution.

## 5. Error & Fallback Patterns

* **The "I Didn't Get That" State**: If transcription fails or confidence is low, display the recognized text in red with a "Tap to Edit" option using the **44x44px minimum touch target**.
* **Graceful Degradation**: If the local GPU instance is unreachable, the UI must immediately switch to a "Manual Entry Only" mode and inform the user via a high-contrast P2 alert.
