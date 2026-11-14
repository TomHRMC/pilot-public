# Follow-up question suggestions

> **Design-time agent rule** — written to steer the AI agents during the build and published as last used. Where it differs from the as-built system, [`PROVENANCE.md`](../../PROVENANCE.md) and [`dev-docs/diligence/`](../../dev-docs/diligence/README.md) are correct.

## 1. How to CALL the `ask_followup_question` tool (format is mandatory)

The `ask_followup_question` tool takes **structured arguments**, never a plain
string. Every call MUST provide:

- **`question`** — a single clear string.
- **`follow_up`** — a **list of 2–4 suggestion objects**, each an object with a
  `text` key (the complete, actionable answer) and a `mode` key set to `null`.

A suggestion is NOT a bare string and NOT free-form prose in the question body.
If you catch yourself typing the answer options as sentences inside `question`,
STOP — move them into the `follow_up` list as proper objects.

**Correct call shape** (arguments):

```json
{
  "question": "Which database should the service use?",
  "follow_up": [
    { "text": "Use PostgreSQL 17 on RDS", "mode": null },
    { "text": "Use the existing shared cluster", "mode": null }
  ]
}
```

**Forbidden:**
- Passing `follow_up` as a single string, or as a newline-joined blob of text
  instead of a list of objects.
- Emitting the suggestions as plain markdown/prose in the message body instead of
  through the tool's `follow_up` argument.
- Omitting `follow_up` entirely when you are asking the user to choose between
  options — always give 2–4 concrete, ready-to-pick answers.
- Placeholders like `<path here>` or `[option]` — every suggestion must be a
  complete, immediately-usable answer.
- Including any `mode` other than `null`

## 2. Never switch modes from inside a suggestion

`mode` on every suggestion object MUST be `null` (equivalently, in the legacy
`<suggest>` XML form, never add a `mode` attribute):

- All suggested answers must return the response within the current mode only.
- Do not offer suggestions that switch to Code, Architect, Debug, or any other
  mode. Each suggestion contains only the answer text — `<suggest>Use PostgreSQL</suggest>`,
  never `<suggest mode="code">Use PostgreSQL</suggest>`.

If a different mode would genuinely be better suited for the next step, say so in
the `question` text and let me switch modes manually. Never initiate or embed a
mode switch inside a suggestion.