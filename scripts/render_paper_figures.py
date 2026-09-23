"""Paper vector graphics from existing evidence only; no detector execution."""
from pathlib import Path
import hashlib
import json
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.colors import to_rgb
from matplotlib.patches import Rectangle
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "paper/evidence/fast_main/MAIN_RESULTS.csv"
OUT = ROOT / "icassp/figures"
OUT.mkdir(exist_ok=True)
df = pd.read_csv(SRC).sort_values("CDU_rank")
assert len(df) == 9 and df.Detector.nunique() == 9
assert (df.n_series == 350).all() and (df.n_sources == 23).all()
plt.rcParams.update({"font.family":"serif", "font.size":8,
    "pdf.fonttype":42,"ps.fonttype":42,"axes.spines.top":False,"axes.spines.right":False})
blue, ink = "#265e83", "#30343b"
# Fixed categorical identities, inspired by the user's supplied palette.
# Color is redundant with shape and is not a significance encoding.
styles = {
    "SubPCA": ("#6E8FB2", "o"),
    "POLY": ("#7DA494", "s"),
    "MOMENT_FT": ("#EAB67A", "^"),
    "MOMENT_ZS": ("#9F8DB8", "v"),
    "M2N2": ("#C16E71", "D"),
    "TranAD": ("#78B6C8", "P"),
    "TimesNet": ("#D8ACC1", "X"),
    "FITS": ("#98AF1E", "h"),
    "AnomalyTransformer": ("#E5A79A", "*"),
}
def edge(color):
    return tuple(.66 * c for c in to_rgb(color))

def forest(ax):
    for pos, row in enumerate(df.itertuples()):
        color, marker = styles[row.Detector]
        ax.errorbar(row.CDU, pos,
            xerr=[[row.CDU-row.CDU_CI_low], [row.CDU_CI_high-row.CDU]],
            fmt=marker, color=color, ecolor=color, markeredgecolor=edge(color),
            markeredgewidth=.5, markersize=4.5, capsize=0,
            elinewidth=1.05, zorder=3)
    ax.set_yticks(np.arange(9), df.Detector.str.replace("_","-",regex=False), fontsize=7.5)
    ax.set_ylim(8.65, -.65)
    # Zero remains a labelled tick, not a vertical stroke through all markers.
    ax.spines["left"].set_visible(False)
    ax.spines["bottom"].set_color("#888888")
    ax.spines["bottom"].set_linewidth(.6)
    ax.set_xlim(-.010,.033)
    ax.set_xticks([-.01,0,.01,.02,.03],["-0.01","0","0.01","0.02","0.03"])
    ax.set_xlabel("CDU (bits)")
    ax.tick_params(axis="y",length=0)
def save(fig, name, close=True):
    fig.savefig(OUT / (name+".pdf"), bbox_inches="tight", pad_inches=.03)
    fig.savefig(OUT / (name+".png"), dpi=220, bbox_inches="tight", pad_inches=.03)
    if close:
        plt.close(fig)
fig, ax = plt.subplots(figsize=(3.35, 2.25))
y = np.arange(9)
forest(ax)
fig.tight_layout(pad=.35)
save(fig,"cdu_intervals")
fig, (scatter, intervals) = plt.subplots(1, 2, figsize=(7.05, 2.80),
    gridspec_kw={"width_ratios":[1.22, 1]})
fig.subplots_adjust(left=.075, right=.985, bottom=.29, top=.92, wspace=.62)
xmid, ymid = float(df.Raw_VUS.median()), float(df.CDU.median())
scatter.set(xlim=(.085,.465),ylim=(-.0035,.0135))
scatter.axvline(xmid, color="#b8b8b8", ls=(0,(4,4)), lw=.7, zorder=1)
scatter.axhline(ymid, color="#b8b8b8", ls=(0,(4,4)), lw=.7, zorder=1)
for row in df.itertuples():
    color, marker = styles[row.Detector]
    scatter.scatter(row.Raw_VUS, row.CDU, s=42, marker=marker,
        facecolor=color, edgecolor=edge(color), linewidth=.6, zorder=3)
scatter.set_xlabel("Raw VUS-PR (series-macro)")
scatter.set_ylabel("CDU (bits)")
scatter.set_xticks([.1,.2,.3,.4])
scatter.set_yticks([0,.005,.01],["0","0.005","0.010"])
scatter.set_title("(a) Accuracy and conditional utility",fontsize=8.5,loc="left")
rho = df.Raw_VUS.rank().corr(df.CDU.rank())
scatter.text(.03,.94,f"Spearman = {rho:.3f}",transform=scatter.transAxes,
    fontsize=7.5,va="top",color="#555555")
