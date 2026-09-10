# CDU 实验运行命令

在本目录打开 PowerShell 后运行：

```powershell
python step2_oneliner_bench.py 350 8
python cdu_analysis.py
python make_report.py
```

`step2_oneliner_bench.py` 每 10 条序列断点落盘；再次执行同一命令会跳过已有完整行。第三个参数可指定输出文件名，第二个参数是并行进程数（内存不足时改为 4）。

完成后主要产物位于 `results/`：`basis_vuspr.csv`、`cdu.csv`、`rerank.csv`、`layered.csv`、`sanity.md`、`cdu_scatter.png`，中文报告为 `report.md`。
