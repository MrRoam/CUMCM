"""运行第一问检查及原共有几何回归，保存原始输出和源码散列。"""
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import subprocess
import sys
from datetime import datetime, timezone

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))
from experiments.b_q1.run_examples import source_hashes


def main():
    suites = []
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    for module in ("experiments.b_q1.test_solver", "experiments.b_overnight.test_q2_geometry"):
        args = [sys.executable, "-m", "unittest", module, "-v"]
        run = subprocess.run(args, cwd=REPO, env=env, capture_output=True, text=True, encoding="utf-8")
        transcript = run.stdout + run.stderr
        count = re.search(r"Ran (\d+) tests?", transcript)
        suites.append({"module": module, "command": "py -3.13 -m unittest " + module + " -v",
                       "returncode": run.returncode, "test_count": int(count[1]) if count else 0,
                       "transcript": transcript})
    hashes = source_hashes()
    legacy_test = REPO / "experiments/b_overnight/test_q2_geometry.py"
    hashes[legacy_test.relative_to(REPO).as_posix()] = hashlib.sha256(legacy_test.read_bytes()).hexdigest()
    artifact_checks = {}
    try:
        examples_path = HERE / "results/examples.json"
        examples = json.loads(examples_path.read_text(encoding="utf-8"))
        artifact_checks["example_source_hashes_current"] = examples["source_sha256"] == source_hashes()
        artifact_checks["example_inputs_unchanged"] = all(
            row["input_sha256"] == hashlib.sha256((HERE / "examples" / (name + ".json")).read_bytes()).hexdigest()
            for name, row in examples["examples"].items())
        artifact_checks["all_examples_physically_valid"] = all(row["physical_check"]["all_valid"] for row in examples["examples"].values())
        figures = json.loads((HERE / "results/figures_manifest.json").read_text(encoding="utf-8"))
        artifact_checks["figure_input_current"] = figures["input_sha256"] == hashlib.sha256(examples_path.read_bytes()).hexdigest()
        artifact_checks["figure_script_current"] = figures["script_sha256"] == hashlib.sha256((HERE / "plot_results.py").read_bytes()).hexdigest()
        artifact_checks["figure_files_unchanged"] = all(
            hashlib.sha256((HERE / name).read_bytes()).hexdigest() == digest for name, digest in figures["files_sha256"].items())
    except (OSError, ValueError, KeyError) as exc:
        artifact_checks["artifact_read_error"] = str(exc)
    passed = (all(s["returncode"] == 0 and s["test_count"] > 0 for s in suites)
              and bool(artifact_checks) and all(value is True for value in artifact_checks.values()))
    report = {"checked_at_utc": datetime.now(timezone.utc).isoformat(), "python": platform.python_version(),
              "all_passed": passed, "test_count": sum(s["test_count"] for s in suites),
              "transformation_seed": 20260911, "source_sha256": hashes, "suites": suites,
              "artifact_checks": artifact_checks}
    out = HERE / "results"
    out.mkdir(exist_ok=True)
    (out / "validation.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lines = ["# 第一问验证记录", "", f"UTC时间：{report['checked_at_utc']}；Python：{report['python']}。",
             "", f"结果：{'通过' if passed else '未通过'}；共 {report['test_count']} 项测试。",
             "", "包含第一问完整输入链、解析算例、变换不变性、追加观测、必要边界及旧共有几何回归。",
             "随机旋转/平移种子为20260911，每个解析案例12次；这是几何性质检查，不是失败率估计。",
             "源码散列与原始运行输出见同目录 validation.json；本记录由脚本生成。",
             "执行和核验由AI完成，团队人工审阅状态尚未登记。", ""]
    lines += ["## 生成物一致性", ""]
    lines += [f"- {name}: {value}" for name, value in artifact_checks.items()]
    lines += [""]
    for suite in suites:
        lines += ["## " + suite["module"], "", "```text", suite["transcript"].rstrip(), "```", ""]
    (out / "VALIDATION.md").write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps({"all_passed": passed, "test_count": report["test_count"]}))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
