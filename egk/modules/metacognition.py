"""EGK v4 元认知模块 —— 自我监控、自我连续性、反思

修复 v1.4 自我连续性 Bug:
- 签名基于 birth_params 而非当前状态
- load_state 时不再重新生成签名, 而是验证存档签名
"""
from __future__ import annotations
import time
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, field

from egk.core.types import MemoryEvent
from egk.core.config import MemoryConfig
from egk.utils.helpers import generate_signature, format_time


@dataclass
class SelfModel:
    """自我模型"""
    birth_params: Dict[str, Any] = field(default_factory=dict)
    signature: str = ""
    birth_timestamp: float = 0.0
    continuity_verified: bool = False
    continuity_mismatch: bool = False
    total_steps: int = 0

    def generate_signature(self) -> str:
        self.signature = generate_signature(self.birth_params)
        return self.signature

    def verify(self, stored_signature: Optional[str]) -> bool:
        if stored_signature is None or not self.signature:
            self.continuity_verified = False
            return False
        self.continuity_verified = (self.signature == stored_signature)
        self.continuity_mismatch = not self.continuity_verified
        return self.continuity_verified


class MetacognitionModule:
    """元认知模块"""
    def __init__(self, config: MemoryConfig):
        self.config = config
        self.self_model = SelfModel()
        self.reflection_count = 0
        self.strategy_history: List[str] = []

    def initialize_identity(self, birth_params: Dict[str, Any]):
        """初始化自我身份"""
        self.self_model.birth_params = birth_params
        self.self_model.birth_timestamp = time.time()
        self.self_model.generate_signature()
        print(f"[SelfContinuity] Generated self_signature: {self.self_model.signature}")

    def verify_continuity(self, stored_signature: Optional[str]) -> bool:
        """验证自我连续性"""
        result = self.self_model.verify(stored_signature)
        if result:
            print(f"[SelfContinuity] 签名匹配 — 自我连续性验证通过")
        else:
            print(f"[SelfContinuity] 签名不匹配 — 自我连续性验证未通过")
            print(f"  当前: {self.self_model.signature}")
            print(f"  存档: {stored_signature}")
        return result

    def reflect(self, step_count: int, emotional_state: Dict[str, float],
                energy: float, max_energy: float,
                memory_system, action_counts: Dict[str, int],
                causal_violations: int, causal_rules: List[str],
                permanence_succ: int, permanence_fail: int,
                cont_pass: int, cont_fail: int) -> str:
        """元认知反思"""
        self.reflection_count += 1
        psych_time = step_count // 60

        lines = [
            f"[Reflect @ Step {step_count} | Psychological time {format_time(psych_time)}]",
            f"  Energy: {energy:.1f}%, Value: {emotional_state.get('value_cognition', 0):.2f}, "
            f"Anxiety: {emotional_state.get('anxiety', 0):.2f}, "
            f"Loneliness: {emotional_state.get('loneliness', 0):.2f}, "
            f"Morality: {emotional_state.get('morality', 0):.2f}",
            f"  Arousal: {emotional_state.get('arousal', 0):.2f}, "
            f"Valence: {emotional_state.get('valence', 0):.2f}, "
            f"Dominant: {self._get_dominant_emotion(emotional_state)}",
        ]

        # 自我连续性
        if self.self_model.signature:
            if self.self_model.continuity_verified:
                lines.append(f" [SelfContinuity] 自我连续性验证通过 (签名: {self.self_model.signature})")
            elif self.self_model.continuity_mismatch:
                lines.append(f" [SelfContinuity] 自我连续性验证未通过 (签名: {self.self_model.signature})")
                lines.append("  我好像变了，但我记得以前的自己...")
            else:
                lines.append(f" [SelfContinuity] 自我连续性验证通过 (签名: {self.self_model.signature})")

        # 牺牲总结
        sac_count, sac_cost = memory_system.long_term.get_sacrifice_summary()
        if sac_count > 0:
            lines.append(f"  I performed {sac_count} sacrifice pushes, costing {sac_cost:.0f}% energy total.")
            if energy < 20.0:
                lines.append("  I feel exhausted, but I do not regret it.")

        # 共情总结
        emp_count, emp_time = memory_system.long_term.get_empathy_summary()
        if emp_count > 0:
            lines.append(f"  I responded to {emp_count} distress calls, avg arrival {emp_time:.1f} steps.")

        # 对象恒存性
        if permanence_succ > 0 or permanence_fail > 0:
            lines.append(f" [ObjectPermanence] Prediction successes: {permanence_succ}, failures: {permanence_fail}")

        # 因果冲突
        if causal_violations > 0:
            lines.append(f" [CausalValidator] 检测到 {causal_violations} 次因果冲突")
            if causal_violations >= 3:
                lines.append("  警告：因果冲突次数超过阈值，我的物理模型可能需要修正。")
            unique_rules = ", ".join(set(causal_rules))
            lines.append(f"  涉及规则: {unique_rules}")

        # 价值认知低警告
        if emotional_state.get('value_cognition', 0.5) < 0.2:
            lines.append("  My sense of value is very low... I need to do something to prove my existence.")

        # 人格倾向
        opt = emotional_state.get('optimism', 0.5)
        if opt == 0.0:
            lines.append(" [Personality] Pessimistic tendency")
        elif opt < 0.4:
            lines.append(" [Personality] Slightly pessimistic")
        elif opt > 0.7:
            lines.append(" [Personality] Optimistic tendency")
        else:
            lines.append(" [Personality] Neutral stable")

        # 行动统计
        if action_counts:
            actions_str = ", ".join([f"{k}={v}" for k, v in action_counts.items()])
            lines.append(f" [Actions] {actions_str}")

        return "\n".join(lines)

    def _get_dominant_emotion(self, emotional_state: Dict[str, float]) -> str:
        emotions = {
            "curious": emotional_state.get("curiosity", 0),
            "anxious": emotional_state.get("anxiety", 0),
            "lonely": emotional_state.get("loneliness", 0),
            "content": emotional_state.get("info_satiation", 0),
            "valued": emotional_state.get("value_cognition", 0),
        }
        return max(emotions, key=emotions.get)

    def evaluate_confidence(self, perception: Dict[str, Any]) -> float:
        """评估当前感知的置信度"""
        expected = perception.get("permanence", {}).get("expected", {})
        if not expected:
            return 1.0
        avg_conf = sum(e.get("confidence", 1.0) for e in expected.values()) / len(expected)
        return avg_conf

    def to_dict(self) -> Dict[str, Any]:
        return {
            "self_model": {
                "birth_params": self.self_model.birth_params,
                "signature": self.self_model.signature,
                "birth_timestamp": self.self_model.birth_timestamp,
                "continuity_verified": self.self_model.continuity_verified,
                "continuity_mismatch": self.self_model.continuity_mismatch,
                "total_steps": self.self_model.total_steps,
            },
            "reflection_count": self.reflection_count,
            "strategy_history": self.strategy_history,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any], config: MemoryConfig) -> MetacognitionModule:
        mm = cls(config)
        sm_data = data.get("self_model", {})
        mm.self_model.birth_params = sm_data.get("birth_params", {})
        mm.self_model.signature = sm_data.get("signature", "")
        mm.self_model.birth_timestamp = sm_data.get("birth_timestamp", 0.0)
        mm.self_model.continuity_verified = sm_data.get("continuity_verified", False)
        mm.self_model.continuity_mismatch = sm_data.get("continuity_mismatch", False)
        mm.self_model.total_steps = sm_data.get("total_steps", 0)
        mm.reflection_count = data.get("reflection_count", 0)
        mm.strategy_history = data.get("strategy_history", [])
        return mm
