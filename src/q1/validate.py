"""执行第一问测试并将真实验证记录写入 outputs/q1/validation.json。"""

import hashlib
import json
from pathlib import Path
import platform
import unittest


def main():
    suite = unittest.defaultTestLoader.loadTestsFromName("src.q1.test_geometry")
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    here = Path(__file__).resolve().parent
    report = {"python_version": platform.python_version(), "executor": "AI 自动核验",
              "human_review": "pending", "tests_run": result.testsRun,
              "successful": result.wasSuccessful(),
              "failures": [str(t) for t, _ in result.failures],
              "errors": [str(t) for t, _ in result.errors],
              "skipped": [str(t) for t, _ in result.skipped],
              "seeds": [20260911, 421, 7301],
              "scope": "解析特例、400组固定种子对照、129条有效边；非模拟器验证",
              "code_sha256": {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                              for p in sorted(here.glob("*.py"))}}
    output = here.parents[1] / "outputs/q1/validation.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    raise SystemExit(0 if result.wasSuccessful() else 1)


if __name__ == "__main__":
    main()
