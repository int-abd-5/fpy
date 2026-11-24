# F26-012 Native LaTeX Report Conversion

## Goal

Rebuild the F26-012 report as editable LaTeX source using the FYP committee's supplied `FastFyp.cls`, preserving the report's main content while applying the evaluator's corrections.

## Work plan

- [x] Inspect the provided class, source report, existing wrapper, and repository state.
- [x] Confirm page ranges, report headings, figure/table inventory, and source publication venues.
- [x] Create a separate native LaTeX project with the unmodified committee class and supplied cover assets.
- [x] Transcribe the PDF's front matter and Chapters 1–6 into native LaTeX sections, tables, and figures.
- [x] Number figures and tables by chapter, remove the all-SDG figure and appendices, add declaration signatures, and update bibliography entries.
- [x] Compile with Tectonic and provide Overleaf build steps.
- [x] Inspect the generated PDF and verify the source package contents.

## Constraints

- Keep the existing PDF-wrapper project and unrelated working-tree changes untouched.
- Do not alter `FastFyp.cls`; use it as supplied.
- Do not reproduce the 31 pages of repetitive traceability matrices after References.
- Use only a relevant SDG illustration (SDG 9) in Chapter 2.
- Preserve factual report content except for changes required to satisfy the evaluator's corrections and publication metadata.