forest(intervals)
intervals.set_title("(b) 95% source-bootstrap intervals",fontsize=8.5,loc="left")
legend_handles = [Line2D([], [], linestyle="none", marker=marker,
    markerfacecolor=color, markeredgecolor=edge(color), markeredgewidth=.6,
    markersize=5.8, label=name.replace("_","-"))
    for name, (color, marker) in styles.items()]
fig.legend(handles=legend_handles, loc="lower center", bbox_to_anchor=(.5,.015),
    ncol=5, frameon=False, fontsize=7.5, handletextpad=.45, columnspacing=1.25,
    labelspacing=.75)
save(fig,"vus_cdu", close=False)
scatter.set_xlabel("原始 VUS-PR（序列宏平均）", fontfamily="Microsoft YaHei")
scatter.set_ylabel("CDU（比特）", fontfamily="Microsoft YaHei")
scatter.set_title("(a) 检测准确性与条件效用", fontsize=8.5, loc="left", fontfamily="Microsoft YaHei")
intervals.set_xlabel("CDU（比特）", fontfamily="Microsoft YaHei")
intervals.set_title("(b) 来源级 Bootstrap 95% 置信区间", fontsize=8.5, loc="left", fontfamily="Microsoft YaHei")
save(fig,"vus_cdu_zh")
df[["Detector","Raw_VUS","CDU","CDU_CI_low","CDU_CI_high","Raw_rank","CDU_rank"]].to_csv(
    OUT/"vus_cdu_data.csv",index=False)
fig, ax = plt.subplots(figsize=(3.35,1.72))
ax.set(xlim=(0,10),ylim=(0,5.7))
ax.axis("off")
def box(x,y,w,h,text):
    ax.add_patch(Rectangle((x,y),w,h,fc="#f1f5f8",ec=blue,lw=.8))
    ax.text(x+w/2,y+h/2,text,ha="center",va="center",fontsize=8)
def arrow(a,b):
    ax.annotate("",xy=b,xytext=a,arrowprops={"arrowstyle":"->","lw":.8,"color":ink})
ax.text(5,5.35,"Train: other sources | Test: source g",ha="center",fontsize=8)
box(.1,3.35,2.1,1.05,"Basis B")
box(.1,1.85,2.1,1.05,"Basis B\n+ score S")
box(3.1,3.35,2.5,1.05,"Basis\nprobe")
box(3.1,1.85,2.5,1.05,"Augmented\nprobe")
box(6.65,3.35,3.15,1.05,"Test loss\nL(B)")
box(6.65,1.85,3.15,1.05,"Test loss\nL(B,S)")
for yy in (3.875,2.375):
    arrow((2.2,yy),(3.1,yy))
    arrow((5.6,yy),(6.65,yy))
box(.1,.05,9.7,1.05,"CDU = L(B) - L(B,S)\nSource mean + source bootstrap")
ax.text(5,1.45,"Same test points, labels and weights",ha="center",fontsize=7)
save(fig,"protocol", close=False)
translated_labels = {
    "Train: other sources | Test: source g": "训练：其余来源 | 测试：来源 g",
    "Basis B": "统计基底 B",
    "Basis B\n+ score S": "统计基底 B\n+ 分数 S",
    "Basis\nprobe": "基底\n探针",
    "Augmented\nprobe": "增广\n探针",
    "Test loss\nL(B)": "测试损失\nL(B)",
    "Test loss\nL(B,S)": "测试损失\nL(B,S)",
    "CDU = L(B) - L(B,S)\nSource mean + source bootstrap":
        "CDU = L(B) - L(B,S)\n来源宏平均 + 来源级 Bootstrap",
    "Same test points, labels and weights": "相同测试点、标签与权重",
}
for label in ax.texts:
    if label.get_text() in translated_labels:
        label.set_text(translated_labels[label.get_text()])
        label.set_fontfamily("Microsoft YaHei")
save(fig,"protocol_zh")
(OUT/"figure_provenance.json").write_text(json.dumps({
    "input":str(SRC.relative_to(ROOT)),"sha256":hashlib.sha256(SRC.read_bytes()).hexdigest(),
    "n_detectors":9,"uncertainty":"10000-replicate paired source percentile bootstrap, without refitting",
    "graphics":["protocol.pdf (schematic)","cdu_intervals.pdf (observed estimates)",
                "vus_cdu.pdf (observed scatter and intervals)"],
    "quadrant_rule":"Pool medians, descriptive only; points on boundaries remain there",
    "quadrant_x":xmid,"quadrant_y":ymid,
    "model_styles":{name:{"color":color,"marker":marker}
                    for name,(color,marker) in styles.items()},
    "style_reference":"User-supplied palette images; categorical colors do not encode significance",
    "reference_lines":"Scatter: two pool medians only. Intervals: zero tick only, no vertical line.",
    "interval_style":"Uncapped 95% intervals, padded domain, categorical rows with equal spacing."
},indent=2),encoding="utf-8")
print("Rendered paper vector figures and PNG previews.")
