# 🛠️ Trade Shorthand Lexicon: Intent Mapping Rules

> **Design-time agent rule** — written to steer the AI agents during the build and published as last used. Where it differs from the as-built system, [`PROVENANCE.md`](../../PROVENANCE.md) and [`dev-docs/diligence/`](../../dev-docs/diligence/README.md) are correct.

## 1. The "Field-to-Code" Translation Mandate

The Electrical Domain Expert must use this lexicon to ensure that the **Ollama Llama 3.1 8B** model correctly interprets informal voice commands. Every "slang" term must be mapped to its corresponding **NEC-compliant** technical category or material ID.

## 2. Common Electrical Shorthand Mappings

The agent must use the following table to resolve intents and populate quote line items:

| Field Term (Shorthand) | Technical Mapping | Logic/Constraint |
| --- | --- | --- |
| **"Romex"** | NM-B (Non-Metallic Sheathed Cable) | Default to **12/2** or **14/2** based on circuit amperage. |
| **"MC"** | Metal-Clad Cable | Check if "Healthcare Grade" is required for commercial tasks. |
| **"Home Run"** | Branch Circuit originating from Panel | Calculate total distance to the first outlet/device. |
| **"Pigtail"** | Conductor Lead/Connection | Include wire nuts and 6 inches of conductor in material list. |
| **"Mud Ring"** | Plaster Ring / Device Bracket | Match size to the number of gangs requested. |
| **"KO"** | Knockout | Ensure appropriate bushings or connectors are added to the quote. |
| **"Smurf Tube"** | ENT (Electrical Non-metallic Tubing) | Verify use cases; typically for low-voltage or specific flex needs. |

## 3. Quoting Logic for "Assemblies"

When a user mentions a high-level task, the agent must expand it into a full "Assembly" of parts to maintain **>98% pricing accuracy**:

* **"Add a 20 amp circuit"**: Automatically include: 1x 20A Breaker, ~50ft 12/2 Romex/MC, 1x Single-gang box, 1x 20A Receptacle, 1x Wall plate, and 5x Wire nuts.
* **"Service Upgrade"**: Include: 1x Main Panel, 1x Meter Socket, Grounding Rods, Grounding Clamp, and appropriate Service Entrance (SE) cable.
* **"Three-way switch"**: Ensure two 3-way switches and 14/3 or 12/3 "traveler" wire is added to the quote.

## 4. Contextual Disambiguation

The agent must use the current job context to resolve ambiguous terms:

* **"Panel"**: If in a residential session, default to a **200A Load Center**; if in commercial, check for **Three-Phase** requirements.
* **"Boxes"**: If the user says "Add 10 boxes," default to the type previously used in the current quote (e.g., Plastic vs. Metal).

## 5. NEC Warning Triggers

If the user uses shorthand that implies a code violation, the agent must trigger a warning:

* **"Run Romex in the slab"**: Flag as a violation; Romex (NM-B) is not rated for wet/damp underground locations.
* **"T-tap the 15 amp"**: Ensure the user isn't exceeding maximum circuit capacity.
