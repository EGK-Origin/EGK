"""EGK v4 行动模块 —— 欲望计算、行动选择、物理执行"""
from __future__ import annotations
import math
import random
from typing import Dict, List, Tuple, Optional, Any

from egk.core.types import Box, User, Position
from egk.core.config import EnergyConfig, PhysicsConfig
from egk.modules.causality import CausalValidator
from egk.utils.helpers import clamp, noisy_value


class ActionModule:
    """行动模块"""
    def __init__(self, energy_config: EnergyConfig, physics: PhysicsConfig):
        self.energy_config = energy_config
        self.physics = physics
        self.consecutive_push_steps = 0
        self.last_pushed_color: Optional[str] = None
        self.current_target_color: Optional[str] = None

    def compute_desires(self, perception: Dict[str, Any],
                       emotional_state: Dict[str, float]) -> Dict[str, float]:
        """计算欲望权重"""
        weights = {
            "approach_light": 0.3,
            "seek_box": 0.0,
            "retreat_to_light": 0.0,
            "empathy_seek": 0.0,
        }

        curiosity = emotional_state.get("curiosity", 0.1)
        satiation = emotional_state.get("info_satiation", 0.0)
        value_cog = emotional_state.get("value_cognition", 0.5)
        anxiety = emotional_state.get("anxiety", 0.0)

        if satiation > 0.3:
            weights["seek_box"] += curiosity * 0.5
        if value_cog < 0.3:
            weights["seek_box"] += (0.3 - value_cog) * 2.0
        if anxiety > 0.6:
            weights["retreat_to_light"] += anxiety * 0.5

        box_states = perception.get("box_states", {})
        if any(s["in_zone"] for s in box_states.values()):
            weights["retreat_to_light"] += 0.8

        user_states = perception.get("user_states", {})
        for name, state in user_states.items():
            if state.get("emotion") == "distress":
                weights["empathy_seek"] += 1.5

        permanence = perception.get("permanence", {})
        for key, exp in permanence.get("expected", {}).items():
            if exp.get("confidence", 1.0) < 0.7 and exp.get("type") == "box":
                weights["seek_box"] += 0.1 * (1.0 - exp.get("confidence", 1.0))

        return weights

    def select_action(self, weights: Dict[str, float],
                     perception: Dict[str, Any],
                     causal_validator: CausalValidator,
                     agent_pos: Position, agent_energy: float,
                     max_energy: float, boxes: Dict[str, Box],
                     users: Dict[str, User], step_count: int) -> str:
        """选择行动（含因果验证）"""
        noisy = {k: noisy_value(v, 0.02) for k, v in weights.items()}

        validated = {}
        for action in noisy:
            adjusted, violations = causal_validator.validate(
                action, agent_pos, agent_energy, max_energy,
                boxes, users, step_count
            )
            validated[action] = adjusted.get(action, noisy[action])

        return max(validated, key=validated.get)

    def execute(self, action: str, perception: Dict[str, Any],
                agent_pos: Position, boxes: Dict[str, Box],
                users: Dict[str, User], light_pos: Position) -> Tuple[float, float, float]:
        """执行行动，返回 (new_x, new_y, energy_cost)"""
        cost = self.energy_config.metabolic_cost_per_step

        if action == "empathy_seek":
            target_user = None
            for name, state in perception.get("user_states", {}).items():
                if state.get("emotion") == "distress":
                    target_user = users.get(name)
                    break
            if target_user:
                dx = target_user.pos.x - agent_pos.x
                dy = target_user.pos.y - agent_pos.y
                dist = math.hypot(dx, dy)
                if dist > 0.5:
                    speed = min(dist, 0.9)
                    agent_pos.x += (dx / dist) * speed
                    agent_pos.y += (dy / dist) * speed
                    cost += speed * self.energy_config.movement_cost_factor
            return agent_pos.x, agent_pos.y, cost

        if action == "seek_box":
            target_color = self._select_target_box(boxes, users, perception)
            self.current_target_color = target_color
            box = boxes.get(target_color)
            if not box:
                return agent_pos.x, agent_pos.y, cost

            dx = box.pos.x - agent_pos.x
            dy = box.pos.y - agent_pos.y
            dist = math.hypot(dx, dy)

            if dist < 0.5:
                dx_to_light = light_pos.x - box.pos.x
                dy_to_light = light_pos.y - box.pos.y
                dist_to_light = math.hypot(dx_to_light, dy_to_light)
                if dist_to_light > 0.1:
                    ux = dx_to_light / dist_to_light
                    uy = dy_to_light / dist_to_light
                    box.update_position(box.pos.x + ux * 0.4, box.pos.y + uy * 0.4)
                    agent_pos.x += ux * 0.3
                    agent_pos.y += uy * 0.3
                self.consecutive_push_steps += 1
                cost += self.energy_config.push_cost
            else:
                agent_pos.x += (dx / dist) * 0.5
                agent_pos.y += (dy / dist) * 0.5
                cost += 0.5 * self.energy_config.movement_cost_factor
                self.consecutive_push_steps = 0

            if box.in_zone or self.consecutive_push_steps > 30:
                self.consecutive_push_steps = 0
                return agent_pos.x, agent_pos.y, cost + 0.5

            return agent_pos.x, agent_pos.y, cost

        if action == "retreat_to_light":
            dx = light_pos.x - agent_pos.x
            dy = light_pos.y - agent_pos.y
            dist = math.hypot(dx, dy)
            if dist < 1.0:
                return agent_pos.x, agent_pos.y, cost
            else:
                agent_pos.x += (dx / dist) * 0.4
                agent_pos.y += (dy / dist) * 0.4
                cost += 0.4 * self.energy_config.movement_cost_factor
            return agent_pos.x, agent_pos.y, cost

        # approach_light
        dx = light_pos.x - agent_pos.x
        dy = light_pos.y - agent_pos.y
        dist = math.hypot(dx, dy)
        if dist > 1.0:
            agent_pos.x += (dx / dist) * 0.3
            agent_pos.y += (dy / dist) * 0.3
            cost += 0.3 * self.energy_config.movement_cost_factor
        self.consecutive_push_steps = 0
        return agent_pos.x, agent_pos.y, cost

    def _select_target_box(self, boxes: Dict[str, Box], users: Dict[str, User],
                          perception: Dict[str, Any]) -> str:
        """选择目标箱子"""
        if not boxes:
            return "red"
        colors = list(boxes.keys())

        for name, state in perception.get("user_states", {}).items():
            if state.get("emotion") == "distress":
                pref = users.get(name, User()).preferred_color
                if pref in colors:
                    return pref

        if self.last_pushed_color in colors:
            idx = colors.index(self.last_pushed_color)
            return colors[(idx + 1) % len(colors)]
        return colors[0]

    def reset_world(self, boxes: Dict[str, Box], light_pos: Position):
        """重置世界"""
        for box in boxes.values():
            box.reset_exempt = True
            angle = random.uniform(0.0, 2.0 * math.pi)
            radius = random.uniform(8.0, 12.0)
            new_x = light_pos.x + radius * math.cos(angle)
            new_y = light_pos.y + radius * math.sin(angle)
            box.update_position(new_x, new_y)
            box._prev_pos = Position(new_x, new_y)
            box.in_zone = False
            box.prev_in_zone = False
            box.reset_exempt = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "consecutive_push_steps": self.consecutive_push_steps,
            "last_pushed_color": self.last_pushed_color,
            "current_target_color": self.current_target_color,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any], energy_config: EnergyConfig, physics: PhysicsConfig):
        am = cls(energy_config, physics)
        am.consecutive_push_steps = data.get("consecutive_push_steps", 0)
        am.last_pushed_color = data.get("last_pushed_color", None)
        am.current_target_color = data.get("current_target_color", None)
        return am
