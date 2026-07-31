"""EGK_Core unit tests.

Run with: python -m pytest test_egk.py -v
Or:       python test_egk.py
"""

import sys
import unittest

sys.path.insert(0, "..")
from EGK_Core import EGKAgent, MemoryBuffer, Entity, Box, User


class TestMemoryBuffer(unittest.TestCase):
    def test_push_and_query(self):
        mb = MemoryBuffer(max_len=10)
        mb.push({"step": 1, "emotion_tag": "reward", "energy_cost": 5.0})
        mb.push({"step": 2, "emotion_tag": "sacrifice", "energy_cost": 10.0})
        self.assertEqual(len(mb.query("reward", 10)), 1)
        self.assertEqual(len(mb.query("sacrifice", 10)), 1)

    def test_sacrifice_summary(self):
        mb = MemoryBuffer()
        mb.push({"step": 1, "emotion_tag": "sacrifice", "energy_cost": 10.0})
        mb.push({"step": 2, "emotion_tag": "sacrifice", "energy_cost": 10.0})
        count, cost = mb.get_sacrifice_summary()
        self.assertEqual(count, 2)
        self.assertEqual(cost, 20.0)

    def test_empathy_summary_with_none(self):
        mb = MemoryBuffer()
        mb.push({"step": 1, "emotion_tag": "empathy", "response_time": None})
        mb.push({"step": 2, "emotion_tag": "empathy", "response_time": 5.0})
        count, avg = mb.get_empathy_summary()
        self.assertEqual(count, 2)
        self.assertEqual(avg, 5.0)


class TestEnergyFloor(unittest.TestCase):
    """Fix #1: energy must never drop below 0."""

    def test_energy_never_negative(self):
        agent = EGKAgent(energy=50.0)
        agent.register_box("red", -8.0, 0.0)
        agent.register_user("test", -2.0, -2.0, "red")

        for _ in range(100):
            agent.step(phase="sacrifice")
            self.assertGreaterEqual(agent.energy, 0.0)

    def test_apply_feedback_floor(self):
        agent = EGKAgent(energy=5.0)
        agent.register_box("red", 0.0, 0.0)
        agent.boxes["red"].in_zone = True
        agent.boxes["red"].prev_in_zone = False
        agent.apply_feedback({
            "box_states": {"red": {"just_entered": True}},
            "user_states": {}
        }, phase="sacrifice")
        self.assertGreaterEqual(agent.energy, 0.0)


class TestRechargeGuard(unittest.TestCase):
    """Fix #2: auto-recharge prevents deadlock."""

    def test_recharge_triggered(self):
        agent = EGKAgent(energy=100.0)
        agent.energy = 5.0  # manually set low after init
        agent.step()
        self.assertGreater(agent.energy, 5.0)
        recharge_records = [r for r in agent.memory.buffer if r.get("action") == "recharge"]
        self.assertEqual(len(recharge_records), 1)

    def test_recharge_skips_round(self):
        agent = EGKAgent(energy=5.0)
        before = agent.step_count
        agent.step()
        self.assertEqual(agent.step_count, before + 1)
        self.assertTrue(any(r.get("action") == "recharge" for r in agent.memory.buffer))


class TestActionCounter(unittest.TestCase):
    """Fix #3: accurate action statistics via Counter."""

    def test_counter_tracks_actions(self):
        agent = EGKAgent()
        agent.register_box("red", -8.0, 0.0)
        for _ in range(10):
            agent.step()
        summary = agent.get_action_summary()
        total = sum(summary.values())
        self.assertEqual(total, 10)

    def test_counter_is_dict(self):
        agent = EGKAgent()
        agent.step()
        summary = agent.get_action_summary()
        self.assertIsInstance(summary, dict)


class TestOptimismDrift(unittest.TestCase):
    """Fix #4: personality drift judgment at optimism == 0."""

    def test_pessimistic_tendency(self):
        agent = EGKAgent()
        agent.optimism = 0.0
        reflection = agent.reflect()
        self.assertIn("Pessimistic tendency", reflection)

    def test_optimistic_tendency(self):
        agent = EGKAgent()
        agent.optimism = 0.8
        reflection = agent.reflect()
        self.assertIn("Optimistic tendency", reflection)

    def test_neutral_stable(self):
        agent = EGKAgent()
        agent.optimism = 0.5
        reflection = agent.reflect()
        self.assertIn("Neutral stable", reflection)

    def test_slightly_pessimistic(self):
        agent = EGKAgent()
        agent.optimism = 0.3
        reflection = agent.reflect()
        self.assertIn("Slightly pessimistic", reflection)


class TestStage9Integration(unittest.TestCase):
    """Full Stage 9 altruism reproduction."""

    def test_stage9_completes(self):
        from EGK_Core import run_episode
        agent, history = run_episode(steps=500, verbose=False)
        self.assertEqual(len(history), 500)
        self.assertGreaterEqual(agent.energy, 0.0)

    def test_stage9_has_sacrifices(self):
        from EGK_Core import run_episode
        agent, history = run_episode(steps=2000, verbose=False)
        sac_count, _ = agent.memory.get_sacrifice_summary()
        self.assertGreater(sac_count, 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
