# Generated Protocol v1 results (not tracked)

This directory contains resumable formal-control checkpoints, pilot outputs,
main-run outputs, logs, and signatures. It is ignored because it is generated
from external basis/detector caches.

The control runner checkpoints by outer source. Resume with:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\run_protocol_v1_control_queue.ps1 -BaselinePid 0
```

Do not reuse a checkpoint if `RUN_SIGNATURE.json` does not match current inputs
and code.
