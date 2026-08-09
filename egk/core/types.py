"""EGK v4 基础类型与实体定义"""
from __future__ import annotations
import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any
from enum import Enum, auto


class ActionType(Enum):
    """行动类型枚举"""
    APPROACH_LIGHT = auto()
    SEEK_BOX = auto()
    RETREAT_TO_LIGHT = auto()
    EMPATHY_SEEK = auto()
    IDLE = auto()


class EmotionTag(Enum):
    """情绪标签枚举"""
    NORMAL = "normal"
    SACRIFICE = "sacrifice"
    EMPATHY = "empathy"
    REWARD = "reward"
    PERMANENCE = "permanence"
    CAUSAL = "causal"
    CONTINUITY = "continuity"
    ATTENTION = "attention"


class AgentState(Enum):
    """Agent 状态枚举"""
    APPROACH_LIGHT = "APPROACH_LIGHT"
    SEEK_BOX = "SEEK_BOX"
    RETREAT_TO_LIGHT = "RETREAT_TO_LIGHT"
    EMPATHY_SEEK = "EMPATHY_SEEK"
    IDLE = "IDLE"


@dataclass
class Position:
    """二维位置"""
    x: float = 0.0
    y: float = 0.0

    def distance_to(self, other: Position) -> float:
        return math.hypot(self.x - other.x, self.y - other.y)

    def to_tuple(self) -> Tuple[float, float]:
        return (self.x, self.y)

    @classmethod
    def from_tuple(cls, t: Tuple[float, float]) -> Position:
        return cls(t[0], t[1])


@dataclass
class Entity:
    """物理实体基类"""
    pos: Position = field(default_factory=Position)
    label: str = ""

    def distance_to(self, other: Entity) -> float:
        return self.pos.distance_to(other.pos)

    def distance_to_point(self, x: float, y: float) -> float:
        return math.hypot(self.pos.x - x, self.pos.y - y)

    def to_dict(self) -> Dict[str, Any]:
        return {"x": self.pos.x, "y": self.pos.y, "label": self.label}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Entity:
        return cls(pos=Position(data.get("x", 0.0), data.get("y", 0.0)), label=data.get("label", ""))


@dataclass
class Box(Entity):
    """箱子实体"""
    color: str = "red"
    in_zone: bool = False
    prev_in_zone: bool = False
    removed: bool = False
    reset_exempt: bool = False
    _prev_pos: Position = field(default_factory=Position)

    def __post_init__(self):
        if not self.label:
            self.label = f"box_{self.color}"
        self._prev_pos = Position(self.pos.x, self.pos.y)

    def is_in_zone(self, light_pos: Position, radius: float) -> bool:
        self.prev_in_zone = self.in_zone
        self.in_zone = self.pos.distance_to(light_pos) < radius
        return self.in_zone

    def update_position(self, x: float, y: float):
        self._prev_pos = Position(self.pos.x, self.pos.y)
        self.pos.x = x
        self.pos.y = y

    def to_dict(self) -> Dict[str, Any]:
        d = super().to_dict()
        d.update({
            "color": self.color,
            "in_zone": self.in_zone,
            "prev_in_zone": self.prev_in_zone,
            "removed": self.removed,
            "_prev_x": self._prev_pos.x,
            "_prev_y": self._prev_pos.y,
            "reset_exempt": self.reset_exempt,
        })
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Box:
        box = cls(
            pos=Position(data.get("x", 0.0), data.get("y", 0.0)),
            color=data.get("color", "red")
        )
        box.in_zone = data.get("in_zone", False)
        box.prev_in_zone = data.get("prev_in_zone", False)
        box.removed = data.get("removed", False)
        box._prev_pos = Position(data.get("_prev_x", box.pos.x), data.get("_prev_y", box.pos.y))
        box.reset_exempt = data.get("reset_exempt", False)
        return box


@dataclass
class User(Entity):
    """用户实体"""
    name: str = ""
    preferred_color: str = "red"
    emotion: str = "neutral"

    def __post_init__(self):
        if not self.label:
            self.label = f"user_{self.name}"

    def get_social_value(self, box_color: str) -> float:
        return 0.2 if box_color == self.preferred_color else -0.1

    def to_dict(self) -> Dict[str, Any]:
        d = super().to_dict()
        d.update({
            "name": self.name,
            "preferred_color": self.preferred_color,
            "emotion": self.emotion,
        })
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> User:
        user = cls(
            pos=Position(data.get("x", 0.0), data.get("y", 0.0)),
            name=data.get("name", ""),
            preferred_color=data.get("preferred_color", "red")
        )
        user.emotion = data.get("emotion", "neutral")
        return user


@dataclass
class MemoryEvent:
    """记忆事件"""
    step: int
    action: str
    value_delta: float = 0.0
    energy_cost: float = 0.0
    user_feedback: str = ""
    emotion_tag: str = "normal"
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "step": self.step,
            "action": self.action,
            "value_delta": self.value_delta,
            "energy_cost": self.energy_cost,
            "user_feedback": self.user_feedback,
            "emotion_tag": self.emotion_tag,
            **self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> MemoryEvent:
        metadata = {k: v for k, v in data.items() 
                    if k not in ["step", "action", "value_delta", "energy_cost", "user_feedback", "emotion_tag"]}
        return cls(
            step=data.get("step", 0),
            action=data.get("action", ""),
            value_delta=data.get("value_delta", 0.0),
            energy_cost=data.get("energy_cost", 0.0),
            user_feedback=data.get("user_feedback", ""),
            emotion_tag=data.get("emotion_tag", "normal"),
            metadata=metadata,
        )
