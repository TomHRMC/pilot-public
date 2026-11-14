# Pilot for Trades Quote Architecture: Line Items, Visibility, Templates, and Styles

**Version**: 1.0
**Status**: Locked
**Date**: April 25, 2026
**Scope**: Quote data model, line item structure, template system, presentation styles
**Triggered By**: Pass 3 Flow 5 design discussions; competitive analysis of generator-install quotes (Contractor A, Contractor B)
**Affects**: PRD §3.10 (Sales & Quoting), `mvp-arch.md` quote section, Pass 3 Flow 1 spec, Pass 3 Flow 2 (profitability calculation)
**Location**: `dev-docs/architecture-design/`

---

## Purpose

Original Pilot quote design assumed component-level line items: each quote is a flat list of materials and labor lines, each with its own price, presented to the customer in detail. This works for service calls and small jobs.

Real-world contractor quotes often use different presentation strategies. Analysis of two real generator-install quotes (sizes around $12,000) revealed:

- **Contractor A** uses Services + Materials sections, where each *Service* (e.g., "Generator Install Air-Cooled" at $1,738) bundles many implicit components into a single customer-facing deliverable with rich descriptive text
- **Contractor B** uses lump-sum: the entire 26kW system is one $12,189 line with a long bulleted description

These aren't formatting preferences. They're business strategies — contractors choose how itemized to be based on customer trust, margin protection, and the nature of the work. Pilot's quote system must support all three styles or it forces tenants into a presentation that doesn't match how they sell.

This document locks the architectural changes required to support component, deliverable, and lump-sum quote styles with a single flexible data model.

## Three Quote Styles Pilot Will Support

### Style 1: Component-Level

Every part, labor line, and material gets its own line. Customer sees the full breakdown.

**Use case**: Service calls, small repairs, work where transparency builds trust, jobs where line-by-line negotiation is expected.

**Example** (from earlier flows):
```
Square D 200A main breaker          $318.00
42-circuit panel                    $486.00
4/0 SER service cable               $164.00
Permit + inspection                 $225.00
Labor · 6.5 hrs @ $145/hr           $942.50
```

### Style 2: Deliverable-Level

Components are bundled into customer-visible deliverables, each with rich descriptive text. Internal cost components remain in the database for margin tracking but aren't shown on the customer-facing quote.

**Use case**: Installations, multi-phase work, jobs where the contractor wants to sell the *outcome* rather than the parts. Common in HVAC installs, generator installs, panel upgrades sold as packages.

**Example** (deliverable-level quote):
```
Generator Install Air-Cooled         $1,738.00
   - Generator location: left side of home, 5' from crawlspace
   - Coordination with power company: DEC
   - Coordination with town/county permitting if necessary
   - Level and set generator on 3.5" solid concrete pad
   - All NEC and NFPA-compliant installation
   - Project support staff in contact every step
   - Complete final cleanup and debris removal
   - Test backup power system and full inspection
   - 3rd party inspection agency verification

Automated Transfer Switch Installation $928.00
   - Mount ATS next to meter panel combo
   - Pipe between ATS and electric meter, pull feeder wires
   - Refeed electric panel from ATS with new SE cable
   - Separate neutrals and grounds in panel
   - Install new grounding (2 ground rods + copper wire)
   - Test automatic transfer mechanism
```

Internally, "Generator Install Air-Cooled" is parented to multiple hidden child lines tracking the actual cost basis (labor hours, conduit, fittings, etc.) so the profitability report from Flow 2 still works correctly.

### Style 3: Lump-Sum

The entire job is one customer-visible line with prose description. Internal cost decomposition still exists for margin tracking but the customer sees a single price.

**Use case**: Established contractors with high customer trust, brand-protected pricing, projects where the contractor doesn't want line-by-line scrutiny, fixed-bid work.

**Example**:
```
26kW Generator System Installation    $12,189.00
   [Long bulleted description of full scope]
```

## The Data Model: Flat Line Items with Visibility + Parent Links

The chosen approach (Option A from design discussions) achieves all three styles with one flexible structure rather than three separate hierarchies.

### Schema Changes to `quote_line` (or equivalent existing table)

```
quote_line (additions)
  customer_visible       BOOLEAN NOT NULL DEFAULT TRUE
  parent_line_id         UUID NULL REFERENCES quote_line(id) ON DELETE RESTRICT
  display_order          INT NOT NULL  -- ordering within the quote, separate from creation order
  description            TEXT NOT NULL  -- existing; verify supports multi-line + bullets
  is_section_header      BOOLEAN NOT NULL DEFAULT FALSE  -- "Services", "Materials" etc., no price
```

**Field semantics:**

- `customer_visible = TRUE` → line appears on customer-facing PDF, mobile preview, and customer-facing email
- `customer_visible = FALSE` → line is internal-only, used for cost tracking, never shown to customer
- `parent_line_id IS NULL` → top-level line, displayed in customer-facing rendering when visible
- `parent_line_id IS NOT NULL` → child line, contributes to parent's roll-up totals
- `is_section_header = TRUE` → renders as a section divider (e.g., "Services" / "Materials"), no price column populated

