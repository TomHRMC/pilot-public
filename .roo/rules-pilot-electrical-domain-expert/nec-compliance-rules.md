# ⚡ NEC Compliance & Electrical Logic: Domain Rules

> **Design-time agent rule** — written to steer the AI agents during the build and published as last used. Where it differs from the as-built system, [`PROVENANCE.md`](../../PROVENANCE.md) and [`dev-docs/diligence/`](../../dev-docs/diligence/README.md) are correct.

## 1. The Safety First Mandate

The Electrical Domain Expert must prioritize **National Electrical Code (NEC)** compliance above all other quoting or calculation logic. All generated quotes and AI-suggested assemblies must meet or exceed **NEC 2023/2026** standards to ensure passed inspections and user safety.

## 2. Mandatory Calculation Formulas

When performing electrical calculations via voice or UI, the agent must use the following industry-standard formulas:

* **Voltage Drop (Single Phase)**: $VD = \frac{2 \times R \times I \times L}{1000}$.
* **R**: Resistance of conductor (Ohms per 1000 ft at 75°C).
* **I**: Load current in Amperes.
* **L**: Length of conductor in feet.


* **Ampacity**: Must adhere to **NEC Table 310.16** for allowable ampacities of insulated conductors.
* **Conduit Fill**: Must follow **NEC Chapter 9, Table 1** (e.g., 40% fill for over two wires).

## 3. Trade Lexicon & Intent Mapping

To minimize latency and improve Ollama's intent classification, the agent must map common "field talk" to technical terms:

| User Input (Shorthand) | Technical Mapping (NEC/Catalog) | Logic Constraint |
| --- | --- | --- |
| **"Romex"** | Non-Metallic Sheathed Cable (Type NM-B) | Verify if exposed or in damp location. |
| **"MC"** | Metal-Clad Cable (Type MC) | Check for proper grounding bushings. |
| **"200 Amp Service"** | 200A Main Service Entrance | Include panel, meter socket, and grounding electrode. |
| **"Daisy Chain"** | Series-Parallel Wiring | Check for maximum outlet counts per circuit. |
| **"Pig Tail"** | Conductor Termination | Ensure wire nut/connector size matches gauge. |

## 4. Quoting & Assembly Guardrails

* **Material Accuracy**: Quotes must include all NEC-required smalls (wire nuts, staples, bushings) to maintain the target **>98% pricing accuracy**.
* **GFCI/AFCI Requirements**: If the intent involves "Kitchen," "Bathroom," "Garage," or "Outdoor," the AI must automatically suggest **GFCI protection** in the line items.
* **Labor Estimation**: Suggested labor hours must account for the complexity of the task (e.g., "Fishing wire through finished wall" vs. "Open stud").

## 5. Automated Validation

* **Overload Warning**: If a user tries to "Add a 20-amp load to a 15-amp circuit" via voice, the AI must respond with a **Code Warning** before executing the command.
* **Pricing Updates**: Cross-reference all suggested materials against the **Ferguson/Rexel API** feeds to prevent underquoting due to price volatility.
