"""EGK v4 注意力系统 —— 自下而上(显著性) + 自上而下(目标导向)"""
from __future__ import annotations
import math
from typing import Dict, List, Tuple, Any, Optional
from dataclasses import dataclass

from egk.core.types import Position
from egk.utils.helpers import clamp


@dataclass
class AttentionSpotlight:
    """注意力聚光灯"""
    target_id: Optional[str] = None
    target_pos: Optional[Position] = None
    intensity: float = 0.5  # 0-1
    source: str = "bottom_up"  # "bottom_up" or "top_down"

    def is_empty(self) -> bool:
        return self.target_id is None


class AttentionSystem:
    """注意力系统"""
    def __init__(self):
        self.spotlight = AttentionSpotlight()
        self.saliency_map: Dict[str, float] = {}
        self.history: List[str] = []

    def compute_saliency(self, perception: Dict[str, Any], 
                        emotional_state: Dict[str, float]) -> Dict[str, float]:
        """计算显著性图 (自下而上)"""
        saliency = {}
        box_states = perception.get("box_states", {})
        user_states = perception.get("user_states", {})

        # Box 显著性: 距离越近越显著, 刚进入 zone 的 box 更显著
        for color, state in box_states.items():
            dist = state["dist"]
            sal = 1.0 / (1.0 + dist * 0.1)
            if state.get("just_entered"):
                sal += 0.5
            saliency[f"box_{color}"] = sal

        # User 显著性: 情绪为 distress 的用户极其显著
        for name, state in user_states.items():
            dist = state["dist"]
            sal = 1.0 / (1.0 + dist * 0.1)
            if state.get("emotion") == "distress":
                sal += 2.0  # 求救信号极高显著性
            saliency[f"user_{name}"] = sal

        # 不确定性对象显著性 (对象恒存性)
        permanence = perception.get("permanence", {})
        for key, exp in permanence.get("expected", {}).items():
            uncertainty = 1.0 - exp.get("confidence", 1.0)
            if uncertainty > 0.3:
                saliency[key] = saliency.get(key, 0.0) + uncertainty * 0.5

        self.saliency_map = saliency
        return saliency

    def top_down_bias(self, current_goal: str, emotional_state: Dict[str, float]) -> Dict[str, float]:
        """目标导向的注意力偏向 (自上而下)"""
        bias = {}

        if current_goal == "seek_box":
            # 增强对 box 的注意力
            for key in self.saliency_map:
                if key.startswith("box_"):
                    bias[key] = 0.3
        elif current_goal == "empathy_seek":
            # 增强对 distress user 的注意力
            for key in self.saliency_map:
                if key.startswith("user_"):
                    bias[key] = 0.4
        elif current_goal == "approach_light":
            # 关注 light
            bias["light"] = 0.2

        # 焦虑状态下注意力变窄 (聚焦最近威胁)
        if emotional_state.get("anxiety", 0.0) > 0.7:
            # 只保留最高显著性的 2 个目标
            sorted_items = sorted(self.saliency_map.items(), key=lambda x: x[1], reverse=True)
            for key, _ in sorted_items[2:]:
                bias[key] = bias.get(key, 0.0) - 0.2

        return bias

    def focus(self, perception: Dict[str, Any], current_goal: str,
              emotional_state: Dict[str, float]) -> AttentionSpotlight:
        """综合自下而上和自上而下, 确定注意力焦点"""
        saliency = self.compute_saliency(perception, emotional_state)
        bias = self.top_down_bias(current_goal, emotional_state)

        # 综合评分
        combined = {}
        for key in set(list(saliency.keys()) + list(bias.keys())):
            combined[key] = saliency.get(key, 0.0) + bias.get(key, 0.0)

        if not combined:
            self.spotlight = AttentionSpotlight()
            return self.spotlight

        # 选择焦点
        best_key = max(combined, key=combined.get)
        best_score = combined[best_key]

        # 确定位置
        target_pos = None
        box_states = perception.get("box_states", {})
        user_states = perception.get("user_states", {})

        if best_key.startswith("box_"):
            color = best_key.replace("box_", "")
            if color in box_states:
                target_pos = box_states[color].get("pos")
        elif best_key.startswith("user_"):
            name = best_key.replace("user_", "")
            if name in user_states:
                target_pos = user_states[name].get("pos")
        elif best_key == "light":
            target_pos = perception.get("light_pos")

        self.spotlight = AttentionSpotlight(
            target_id=best_key,
            target_pos=target_pos,
            intensity=clamp(best_score),
            source="mixed",
        )
        self.history.append(best_key)

        return self.spotlight

    def to_dict(self) -> Dict[str, Any]:
        return {
            "spotlight": {
                "target_id": self.spotlight.target_id,
                "intensity": self.spotlight.intensity,
                "source": self.spotlight.source,
            },
            "history": self.history[-50:],
        }
