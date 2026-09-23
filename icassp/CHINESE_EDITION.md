# 中文审阅版

- 英文投稿源文件：main.tex，PDF：main.pdf。
- 中文完整译稿：main_zh.tex，PDF：main_zh.pdf。
- 中文正文：sections/focused_abstract_zh.tex 和 sections/focused_body_zh.tex。
- 中文结果表：tables/focused_results_zh.tex。
- 图中文字与图注已翻译；模型名称及参考文献保留原文。
- 数字、公式、论述范围与英文稿一致；不是新的实验结果。

Windows 下编译中文稿：

~~~powershell
powershell -NoProfile -ExecutionPolicy Bypass -File icassp/build_zh.ps1
~~~

采用 XeLaTeX + xeCJK，字体为宋体、黑体、微软雅黑及 Times New Roman。
其他系统需要安装对应字体或明确配置替代字体。中文稿用于讨论审阅，
其分页独立于英文投稿版本，不应将中文排版文件误当成会议官方模板。

Fig. 2 最新样式：去掉区间图中贯穿所有点的零竖线及区间端帽；
以零刻度保留数值参照，细线显示完整置信区间；缩小标记、增加绘图区
行距和两端留白。没有改变数据坐标或区间端点，也没有使用抖动移动点。
