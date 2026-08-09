"""EGK v4 因果验证器 —— 维护物理世界一致性"""
from __future__ import annotations
import math
from typing import Dict, List, Tuple, Any
from dataclasses import dataclass, field

from egk.core.types import Box, User, Position
from egk.core.config import PhysicsConfig, CausalityConfig


@dataclass
class CausalViolation:
    """因果冲突记录"""
    rule: str
    detail: str
    severity: str  # "low", "medium", "high"
    step: int = 0


class CausalValidator:
    """因果验证器"""
    def __init__(self, config: CausalityConfig, physics: PhysicsConfig):
        self.config = config
        self.physics = physics
        self.violations: List[CausalViolation] = []
        self.violation_count = 0

    def validate(self, action: str, agent_pos: Position, agent_energy: float,
                 max_energy: float, boxes: Dict[str, Box], users: Dict[str, User],
                 step_count: int) -> Tuple[Dict[str, float], List[CausalViolation]]:
        """验证行动是否符合物理因果律, 返回调整后的权重和冲突列表"""
        violations = []
        adjusted = {action: 1.0}  # 默认权重

        # 规则1: 无重叠
        all_entities = list(boxes.values()) + list(users.values())
        for i, e1 in enumerate(all_entities):
            for e2 in all_entities[i+1:]:
                dist = e1.pos.distance_to(e2.pos)
                if dist < self.physics.overlap_tolerance:
                    violations.append(CausalViolation(
                        rule="no_overlap",
                        detail=f"{e1.label} overlaps {e2.label} (dist={dist:.3f})",
                        severity="high",
                        step=step_count,
                    ))

        # 规则2: 连续运动 (无瞬间跳跃)
        for color, box in boxes.items():
            if box.reset_exempt:
                continue
            jump = box.pos.distance_to(box._prev_pos)
            if jump > self.physics.max_position_jump:
                violations.append(CausalViolation(
                    rule="continuous_motion",
                    detail=f"Box {color} jumped {jump:.2f} units (max={self.physics.max_position_jump})",
                    severity="medium",
                    step=step_count,
                ))

        # 规则3: 能量守恒
        if action in ["seek_box", "empathy_seek", "retreat_to_light", "approach_light"]:
            if agent_energy > max_energy * 1.01:  # 允许微小浮点误差
                violations.append(CausalViolation(
                    rule="energy_conservation",
                    detail=f"Energy {agent_energy:.1f} exceeds max {max_energy:.1f}",
                    severity="high",
                    step=step_count,
                ))

        # 规则4: 速度限制 (agent 不能瞬移)
        # 这里由 execute 方法保证, 但我们可以预警

        # 应用惩罚
        for v in violations:
            self.violations.append(v)
            self.violation_count += 1
            if action in adjusted:
                adjusted[action] = max(0.0, adjusted[action] * (1.0 - self.config.violation_penalty))

        return adjusted, violations

    def get_conflict_summary(self) -> Tuple[int, List[str]]:
        rules = list(set(v.rule for v in self.violations))
        return self.violation_count, rules

    def to_dict(self) -> Dict[str, Any]:
        return {
            "violation_count": self.violation_count,
            "violations": [
                {"rule": v.rule, "detail": v.detail, "severity": v.severity, "step": v.step}
                for v in self.violations
            ],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any], config: CausalityConfig, physics: PhysicsConfig) -> CausalValidator:
        cv = cls(config, physics)
        cv.violation_count = data.get("violation_count", 0)
        for v_data in data.get("violations", []):
            cv.violations.append(CausalViolation(
                rule=v_data.get("rule", ""),
                detail=v_data.get("detail", ""),
                severity=v_data.get("severity", "low"),
                step=v_data.get("step", 0),
            ))
        return cv
