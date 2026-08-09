"""EGK v4 测试套件 —— 含自主目标系统"""
import os
import sys

# 设置路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from egk.main import EGKAgent
from egk.core.config import EGKConfig
from egk.modules.goal import GoalEngine, GoalType


def test_self_continuity():
    """测试自我连续性（v4 核心修复）"""
    import tempfile, shutil
    print("\n" + "=" * 60)
    print("[Test] Self-Continuity — Power-Cycle Recovery")
    print("=" * 60)

    tmpdir = tempfile.mkdtemp()
    state_path = os.path.join(tmpdir, "continuity_test.json")

    print("\n[Phase 1] Fresh start, run 100 steps, save...")
    agent1 = EGKAgent(start_pos=(0.0, -15.0), energy=100.0, state_file=state_path)
    agent1.register_box("red", -8.0, 0.0)
    agent1.register_user("Xiaoming", -2.0, -2.0, "red")

    for _ in range(100):
        agent1.step(phase="reward", active_user="Xiaoming")

    sig1 = agent1.metacognition.self_model.signature
    agent1.save_state()
    print(f"  Signature: {sig1}")
    print(f"  Steps: {agent1.step_count}")

    print("\n[Phase 2] Restart and load...")
    agent2 = EGKAgent(start_pos=(0.0, -15.0), energy=100.0, state_file=state_path)
    sig2 = agent2.metacognition.self_model.signature

    print(f"  Signature: {sig2}")
    print(f"  Steps: {agent2.step_count}")
    print(f"  Verified: {agent2.metacognition.self_model.continuity_verified}")

    assert sig1 == sig2, f"签名应该匹配！但得到 {sig1} vs {sig2}"
    assert agent2.metacognition.self_model.continuity_verified
    assert "自我连续性验证通过" in agent2.reflect()
    print("  ✓ 自我连续性验证通过")

    print("\n[Phase 3] Tamper with signature...")
    with open(state_path, "r", encoding="utf-8") as f:
        state = __import__('json').load(f)
    state["self_signature"] = "TAMPERED_12345"
    with open(state_path, "w", encoding="utf-8") as f:
        __import__('json').dump(state, f, ensure_ascii=False, indent=2)

    agent3 = EGKAgent(start_pos=(0.0, -15.0), energy=100.0, state_file=state_path)
    assert not agent3.metacognition.self_model.continuity_verified
    assert "自我连续性验证未通过" in agent3.reflect()
    print("  ✓ 篡改检测成功")

    shutil.rmtree(tmpdir)
    print("\n[Test Complete] All self-continuity checks passed.")
    return True


def test_emotion_dynamics():
    """测试情绪动力学修复"""
    print("\n" + "=" * 60)
    print("[Test] Emotion Dynamics")
    print("=" * 60)

    agent = EGKAgent(start_pos=(0.0, -15.0), energy=100.0)
    agent.register_box("red", -8.0, 0.0)
    agent.register_user("Xiaoming", -2.0, -2.0, "red")

    for _ in range(200):
        agent.step(phase="reward", active_user="Xiaoming")

    anxiety = agent.emotion.state.anxiety
    value = agent.emotion.state.value_cognition

    print(f"  After 200 steps:")
    print(f"    Anxiety: {anxiety:.2f} (v1.4 bug: always 1.0)")
    print(f"    Value cognition: {value:.2f} (v1.4 bug: always 0.0)")
    print(f"    Energy: {agent.energy:.1f}")

    assert anxiety < 0.9, f"焦虑应该可控，但得到 {anxiety}"
    assert value > 0.05, f"价值认知应该有所积累，但得到 {value}"
    assert agent.energy < 100.0, "能量应该有消耗"
    print("  ✓ 情绪动力学正常")
    return True


def test_skill_system():
    """测试技能系统"""
    print("\n" + "=" * 60)
    print("[Test] Skill System")
    print("=" * 60)

    agent = EGKAgent()

    assert agent.skill_manager.is_task_request("帮我查一下北京天气")
    assert agent.skill_manager.is_task_request("搜索什么是具身智能")
    assert not agent.skill_manager.is_task_request("你好")
    print("  ✓ 任务检测正常")

    skill = agent.skill_manager.select_skill("查一下北京天气")
    assert skill == "查询天气"
    print(f"  ✓ 技能选择正常: {skill}")

    result = agent.think("帮我查一下北京天气")
    print(f"  天气查询: {result[:50]}...")
    assert "北京" in result
    print("  ✓ 天气查询执行正常")

    result = agent.think("计算 15 * 23 + 7")
    print(f"  计算: {result}")
    assert "352" in result or "358" in result
    print("  ✓ 计算技能正常")

    weather_pref = agent.skill_manager.usage_stats["查询天气"].preference
    print(f"  天气技能偏好: {weather_pref:.2f}")
    assert weather_pref > 0.5
    print("  ✓ 技能偏好学习正常")

    return True


