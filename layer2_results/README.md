# Local generated artifacts (not tracked)

This directory is intentionally ignored by Git. It holds cached basis curves,
detector point-wise scores, manifests, Raw VUS calculations, and Stage-2 audit
outputs. The current local cache is approximately 4 GB.

For a collaborator who needs to reproduce Protocol v1 without rerunning neural
detectors, restore the same cache tree here, then run:

```powershell
python scripts\validate_workspace.py
```

Do not overwrite an audited cache in place. Use a separate results location or
branch and record a new manifest/signature.
