"""第二问面积平均选点策略命令行入口。"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import platform
import sys

from .strategy import (
    CONFIG_PATH,
    evaluate_point,
    load_config,
    local_selected_point,
    recommend_second_point,
    search_area_mean,
)


ROOT = Path(__file__).resolve().parents[2]


def code_hashes():
    here = Path(__file__).resolve().parent
    return {
        path.name: hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(here.iterdir())
        if path.suffix in {".py", ".json", ".md"}
    }


def safe_output(relative_path: Path) -> Path:
    if relative_path.is_absolute():
        raise ValueError("输出必须使用仓库相对路径")
    output = (ROOT / relative_path).resolve()
    if not output.is_relative_to(ROOT / "outputs"):
        raise ValueError("结果只能写入outputs目录")
    return output


def main():
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="B题第二问：面积均匀平均半径选点")
    subparsers = parser.add_subparsers(dest="command", required=True)

    recommend = subparsers.add_parser("recommend", help="把标准局部选点变换到全局坐标")
    recommend.add_argument("--first-x", type=float, default=0.0)
    recommend.add_argument("--first-y", type=float, default=0.0)
    recommend.add_argument("--bearing-deg", type=float, default=0.0)
    recommend.add_argument("--side", choices=("left", "right"), default="left")

    verify = subparsers.add_parser("verify-selected", help="在面积均匀加密网格上复核采纳点")
    verify.add_argument(
        "--output",
        type=Path,
        default=Path("outputs/q2/adopted_average_strategy.json"),
    )
    verify.add_argument("--radial-count", type=int, default=320)
    verify.add_argument("--angle-count", type=int, default=17)
    verify.add_argument("--error-count", type=int, default=17)

    search = subparsers.add_parser("search", help="复算当前粗网格加边界细化搜索")
    search.add_argument(
        "--output",
        type=Path,
        default=Path("outputs/q2/adopted_average_strategy_search.json"),
    )
    args = parser.parse_args()

    if args.command == "recommend":
        point = recommend_second_point(
            (args.first_x, args.first_y), args.bearing_deg, args.side
        )
        print(
            json.dumps(
                {
                    "second_point_m": point.tolist(),
                    "side": args.side,
                    "applicability": "仅适用于strategy_config.json所述未裁剪标准场景",
                },
                ensure_ascii=False,
            )
        )
        return

    output = safe_output(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    if args.command == "verify-selected":
        result = evaluate_point(
            local_selected_point(),
            args.radial_count,
            args.angle_count,
            args.error_count,
        )
        action = "固定采纳点的独立加密网格复核"
    else:
        result = search_area_mean()
        action = "确定性粗网格加局部边界细化复算"
    report = {
        "schema_version": 1,
        "status": "当前采用方案的AI自动复核；非官方成绩、非连续全局最优证明",
        "action": action,
        "model_config": load_config(),
        "result": result,
        "python_version": platform.python_version(),
        "numpy_required": True,
        "human_review": "pending",
        "code_sha256": code_hashes(),
        "config_sha256": hashlib.sha256(CONFIG_PATH.read_bytes()).hexdigest(),
    }
    output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(args.output.as_posix())
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
