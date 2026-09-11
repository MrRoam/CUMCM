"""直接调用自建环境的最小例子；从仓库根目录执行本文件。"""
import json

from simulation import LocalEnvironment, Scenario, Source


def main():
    # 仅演示接口；1个源不是题面要求的10—16源完整测试。
    case = Scenario("one_source_demo", 20260911, "manual", "zero",
                    (Source(channel=1, position=(100.0, 0.0), radius=1000.0),))
    actions = [
        dict(kind="measure", position=(0.0, 0.0), channel=1),
        dict(kind="clear", position=(80.0, 0.0), channel=1),
        dict(kind="measure", position=(80.0, 0.0), channel=1),
    ]
    env = LocalEnvironment(case)
    feedback = [env.act(action) for action in actions]
    assert feedback[0]["svd_deg"] == 0.0
    assert feedback[1]["clear_result"] == "success"
    assert feedback[2]["measure_result"] == "no_signal"
    assert env.virtual_time_s == 31.0
    replay = LocalEnvironment(Scenario.from_dict(case.to_dict()))
    assert [replay.act(action) for action in actions] == feedback
    print(json.dumps(dict(case=case.to_dict(), actions=actions,
                          feedback=feedback, deterministic_replay=True),
                     ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
