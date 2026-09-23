# 当前运行与后续队列

2026-09-14 本机当前 evaluator 为 PID 53556，命令依次计算 SubPCA、POLY、MOMENT_FT。Shared baseline 已完成；保持此进程运行。

已准备 `scripts/queue_fast_controls.ps1`，目标为 Fast duplicate、noise、alpha2，支持既有 source checkpoints。它先等指定 evaluator 退出，之后独立进程逐个运行 control；某 control 失败会保留错误并继续下一个。它不会重新计算 detector。

**准备状态：已 dry-run；本次未启动 waiting process。** 原请求“另外三个实验”尚未明确是否指 controls；另外六个 detector 已分配给其他机器，因此先确认对象，以免重复工作。

确认是这三个 controls 后，可以从项目根目录启动后台 waiting process：

```powershell
$queueRoot = (Get-Location).Path
$queueTag = Get-Date -Format yyyyMMdd_HHmmss
$queueArgs = @('-NoProfile','-ExecutionPolicy','Bypass','-File',
    'scripts\queue_fast_controls.ps1','-WaitForPid','53556',
    '-PythonExe',(Get-Command python).Source)
$queueProcess = Start-Process powershell.exe -ArgumentList $queueArgs `
    -WorkingDirectory $queueRoot -WindowStyle Hidden -PassThru `
    -RedirectStandardOutput "protocol_fast_results\logs\controls_queue_$queueTag.stdout.log" `
    -RedirectStandardError "protocol_fast_results\logs\controls_queue_$queueTag.stderr.log"
$queueProcess.Id
```

只启动一份 queue。PID 53556 仅是本次运行；重启本机 evaluator 后须先核实新 PID。若该 PID 已不存在，则脚本立即开始 controls；若它已被非 Fast 程序占用，则拒绝启动。

当前实验进度：

```powershell
Get-Content protocol_fast_results\logs\local_detectors.stdout.log -Tail 20 -Wait
```

Controls 输出目录按 evaluator 现有结构是 `protocol_fast_results/main/duplicate_Var-96/`、`main/independent_noise/`、`main/complementary_alpha_2/`，不要误认为它们属于九个真实 detector。旧 nested controls 在 `protocol_v1_results/controls/`，二者分开保存。
