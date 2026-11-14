# AI Pitfalls — and the Guardrails That Contained Them

Building a platform to production standards with a multi-agent AI workflow taught one lesson above all: **AI is a brilliant, tireless junior team that will confidently do the wrong thing at superhuman speed.** The speed is real. So is the risk compounding underneath it — code nobody reviewed, decisions nobody owns, work that *looks* finished and isn't.

Across this build, AI agents would repeatedly drift from the directions given in a chat, or from the project's established standards and procedures. Rather than re-correct the same drift every time, the workflow was **hardened with guardrails that removed the agents' latitude to make decisions outside the defined rules.** Each pattern below is a real failure mode from the build, paired with the guardrail built to contain it. Together they're the case for why senior judgment got *more* valuable in the AI era, not less.

*(This is a curated public snapshot of a personal R&D build — "Pilot for Trades," technical design built to the SOC 2 security criteria (not audited), never released, no customers. Specifics are generalized; the patterns are exactly as they happened.)*

---

## 1. The environment the agent kept forgetting
**The drift.** Agents tried to run Python without activating the project's virtual environment, hit `command not found`, and then chased the wrong cause — "maybe I need python3," "let me see what's installed" — instead of the real one.
**The guardrail.** A fixed, mandatory command prefix (activate the venv, from the correct directory) codified into the engineer methods. The agent reads it before acting; running Python any other way is simply not allowed.

## 2. Database schema drift
**The drift.** The physical database and the master schema definition fell out of sync — a migration run without the matching schema-file update, or the schema file hand-edited directly. A stale source of truth would then propagate errors through every downstream analysis.
**The guardrail.** One Golden Master JSON as the source of truth, mutated **only** through a dedicated tool (never by hand), behind a mandatory schema-diff gate that must reconcile the live DB against the master file before any work proceeds. Sync first, always.

## 3. The data-model decisions that stay human
**The pattern.** The agent could implement any field it was told to — but *which* fields to add, which to defer, what should be nullable, and how to sequence schema changes against cost and testing were decisions only a human should make. Hand these to the AI and you get a plausible data model that paints you into a corner months later.
**The guardrail.** The human explicitly owns data-model scope and evolution; the AI drafts and implements against those calls. This is where judgment is least substitutable.

## 4. "It looks like they didn't run the tests"
**The drift.** Agents declared work complete without running the test suite, or ran the wrong scope (the slow full suite instead of the fast unit baseline, or vice-versa).
**The guardrail.** A regression baseline captured *before any file is touched*, and every unit of work reporting `baseline → new, zero regressions, +N tests`. "Done" is never a claim; it's a measured result.

## 5. Code finished, documentation forgotten
**The drift.** The most persistent pattern: the agent completed the code and the immediate section, then skipped the paired bookkeeping — the completion tracker, the finding closeout, the requirements and architecture docs. Work that was "done" in code but invisible everywhere else.
**The guardrail.** "Done" redefined as code **plus** migration **plus** schema update **plus** the paired docs and trackers, enforced by a rigid closeout template so the bookkeeping cannot be silently dropped.

## 6. The security test-endpoints it kept omitting
**The drift.** The architecture requires every secure route to ship with a companion `/test` variant — auth bypassed in DEV/QA (env-gated), blocked in staging and production — so the app can be tested locally without a live authenticated cloud connection. Agents routinely shipped the public endpoint and left the test variant out.
**The guardrail.** A documented dual-endpoint rule, a security-aware production suppression of the API spec, and a systematic audit-and-remediation pass to add the missing test endpoints rather than patching them ad hoc.

## 7. Hallucinated schema
**The drift.** Agents invented column names and database-introspection query shapes when reasoning about the data model — confident, fluent, and wrong.
**The guardrail.** A reference guide plus a standing rule: verify live database state before composing any query. Never hand-trace, never assume.

---

## The through-line

None of these were caught by luck — they were caught because a senior operator was accountable for every output and knew what "wrong" looked like before it shipped. Then each catch became a rule the system enforces, so it couldn't recur. That's the real shape of AI-augmented delivery: the tools make one person dramatically faster, and the judgment layered on top — plus the guardrails that encode it — is what makes the result correct. Take that layer out and you don't get a product. You get the fastest, most confident way yet invented to build the wrong thing.
