# Manuscript content freeze — 2026-09-24

Status: FROZEN by the author's instruction after the final terminology and bibliography pass.

The authoritative submission is `main.tex` -> `main.pdf`: four pages of technical content and one references-only page. The active prose files are `sections/focused_abstract.tex`, `sections/focused_body.tex`, and `sections/results_revised.tex`. The Chinese reading edition has not been synchronized with this final English revision.

## Final changes

- Abstract: "complementary evaluation axis".
- Section 4.2: low reconstructibility alone does not imply conditional contribution.
- Section 4.3: "Conditional rankings are stable" and the factual basis-only loss comparison.
- Acknowledgment replaced verbatim at the author's subsequent request: "OpenAI Codex was used for language and clarity editing. The authors reviewed and verified the final manuscript."
- Bibliography: supplied publication metadata retained; publication URLs and the Conditional Probing arXiv identifier recorded. Its EMNLP proceedings citation and Christopher D. Manning's initial are retained.
- Author order: Yizhou Wang, Kecheng Su, Shufan He, Song Gao, Xiaolong Wang, Rui Huang, Fangming Gu (corresponding author).

Both figures, their captions and inclusion settings, and Table 1 were left unchanged at the author's explicit request. Figure-internal wording is therefore not part of this terminology pass.

## Checks

The final build has five pages, with references only on page 5. No LaTeX warnings, undefined citations, or overfull boxes were reported. Rendered pages were checked. The figure PDF and table source hashes are unchanged from before this pass.

## Frozen SHA-256 identifiers

```text
18BCF48CD51C210FC5233DA9D00442C19869BB984200C1BFB603B0B81185B48E  main.pdf
331715FEBE61809659826F473DA6B26274A703BBF846671F71DB5B14F6E431C2  main.tex
EF93C15698A79EC5F8B65347A5331F8A6ADB171AA717CC13CDA565B495CACF9B  sections/focused_abstract.tex
6FAE1DE38AA81064CB8B5AE864E2F868BE8BC8B4F61755AC4EAD3F492DAEB646  sections/focused_body.tex
599D6894D84BBD2D81CF740322BDB096B13E49E7B29C1D4EAF6B8088C5CA7C38  sections/results_revised.tex
5C9A4C9B849E328140B05CF84BF827621CB04E56825DA450675CC973B8D6ED27  references.bib
0632430F1539B92F121A8BF022287EA546AF1B4BCE47D40E9CF2F52794D92202  figures/main_concept.pdf
14C95F71BBBEBD5CDF8E6B09F32CA590D1AABC9E125A7F6408EB2FDBBCE2563C  figures/conditional_comparison.pdf
F76126641D5BFD2A7924AE84B1265468AD422DADB857E7FAA0B9546D1781B014  tables/primary_results.tex
```

On 2026-09-26, the author authorized adding the public repository URL to the Introduction. This targeted availability statement is included in the hashes above; figures, tables and numerical results are unchanged.

The PDF hash identifies this exact compiled file; a later identical-source build can differ in PDF timestamps.

Do not run general rewriting, broad polishing, automatic limitations expansion, figure regeneration, or numerical updates. Further edits require a specific author request or a demonstrated factual/submission-format error. This freeze is a local document record, not a Git commit or tag.
