"""PR #9 的可复现交接核验：单元检查、历史账本、输出边界和完整本地运行。"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import statistics
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / 'probability_patrol'))
import runner


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', required=True)
    args = parser.parse_args()
    out = runner.new_run(args.out)
    tests = []
    env = dict(os.environ, PYTHONIOENCODING='utf-8')
    for path in sorted(HERE.glob('*/test_*.py')):
        proc = subprocess.run([sys.executable, str(path)], cwd=ROOT, env=env,
                              capture_output=True, text=True, encoding='utf-8', timeout=240)
        log = proc.stdout + proc.stderr
        match = re.search(r'Ran (\d+) tests?', log)
        row = dict(file=path.relative_to(ROOT).as_posix(), exit_code=proc.returncode,
                   tests=int(match.group(1)) if match else None, output=log)
        tests.append(row)
        runner.dump(out / 'tests.json', tests)
        print(row['file'], row['exit_code'], row['tests'], flush=True)
    assert all(t['exit_code'] == 0 and t['tests'] for t in tests), '主测试失败'

    sys.path.insert(0, str(HERE / 'adaptive_second'))
    from diagnose import replay
    folder = HERE / 'adaptive_second/runs/confirm'
    cases = runner.read_cases(folder / 'cases.json')
    counts = 0
    values = {m: [] for m in ('fixed', 'position', 'joint', 'baseline')}
    for case in cases:
        for mode in values:
            counts += replay(folder / case.name / mode, case)
            result = json.loads((folder / case.name / mode / 'result.json').read_text(encoding='utf-8'))
            values[mode].append(result['total_s'] / 60)
    replayed = dict(cases=len(cases), runs=sum(map(len, values.values())), actions=counts,
                    means_min={m: statistics.mean(v) for m, v in values.items()})
    runner.dump(out / 'historical_replay.json', replayed)

    # 在启动任何模拟前确认拒绝旧批次、源码目录及越界路径。
    rejected = []
    for target in (HERE / 'runs/forbidden', ROOT / 'outputs/experiments/b_q3',
                   ROOT / 'outputs/experiments/b_q3/../../forbidden', out):
        try:
            runner.new_run(target)
        except (ValueError, FileExistsError):
            rejected.append(str(target.relative_to(ROOT)))
        else:
            raise AssertionError('非法输出被接受')
    # 重复批次不能因为参数相同就跳过执行。
    assert len(rejected) == 4
    runner.dump(out / 'path_checks.json', dict(rejected=rejected))

    # 预定四种布局，每种一个 smooth 误差案例；不因结果筛选案例。
    smoke = [runner.make_cases('development')[i] for i in (0, 3, 6, 9)]
    runner.dump(out / 'smoke_cases.json', [c.to_dict() for c in smoke])
    commands = []
    for policy in ('baseline', 'patrol'):
        target = out / policy
        command = [sys.executable, str(HERE / 'probability_patrol/runner.py'),
                   '--policy', policy, '--cases', str(out / 'smoke_cases.json'),
                   '--out', str(target), '--workers', '1', '--wall-limit-s', '120']
        proc = subprocess.run(command, cwd=ROOT, env=env, capture_output=True,
                              text=True, encoding='utf-8', timeout=600)
        runner.dump(out / (policy + '_command.json'), dict(
            command=['python'] + [str(Path(x).relative_to(ROOT)) if Path(x).is_absolute() and Path(x).is_relative_to(ROOT) else x for x in command[1:]],
            exit_code=proc.returncode, output=proc.stdout+proc.stderr))
        assert proc.returncode == 0, proc.stderr
        for case in smoke:
            replay(target / 'cases' / case.name, case)
        commands.append(policy)
        print('完整运行通过:', policy, flush=True)
    record = dict(unit_tests=sum(t['tests'] for t in tests), historical_replay=replayed,
                  output_rejections=len(rejected), fresh_runs=len(smoke)*len(commands),
                  scope='AI自动核验；自建环境，不代表官方成绩或团队人工核验')
    runner.dump(out / 'validation.json', record)
    runner.finish_run(out, len(smoke)*len(commands))
    print(json.dumps(record, ensure_ascii=False), flush=True)


if __name__ == '__main__':
    main()
