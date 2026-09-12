"""从保存的第一问输入/结果生成两幅图；兼容现有Python3.7制图环境。"""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import platform
from datetime import datetime, timezone

HERE = Path(__file__).resolve().parent
os.environ.setdefault("MPLCONFIGDIR", str(HERE / ".cache/matplotlib"))
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, Polygon
from matplotlib.font_manager import FontProperties


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--font", type=Path, default=Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts/msyh.ttc")
    args = parser.parse_args()
    if not args.font.is_file():
        parser.error("请用 --font 指定可用的中文字体文件")
    font = FontProperties(fname=str(args.font))
    plt.rcParams.update({"font.size": 10, "axes.unicode_minus": False, "svg.fonttype": "path", "savefig.dpi": 180})
    source = HERE / "results/examples.json"
    data = json.loads(source.read_text(encoding="utf-8"))["examples"]
    folder = HERE / "figures"
    folder.mkdir(exist_ok=True)
    saved = []
    blue, orange, green, ink = "#2866A3", "#CC7136", "#25816B", "#273442"

    def setup(ax, title, limits):
        ax.set_title(title, fontproperties=font, pad=12)
        ax.set_aspect("equal", adjustable="box")
        ax.set_xlim(*limits[0]); ax.set_ylim(*limits[1])
        ax.set_xlabel("向东距离 / 米", fontproperties=font)
        ax.set_ylabel("向北距离 / 米", fontproperties=font)
        ax.grid(True, color="#E6EAF0", linewidth=0.6)

    def label(ax, x, y, text, **kwargs):
        ax.text(x, y, text, fontproperties=font, **kwargs)

    def save(fig, name):
        fig.tight_layout(rect=(0, 0.065, 1, 1))
        for ext in ("png", "svg"):
            path = folder / (name + "." + ext)
            fig.savefig(str(path), facecolor="white")
            saved.append(path)
        plt.close(fig)

    crossing = data["crossing"]
    poly = crossing["result"]["vertices_m"]
    observations = crossing["input"]["observations"]
    fig, axes = plt.subplots(1, 2, figsize=(12, 5.6))
    for ax, limits, title in zip(axes, [((-550, 70), (-550, 70)), ((-13, 13), (-13, 13))],
                                 ["两次观测形成前向误差扇形", "交集放大：顶点与最远端点"]):
        setup(ax, title, limits)
        for i, row in enumerate(observations):
            p, theta = row["position_m"], row["bearing_deg"]
            points = [p] + [[p[0]+650*math.cos(math.radians(theta+a)), p[1]+650*math.sin(math.radians(theta+a))] for a in (-1, 1)]
            ax.add_patch(Polygon(points, color=(blue if i == 0 else orange), alpha=0.10))
            for a in (-1, 0, 1):
                end = [p[0]+650*math.cos(math.radians(theta+a)), p[1]+650*math.sin(math.radians(theta+a))]
                ax.plot([p[0], end[0]], [p[1], end[1]], color=(blue if i == 0 else orange),
                        linestyle="--" if a else "-", linewidth=0.85)
            if ax is axes[0]:
                ax.scatter([p[0]], [p[1]], color=ink, s=24)
                label(ax, p[0]+(12 if i == 0 else -12), p[1]-30,
                      "检测点{}".format(i+1), ha="left" if i == 0 else "right")
        ax.add_patch(Polygon(poly, facecolor=green, edgecolor=green, alpha=0.40))
        a, b = crossing["result"]["diameter_endpoints_m"]
        ax.plot([a[0], b[0]], [a[1], b[1]], color=ink, linewidth=2)
        ax.scatter([p[0] for p in poly], [p[1] for p in poly], color=ink, s=16)
    label(axes[1], -11.5, 10.7, "直径 = {:.6f} 米".format(crossing["result"]["diameter_m"]), color=ink)
    fig.text(0.5, 0.025, "自建算例；每次示向度允许误差为 ±1°。绘图显示范围仅用于展示，计算未用边框截断。", ha="center", fontproperties=font)
    save(fig, "intersection_and_diameter")

    triangle = data["triangle"]
    poly = triangle["result"]["vertices_m"]
    center = triangle["input"]["source_m"]
    diameter = triangle["result"]["diameter_m"]
    radius = triangle["input"]["minimum_cover_radius_m"]
    assert abs(diameter-40) < 1e-7 and abs(radius-40/math.sqrt(3)) < 1e-12
    fig, axes = plt.subplots(1, 2, figsize=(12, 5.6))
    for ax, title in zip(axes, ["最长边中点作圆心：不能覆盖", "最小覆盖圆：半径仍然大于20米"]):
        setup(ax, title, ((-8, 48), (-24, 43)))
        ax.add_patch(Polygon(poly, facecolor=blue, edgecolor=blue, alpha=0.18))
        ax.scatter([p[0] for p in poly], [p[1] for p in poly], color=ink, s=23)
    axes[0].add_patch(Circle((20, 0), 20, fill=False, edgecolor=orange, linewidth=2))
    axes[0].plot([0, 40], [0, 0], color=ink, linewidth=2)
    label(axes[0], 20, -17, "区域直径 = 40 米\n圆半径 = 20 米", ha="center")
    label(axes[0], 20, 37, "顶点在圆外", ha="center", color=orange)
    axes[1].add_patch(Circle(center, radius, fill=False, edgecolor=green, linewidth=2))
    axes[1].scatter([center[0]], [center[1]], color=green, s=25)
    label(axes[1], 20, -18, "最小覆盖半径 = {:.6f} 米".format(radius), ha="center", color=green)
    fig.text(0.5, 0.025, "正文证明：无论圆心放在哪里，覆盖半径都至少为 40/√3 米。该三角形可由三次合法测向产生。", ha="center", fontproperties=font)
    save(fig, "diameter_circle_counterexample")
    manifest = {"generated_at_utc": datetime.now(timezone.utc).isoformat(), "python": platform.python_version(),
                "matplotlib": matplotlib.__version__, "input_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
                "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                "files_sha256": {p.relative_to(HERE).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in saved}}
    (HERE / "results/figures_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    print("Generated {} figure files".format(len(saved)))


if __name__ == "__main__":
    main()