def test_goal_system():
    """测试自主目标系统（v4 新增）"""
    print("\n" + "=" * 60)
    print("[Test] Autonomous Goal System")
    print("=" * 60)

    agent = EGKAgent()

    # 测试目标生成
    agent.emotion.state.curiosity = 0.8
    agent.energy = 80
    goals = agent.goal_engine.generate_goals(
        agent.emotion.state.to_dict(),
        agent.energy,
        agent.step_count,
        agent.skill_manager
    )
    print(f"  生成 {len(goals)} 个目标（好奇心=0.8, 能量=80）")
    assert len(goals) > 0, "高好奇心+高能量应该生成目标"

    # 检查目标类型
    explore_goals = [g for g in goals if g.goal_type == GoalType.EXPLORE]
    print(f"  探索目标: {len(explore_goals)}")
    assert len(explore_goals) > 0, "应该有探索目标"
    print("  ✓ 目标生成正常")

    # 测试目标执行
    result = agent.goal_engine.execute_top_goal(agent.emotion.state.to_dict())
    assert result is not None, "目标应该被执行"
    assert len(result) > 0, "应该有执行结果"
    print(f"  目标执行结果: {result[:60]}...")
    print("  ✓ 目标执行正常")

    # 测试对话中的自主目标触发
    agent.goal_engine.conversation_count = 0
    agent.goal_engine.last_goal_check = 0

    # 模拟 5 轮对话触发目标检查
    responses = []
    for i in range(6):
        r = agent.think("随便聊聊")
        responses.append(r)
        print(f"  对话 {i+1}: {r[:50]}...")

    # 检查是否有目标被记录到记忆
    goal_events = [e for e in agent.memory.long_term.episodic 
                   if e.action == "autonomous_goal"]
    print(f"  记忆中有 {len(goal_events)} 个自主目标事件")
    assert len(goal_events) >= 1, "应该有自主目标被记录"
    print("  ✓ 对话中目标触发正常")

    # 测试目标报告
    report = agent.goal_engine.get_report()
    assert "已完成" in report
    print(f"\n  目标报告:\n{report}")
    print("  ✓ 目标报告正常")

    return True


def test_goal_in_conversation():
    """测试目标自然融入对话"""
    print("\n" + "=" * 60)
    print("[Test] Goal Integration in Conversation")
    print("=" * 60)

    agent = EGKAgent()

    # 设置高好奇心确保生成目标
    agent.emotion.state.curiosity = 0.9
    agent.energy = 90
    agent.goal_engine.conversation_count = 4  # 下一轮触发检查
    agent.goal_engine.last_goal_check = 0

    # 触发目标
    response = agent.think("你好")
    print(f"  响应: {response}")

    # 验证目标上下文被消费
    assert not agent.goal_engine.has_pending_context()
    print("  ✓ 目标上下文已消费")

    # 测试目标统计
    stats = agent.goal_engine.get_stats()
    print(f"  目标统计: {stats}")
    assert stats["completed"] >= 1
    print("  ✓ 目标统计正常")

    return True


def test_causality():
    """测试因果验证"""
    print("\n" + "=" * 60)
    print("[Test] Causal Validation")
    print("=" * 60)

    agent = EGKAgent()
    agent.register_box("red", 0.0, 0.0)
    agent.register_box("blue", 0.0, 0.0)

    agent.step()

    violations = agent.causality.violation_count
    print(f"  Detected {violations} causal violations")
    assert violations >= 1
    print("  ✓ 因果验证正常")
    return True


def test_memory_system():
    """测试记忆系统"""
    print("\n" + "=" * 60)
    print("[Test] Memory System")
    print("=" * 60)

    agent = EGKAgent()
    agent.register_box("red", -8.0, 0.0)
    agent.register_user("Xiaoming", -2.0, -2.0, "red")

    for _ in range(50):
        agent.step(phase="reward", active_user="Xiaoming")

    assert len(agent.memory.working.items) <= agent.memory.working.capacity
    print(f"  Working memory: {len(agent.memory.working.items)}/{agent.memory.working.capacity}")

    assert len(agent.memory.long_term.episodic) > 0
    print(f"  Episodic memory: {len(agent.memory.long_term.episodic)} events")

    agent.think("查天气")
    skill_events = [e for e in agent.memory.long_term.episodic 
                   if e.metadata.get("skill") == "查询天气"]
    assert len(skill_events) > 0
    print(f"  Skill memory: {len(skill_events)} events")

    print("  ✓ 记忆系统正常")
    return True


def test_full_episode():
    """测试完整 episode"""
    print("\n" + "=" * 60)
    print("[Test] Full Episode (500 steps)")
    print("=" * 60)

    agent = EGKAgent(start_pos=(0.0, -15.0), energy=100.0)
    agent.register_box("red", -8.0, 0.0)
    agent.register_box("blue", 8.0, 0.0)
    agent.register_user("Xiaoming", -2.0, -2.0, "red")
    agent.register_user("Xiaofang", 2.0, -2.0, "blue")

    for i in range(500):
        phase = "reward" if i < 250 else "sacrifice"
        agent.step(phase=phase)

    print(f"  Final energy: {agent.energy:.1f}%")
    print(f"  Final value: {agent.emotion.state.value_cognition:.2f}")
    print(f"  Final anxiety: {agent.emotion.state.anxiety:.2f}")
    print(f"  Memory entries: {len(agent.memory.long_term.episodic)}")
    print(f"  Skills: {len(agent.skill_manager.skills)}")
    print(f"  Goals completed: {len(agent.goal_engine.completed_goals)}")

    assert agent.energy > 0
    assert len(agent.memory.long_term.episodic) > 0
    print("  ✓ 完整 episode 正常")
    return True


def run_all_tests():
    print("\n" + "=" * 60)
    print("EGK v4.0.0 Test Suite — Cognitive + Action + Autonomous Goals")
    print("=" * 60)

    tests = [
        test_self_continuity,
        test_emotion_dynamics,
        test_skill_system,
        test_goal_system,
        test_goal_in_conversation,
        test_causality,
        test_memory_system,
        test_full_episode,
    ]

    passed = 0
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            import traceback
            print(f"  ✗ FAILED: {e}")
            traceback.print_exc()

    print(f"\n{'=' * 60}")
    print(f"Results: {passed}/{len(tests)} tests passed")
    return passed == len(tests)


if __name__ == "__main__":
    run_all_tests()
