"""在仓库根目录运行 python -m src.q1 --demo。"""

import argparse
import hashlib
import json
from pathlib import Path
import platform
import sys

from .examples import demo_observations
from .geometry import analyze, bearing_halfplanes


def main():
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="B 题第一问：方法 A")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--demo", action="store_true", help="运行明确标注的人工构造例")
    group.add_argument("--input", type=Path, help="仓库相对 JSON 路径；含 observations 数组")
    parser.add_argument("--output", type=Path, default=Path("outputs/q1/result.json"))
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    if args.output.is_absolute():
        parser.error("输出必须使用仓库相对路径")
    output = (root / args.output).resolve()
    if not output.is_relative_to(root / "outputs"):
        parser.error("结果只能写入 outputs/，禁止覆盖官方输入")
    if args.demo:
        cases = demo_observations()
        source = "人工构造验证例；非官方参考答案、非模拟器结果"
    else:
        if args.input.is_absolute():
            parser.error("输入必须使用仓库相对路径")
        path = (root / args.input).resolve()
        if not path.is_relative_to(root):
            parser.error("输入必须位于仓库内")
        raw = path.read_bytes()
        data = json.loads(raw.decode("utf-8-sig"), parse_float=str)
        cases = {"input": data["observations"]}
        source = {"path": args.input.as_posix(), "sha256": hashlib.sha256(raw).hexdigest()}
        if output == path:
            parser.error("输出不能覆盖输入")
    report = {"schema_version": 1, "python_version": platform.python_version(),
              "source": source, "angle_error_deg": 1, "coordinate_unit": "m",
              "model": "bearing_wedges_only", "human_review": "pending",
              "numeric_contract": "binary64 三角函数近似；随后整数/有理数精确谓词；JSON 浮点字段仅用于显示",
              "code_sha256": {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                              for p in sorted(Path(__file__).parent.glob("*.py"))},
              "cases": {}}
    for name, observations in cases.items():
        report["cases"][name] = {"observations": observations,
                                 "result": analyze(bearing_halfplanes(observations))}
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(args.output.as_posix())
    for name, case in report["cases"].items():
        result = case["result"]
        print(name, result["status"], "D=", result["diameter_m"],
              "diameter_circle_covers=", result["diameter_circle_covers"])


if __name__ == "__main__":
    main()
