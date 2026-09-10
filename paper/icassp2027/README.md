# ICASSP 2027 four-page skeleton

`main.tex` freezes the proposed four-page narrative and page-budget comments. It intentionally contains placeholders rather than copying Stage-2 random-series numbers into the source-grouped table.

Suggested local build:

```powershell
cd paper\icassp2027
pdflatex main.tex
pdflatex main.tex
```

Before submission, replace the anonymous author block as required by the venue, import the official ICASSP template if it differs from the local IEEEtran class, verify the current call-for-papers instructions, and regenerate every number/figure from the frozen protocol-v1 outputs.