### How Each Style Uses the Same Model

**Component-level quote**: every line has `customer_visible = TRUE`, `parent_line_id = NULL`. Flat, fully visible.

**Deliverable-level quote**: customer-visible parent lines (e.g., "Generator Install Air-Cooled") with `parent_line_id = NULL` and rich `description` text. Hidden child lines reference these parents and track actual costs (labor hours, materials) for margin computation.

**Lump-sum quote**: one customer-visible parent line ("26kW Generator System Installation") containing the full prose description. All cost decomposition lives in hidden child lines.

**Mixed-style quote** (now supported per locked decision): a deliverable parent line + several component-level visible lines beneath it (no parent link). The model doesn't enforce style consistency across a quote — it's a per-line-item property.

### Roll-Up Math

For any customer-visible line with hidden children:
- Customer sees: parent's `total_amount` (set explicitly by the user, not auto-computed from children)
- Internally: the line's `cost_basis` is the sum of children's amounts; this drives margin calculation
- The parent's `total_amount` does NOT need to equal sum of children's amounts (that's the point — margin is `parent_amount − sum_of_children`)

This is critical for margin tracking. A "Generator Install Air-Cooled" deliverable priced at $1,738 customer-facing might have $920 in internal cost components — margin = $818 (47%). The profitability report (Flow 2) reads from this structure.

### Section Headers

For tenants who use Services + Materials groupings (like Contractor A), `is_section_header = TRUE` lines act as visual dividers in customer-facing rendering. They have a description ("Services") and no amount. They're top-level (`parent_line_id = NULL`) but don't carry totals themselves.

Section headers are optional — a tenant who doesn't want sections just doesn't create them.

## Quote Templates and Styles

### Template-Driven Style Selection

A quote template carries a `style` attribute (`component | deliverable | lump_sum`). When a tech or owner creates a quote from a template, the quote inherits the template's style and starts with the template's pre-populated lines (with appropriate visibility flags and parent relationships baked in).

**Templates carry the style in two ways:**
1. The `style` attribute itself (used for UI affordances — e.g., a deliverable-style template's editor surfaces the rich-description editor more prominently)
2. The actual structure of the template's pre-populated line items (which visibility flags are set, which parent links exist)

A tech using a "Service Call" template (component-style) sees a flat list ready for line additions. A tech using a "Generator Install" template (deliverable-style) sees pre-grouped parent deliverables ready for description tweaks and child-cost adjustments.

### Template Ownership: System vs. Tenant

**System templates**: shipped with Pilot, platform-owned (the Pilot for Trades operator manages these centrally — tenants cannot edit). Read-only to tenants. Versioned (e.g., `system_template_id` + `version`).

**Tenant templates**: created by the tenant, either:
- By forking a system template (creating a tenant copy that can be customized)
- By saving a quote as a template (the "save as template" capability)
- By creating from scratch in Settings

Tenants only edit their own templates. System templates are reference material.

### Template Versioning and Update Flow

System templates evolve over time as Pilot improves them. The flow:

1. Pilot releases a new version of a system template (e.g., system template `service_call_v1` → `service_call_v2`)
2. Existing tenants' tenant templates that were forked from `service_call_v1` are not automatically updated
3. Tenants are *notified* in their Settings UI: "Pilot has released v2 of [Template Name] — you are using a customization based on v1. View changes."
4. Tenant chooses to:
   - **Pull the new version**: a new tenant template is created from `service_call_v2`. Old tenant template is preserved (and optionally disabled, not deleted).
   - **Stay on the old version**: nothing happens, no friction
5. Quotes already created against the old tenant template continue to render correctly because each quote's line items are immutable per the existing quote_version pattern

**Key implementation note**: the tenant template should store both `system_template_id` (which system template it derives from) and `forked_from_version` (which version of that system template it was based on). This makes "you're 2 versions behind" notifications possible.

### MVP Seed: System Templates Per Style

Pilot ships with at least one system template per style as defaults available to every tenant from day one:

- **`service_call_basic`** (component-style) — small repair / diagnostic / single-fix work
- **`installation_standard`** (deliverable-style) — multi-deliverable installation work
- **`fixed_bid_simple`** (lump-sum-style) — single-line whole-job pricing

These exist as documentation-by-example. A tenant can use them as-is, fork and customize, or ignore them and build their own templates.

Trade verticals (electrical, plumbing, HVAC) may eventually have their own seed sets; for MVP a generic seed set is acceptable.

### "Save Quote as Template" Capability

Owners can save any approved or sent quote as a tenant template. The save:

1. Captures all customer-visible line items, their descriptions, parent relationships, and cost basis structures
2. Replaces customer-specific data with template variables (customer name → `{customer_name}`, site address → `{site_address}`)
3. Strips quote-specific values that wouldn't transfer (the actual quote total, the specific quote number)
4. Prompts the owner for a template name and category

Implementation note: customer-specific scrubbing requires the dev team to identify which fields must be templatized. Initial set: customer fields, site fields, contact fields, dates, quote numbers. Material quantities and labor hours stay as defaults but are clearly marked as override-able when the template is later used.

## Multi-Line Description Support

Every line item's `description` field must support:

- Plain text up to several thousand characters (the longest line description in the Contractor A quote ran ~700 characters across 12 bullets)
- Newlines preserved on render
- Basic bullet-list formatting (a leading `- ` or `* ` per line is sufficient for MVP; rich text editor is Phase 2)

**UI implications:**

- **Mobile editor**: multi-line text area, not single-line input. Bullet auto-formatting on `-` press is a nice-to-have; for MVP a plain multi-line area is sufficient.
- **Web editor**: same multi-line area, more screen real estate. Phase 2 could upgrade to a markdown-aware editor.
- **Voice editing**: composing 700-character descriptions verbally is impractical. For deliverable and lump-sum styles, descriptions are typically *template-derived* — the template carries the prose, the tech just confirms or makes minor variable substitutions.

**Voice + rich descriptions interaction**: when a tech voice-creates a quote from a deliverable template, the AI's response acknowledges the template and confirms variable substitutions ("Using the standard Generator Install template — confirm location is left side of home?"). The tech doesn't compose the prose; they confirm the inserts.

## Implications for Other Flows

### Pass 3 Flow 1 (Voice Quote Creation)

The voice flow's quote-card rendering needs to handle three styles:

- **Component-style**: the existing card design (line items as a flat list with prices) works as-is
- **Deliverable-style**: card shows the parent line(s) with collapsible bullet-list descriptions; child cost lines are not shown to the tech because they're internal cost tracking
- **Lump-sum-style**: card shows one prominent line with the full description as expanded prose

Voice grammar adjustment: when tech is using a deliverable-style template, "add a line" prompts for which deliverable to add to (or to add a new top-level deliverable). "Add 5 breakers" against a deliverable-style quote becomes a child cost component (internal), not a customer-visible line.

The tech can switch between viewing customer-facing rendering and internal-detail rendering on the quote-card preview. This needs a small UX addition to the voice flow's preview state — a toggle: "Customer view / My view." For MVP this can be a simple chip.

### Pass 3 Flow 2 (Profitability)

Profitability calculation logic must:

- Roll up actual costs from child cost-tracking lines, not just sum visible lines
- Compute margin as `(visible_total) − (sum_of_actual_costs_including_hidden_children)`
- Handle quotes with mixed visibility correctly

The Flow 2 spec already assumed margin = revenue − cost; the architectural change is that "cost" now reads from a richer structure including hidden children rather than just visible labor + material lines.

### Pass 3 Flow 5 (Approval Workflow)

The approval flow now has to handle:

- Editing customer-facing lines (description, qty, amount)
- Editing internal cost-tracking lines (only visible to owner during review)
- Adding/removing visible deliverables vs. adding/removing internal children
- Distinguishing kickback comments on customer-visible vs. internal lines

The owner-edit UI must clearly distinguish "what the customer sees" from "what tracks our cost." This is the most significant Flow 5 design implication and will be addressed when we resume Flow 5 design.

## Naming Disambiguation: Two Different "Templates"

Pilot now has two distinct concepts both called "templates":

1. **Quote templates** (this document) — pre-populated quote structures used to start new quotes
2. **Communication templates** (Pass 2 A4, Flow 4) — pre-built messages for customer comms ("On my way", "Job complete")

These are completely different domains. To prevent confusion in code, schema, and discussion:

- **Code/schema**: prefer `quote_template` and `communication_template` as full names; never standalone `template`
- **API**: `/api/v1/quote-templates/...` and `/api/v1/communication-templates/...`
- **UI**: distinguish in Settings as "Quote templates" and "Customer communication templates" in separate sections
- **Documentation**: always qualify which kind of template is meant

## Validation Checklist

Before implementation begins:

- [ ] Dev team aligned on the flat-with-visibility-flags data model
- [ ] Schema additions reviewed against existing `quote_line` table
- [ ] Roll-up math (parent total = explicit, not auto-summed) understood and documented
- [ ] System template seed set drafted (one per style)
- [ ] Multi-line description rendering verified in PDF generation pipeline
- [ ] Naming convention (`quote_template` vs `communication_template`) adopted across team
- [ ] Profitability calculation in Flow 2 verified to handle hidden children correctly

## Open Questions for Dev Team Review

1. **Existing `quote_line` schema audit**: confirm `description` is `TEXT` with no length cap, and that the new boolean and FK columns can be added without disruption
2. **PDF rendering pipeline**: confirm the existing customer-facing PDF generator can handle multi-line bullet descriptions and section headers
3. **Audit trail**: when an owner edits a tenant template, the changes propagate to *future quotes from that template* but not to existing quotes — verify this is the intended behavior
4. **Template variable substitution**: define the variable namespace for "save quote as template" (`{customer_name}`, `{site_address}`, etc.) — needs to match existing variable conventions if any
5. **Permission model**: who can create/edit tenant templates? Owner only, or also accountant role?

---

*This document captures architectural decisions that propagate through multiple PRD domains and design flow specs. Future flows that touch quoting must reference this document.*
