"""EGK v4 感知模块 + 对象恒存性"""
from __future__ import annotations
import math
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, field

from egk.core.types import Entity, Box, User, Position
from egk.core.config import PhysicsConfig, PermanenceConfig


@dataclass
class ObjectExpectation:
    """对象期望（对象恒存性）"""
    key: str
    pos: Position
    confidence: float = 1.0
    last_seen_step: int = 0
    obj_type: str = "unknown"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "key": self.key, "x": self.pos.x, "y": self.pos.y,
            "confidence": self.confidence, "last_seen_step": self.last_seen_step,
            "type": self.obj_type,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> ObjectExpectation:
        return cls(
            key=data.get("key", ""),
            pos=Position(data.get("x", 0.0), data.get("y", 0.0)),
            confidence=data.get("confidence", 1.0),
            last_seen_step=data.get("last_seen_step", 0),
            obj_type=data.get("type", "unknown"),
        )


class ObjectPermanence:
    """对象恒存性层 —— 即使对象不可见也维持其存在信念"""
    def __init__(self, config: PermanenceConfig, physics: PhysicsConfig):
        self.config = config
        self.physics = physics
        self.expectations: Dict[str, ObjectExpectation] = {}
        self.prediction_successes = 0
        self.prediction_failures = 0

    def update(self, agent_pos: Position, step_count: int,
               boxes: Dict[str, Box], users: Dict[str, User]) -> Dict[str, Any]:
        """更新对象恒存性状态"""
        visible = {}
        expected = {}

        # 处理可见对象
        for color, box in boxes.items():
            if box.removed:
                continue
            dist = agent_pos.distance_to(box.pos)
            if dist <= self.physics.perception_range:
                key = f"box_{color}"
                visible[key] = {
                    "pos": box.pos, "dist": dist,
                    "in_zone": box.in_zone, "type": "box",
                }
                self._update_expectation(key, box.pos, step_count, "box", expected)

        for name, user in users.items():
            dist = agent_pos.distance_to(user.pos)
            if dist <= self.physics.perception_range:
                key = f"user_{name}"
                visible[key] = {
                    "pos": user.pos, "dist": dist,
                    "emotion": user.emotion, "type": "user",
                }
                self._update_expectation(key, user.pos, step_count, "user", expected)

        # 处理不可见对象（期望衰减）
        for key, exp in list(self.expectations.items()):
            if key not in visible:
                steps_unseen = step_count - exp.last_seen_step
                new_conf = max(0.0, exp.confidence - self.config.uncertainty_decay_rate * steps_unseen)
                exp.confidence = new_conf

                if new_conf < self.config.confidence_threshold:
                    del self.expectations[key]
                    self.prediction_failures += 1
                else:
                    expected[key] = {
                        "pos": exp.pos, "confidence": new_conf,
                        "steps_unseen": steps_unseen, "type": exp.obj_type,
                        "prediction_success": False,
                    }

        return {
            "visible": visible,
            "expected": expected,
            "perception_range": self.physics.perception_range,
        }

    def _update_expectation(self, key: str, pos: Position, step: int, 
                           obj_type: str, expected: Dict):
        if key in self.expectations:
            exp = self.expectations[key]
            old_conf = exp.confidence
            new_conf = min(1.0, old_conf + self.config.uncertainty_recovery_rate)

            # 预测验证
            pred_dist = pos.distance_to(exp.pos)
            if pred_dist <= self.config.prediction_success_radius and old_conf < 1.0:
                new_conf = min(1.0, new_conf + self.config.prediction_success_bonus)
                self.prediction_successes += 1
                expected[key] = {
                    "pos": pos, "prediction_success": True,
                    "pred_dist": pred_dist, "confidence": new_conf,
                    "type": obj_type,
                }

            exp.pos = pos
            exp.confidence = new_conf
            exp.last_seen_step = step
        else:
            self.expectations[key] = ObjectExpectation(
                key=key, pos=pos, confidence=1.0,
                last_seen_step=step, obj_type=obj_type,
            )

    def get_expected_position(self, obj_key: str) -> Optional[Tuple[float, float, float]]:
        if obj_key in self.expectations:
            exp = self.expectations[obj_key]
            return (exp.pos.x, exp.pos.y, exp.confidence)
        return None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "expectations": {k: v.to_dict() for k, v in self.expectations.items()},
            "prediction_successes": self.prediction_successes,
            "prediction_failures": self.prediction_failures,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any], config: PermanenceConfig, physics: PhysicsConfig) -> ObjectPermanence:
        op = cls(config, physics)
        for k, v in data.get("expectations", {}).items():
            op.expectations[k] = ObjectExpectation.from_dict(v)
        op.prediction_successes = data.get("prediction_successes", 0)
        op.prediction_failures = data.get("prediction_failures", 0)
        return op


class PerceptionModule:
    """感知模块门面"""
    def __init__(self, physics: PhysicsConfig, permanence_config: PermanenceConfig):
        self.physics = physics
        self.permanence = ObjectPermanence(permanence_config, physics)
        self.light = Entity(pos=Position(*physics.light_pos), label="light")

    def perceive(self, agent_pos: Position, step_count: int,
                 boxes: Dict[str, Box], users: Dict[str, User]) -> Dict[str, Any]:
        """执行感知循环"""
        dist_to_light = agent_pos.distance_to(self.light.pos)

        # Box 状态
        box_states = {}
        for color, box in boxes.items():
            if box.removed:
                continue
            box.is_in_zone(self.light.pos, self.physics.zone_radius)
            box_states[color] = {
                "dist": agent_pos.distance_to(box.pos),
                "in_zone": box.in_zone,
                "just_entered": box.in_zone and not box.prev_in_zone,
                "pos": box.pos,
            }

        # User 状态
        user_states = {}
        for name, user in users.items():
            user_states[name] = {
                "dist": agent_pos.distance_to(user.pos),
                "emotion": user.emotion,
                "pos": user.pos,
            }

        # 对象恒存性更新
        permanence_output = self.permanence.update(agent_pos, step_count, boxes, users)

        return {
            "dist_to_light": dist_to_light,
            "box_states": box_states,
            "user_states": user_states,
            "permanence": permanence_output,
            "light_pos": self.light.pos,
        }
