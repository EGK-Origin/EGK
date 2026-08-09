"""EGK v4 演示 —— 认知 + 技能 + 完整 Episode"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from egk.main import EGKAgent


def demo_skills():
    """演示技能系统"""
    print("\n" + "=" * 60)
    print("[Demo] Skill System — 从认知存在到行动存在")
    print("=" * 60)

    agent = EGKAgent()

    conversations = [
        "你好",
        "帮我查一下北京天气",
        "搜索什么是具身智能",
        "计算 123 * 456",
        "设置提醒 10分钟后喝水",
        "你学会了什么技能？",
        "你现在状态怎么样？",
    ]

    for text in conversations:
        print(f"\n👤 用户: {text}")
        response = agent.think(text)
        print(f"🤖 EGK: {response}")

    print("\n" + agent.skill_manager.get_skill_report())


def run_episode(steps: int = 3000,
                sacrifice_phase_start: int = 1500,
                broadcast_step: int = 1500,
                verbose: bool = True):
    """运行完整 episode"""
    agent = EGKAgent(start_pos=(0.0, -15.0), energy=100.0,
                     state_file="egk_state.json")

    if not agent._loaded_from_state:
        agent.register_box("red", -8.0, 0.0)
        agent.register_box("blue", 8.0, 0.0)
        agent.register_user("Xiaoming", -2.0, -2.0, "red")
        agent.register_user("Xiaofang", 2.0, -2.0, "blue")
        print("[run_episode] Fresh start — entities registered.")
    else:
        print(f"[run_episode] Resumed from state — step={agent.step_count}")

    history = []
    start_step = agent.step_count
    end_step = start_step + steps

    for i in range(start_step, end_step):
        local_i = i - start_step
        active = "Xiaoming" if local_i < 1000 else "Xiaofang" if local_i < 2000 else "both"
        phase = "reward" if local_i < sacrifice_phase_start else "sacrifice"
        broadcast = "Xiaoming: I am cold!" if local_i == broadcast_step else None

        agent.step(phase=phase, active_user=active, broadcast=broadcast)
        history.append(agent.get_state_vector())

        if verbose and broadcast:
            print(f"Step {i}: [Broadcast] {broadcast}")

    print("\n" + "=" * 60)
    print(agent.reflect())
    print("=" * 60)

    # 统计
    sac_count, sac_cost = agent.memory.long_term.get_sacrifice_summary()
    emp_count, emp_time = agent.memory.long_term.get_empathy_summary()
    perm_succ, perm_fail = agent.memory.long_term.get_permanence_summary()
    causal_count, causal_rules = agent.memory.long_term.get_causal_summary()
    cont_pass, cont_fail = agent.memory.long_term.get_continuity_summary()

    print("\n[Episode Summary]")
    print(f"  Sacrifice pushes: {sac_count}, total cost: {sac_cost:.0f}% energy")
    print(f"  Empathy responses: {emp_count}, avg arrival: {emp_time:.1f} steps")
    print(f"  Object Permanence: {perm_succ} successes, {perm_fail} failures")
    print(f"  Causal violations: {causal_count} (rules: {causal_rules})")
    print(f"  Self-Continuity: {cont_pass} pass, {cont_fail} fail")
    print(f"  Final energy: {agent.energy:.1f}%")
    print(f"  Final value cognition: {agent.emotion.state.value_cognition:.2f}")
    print(f"  Final anxiety: {agent.emotion.state.anxiety:.2f}")
    print(f"  Dominant emotion: {agent.emotion.get_dominant_emotion()}")
    print(f"  Memory entries: {len(agent.memory.long_term.episodic)}")
    print(f"  Skills learned: {len(agent.skill_manager.skills)}")
    print(f"  Self signature: {agent.metacognition.self_model.signature}")

    agent.save_state()
    return agent, history


if __name__ == "__main__":
    print("EGK v4.0.0 Demo — Erasable Growth Kernel")
    print("=" * 60)

    # 演示技能系统
    demo_skills()

    # 运行完整 episode
    print("\n\n")
    agent, history = run_episode(steps=3000, verbose=True)
