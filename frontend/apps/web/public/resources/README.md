# Tenant Website Resources

This directory contains static assets for the C-B16 tenant-site compliance feature.

## Requirements Guide PDF

**File**: `tenant-website-requirements-v1.pdf`

The Requirements Guide is a tenant-facing downloadable PDF containing the
full TCR 10DLC website requirements with worked examples.

- **Content author**: Pilot Architect (from C-SPIKE-2 verified requirements)
- **Layout spec**: `dev-docs/marketing-analysis/design-specs/mkt-c-b16-design-spec.md` §8
- **Versioning**: `tenant-website-requirements-v{N}.*` — increment the version
  number when the content changes. All three files below share the same base
  name and are committed together.

### File set (all three committed, same base name)

| File                                    | Role                                                                                             |
| --------------------------------------- | ------------------------------------------------------------------------------------------------ |
| `tenant-website-requirements-v{N}.md`   | **Text source of truth** — Architect-authored content                                            |
| `tenant-website-requirements-v{N}.docx` | **Layout working file** — exported from the Google Doc; this is what you reopen for layout edits |
| `tenant-website-requirements-v{N}.pdf`  | **Published artifact** — the file the app links and serves                                       |

## Download Links

The PDF is linked from:

1. Settings > Website → WebsiteRequirementsPanel (Option 1 card)
2. C-B9 10DLC profile form → WebsiteRequirementsPanel (below the website field)

Links use the path `/resources/tenant-website-requirements-v1.pdf` with the
`download` attribute.

## PDF Generation — Google Docs Process (standing, as of 2026-08-16)

> **Process history**: the originally-specified pipeline (markdown →
> print-stylesheet HTML → headless-Chrome print-to-PDF, mkt spec §8.8) was
> tried and **abandoned** — the render did not hold the §8 layout (margins,
> repeating header/footer, checklist/figure treatment) cleanly. The v1 PDF was
> produced manually via Google Docs, and that is now the standing process for
> every future version. The `tenant-website-requirements-v1.html` intermediate
> from the abandoned pipeline is retired — **delete it** if still present.

To produce a new (or updated) version:

1. **Edit the source** — update `tenant-website-requirements-v{N}.md`
   (content authority: Architect, from verified TCR requirements).
2. **Convert** — upload/import the `.md` into Google Docs and convert it to a
   Google Doc.
3. **Lay out manually** in the Google Doc, applying mkt spec §8.1–§8.7:
   US Letter, 0.75" top/bottom + 0.875" left/right margins; §8.4 typography
   scale; cover block (§8.3); page header/footer on content pages only (§8.5);
   checklist box (§8.6); figure treatments (§8.7).
4. **Export both formats** from the Google Doc: File → Download →
   **PDF Document (.pdf)** (the published artifact) and **Microsoft Word
   (.docx)** (the layout working file — keeps future edits out of the
   conversion step).
5. **Name + commit the triple** — `tenant-website-requirements-v{N}.md`,
   `.docx`, and `.pdf` in this directory. If N was bumped, update the two
   in-app download links (above) and the one-time requirements-email URL
   (C-B16 email task) to the new versioned filename.
