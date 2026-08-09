"""EGK v4 分层记忆系统 —— 感觉/工作/长期记忆"""
from __future__ import annotations
from collections import deque, Counter, defaultdict
from typing import Dict, List, Tuple, Optional, Any

from egk.core.types import MemoryEvent
from egk.core.config import MemoryConfig


class SensoryMemory:
    """感觉记忆: 极短保持, 容量大, 原始感知数据"""
    def __init__(self, max_len: int = 100):
        self.buffer: deque = deque(maxlen=max_len)

    def push(self, perception: Dict[str, Any]):
        self.buffer.append(perception)

    def get_recent(self, n: int = 5) -> List[Dict[str, Any]]:
        return list(self.buffer)[-n:]

    def clear(self):
        self.buffer.clear()


class WorkingMemory:
    """工作记忆: 有限容量(7+-2), 当前意识内容"""
    def __init__(self, capacity: int = 7):
        self.capacity = capacity
        self.items: List[Dict[str, Any]] = []
        self.focus: Optional[str] = None

    def push(self, item: Dict[str, Any]) -> bool:
        if len(self.items) >= self.capacity:
            return False
        self.items.append(item)
        return True

    def pop_oldest(self) -> Optional[Dict[str, Any]]:
        if self.items:
            return self.items.pop(0)
        return None

    def set_focus(self, focus_id: str):
        self.focus = focus_id

    def get_focused(self) -> Optional[Dict[str, Any]]:
        if not self.focus:
            return None
        for item in self.items:
            if item.get("id") == self.focus:
                return item
        return None

    def clear(self):
        self.items.clear()
        self.focus = None


class LongTermMemory:
    """长期记忆: 陈述性(事实)、程序性(技能)、情节性(事件)"""
    def __init__(self):
        self.declarative: Dict[str, Any] = {}
        self.procedural: Dict[str, Tuple[float, int]] = {}
        self.episodic: deque = deque(maxlen=5000)
        self.tagged_events: Dict[str, List[MemoryEvent]] = defaultdict(list)

    def add_episodic(self, event: MemoryEvent):
        self.episodic.append(event)
        self.tagged_events[event.emotion_tag].append(event)

    def query_tagged(self, tag: str, last_n: int = 10) -> List[MemoryEvent]:
        events = self.tagged_events.get(tag, [])
        return events[-last_n:]

    def get_sacrifice_summary(self) -> Tuple[int, float]:
        events = self.tagged_events.get("sacrifice", [])
        total_cost = sum(e.energy_cost for e in events)
        return len(events), total_cost

    def get_empathy_summary(self) -> Tuple[int, float]:
        events = self.tagged_events.get("empathy", [])
        valid_times = [e.metadata.get("response_time", 0.0) for e in events 
                       if e.metadata.get("response_time") is not None]
        avg_time = sum(valid_times) / len(valid_times) if valid_times else 0.0
        return len(events), avg_time

    def get_permanence_summary(self) -> Tuple[int, int]:
        events = self.tagged_events.get("permanence", [])
        successes = sum(1 for e in events if e.metadata.get("outcome") == "success")
        failures = sum(1 for e in events if e.metadata.get("outcome") == "failure")
        return successes, failures

    def get_causal_summary(self) -> Tuple[int, List[str]]:
        events = self.tagged_events.get("causal", [])
        violations = [e for e in events if e.metadata.get("type") == "violation"]
        rules = list(set(e.metadata.get("rule", "unknown") for e in violations))
        return len(violations), rules

    def get_continuity_summary(self) -> Tuple[int, int]:
        events = self.tagged_events.get("continuity", [])
        passes = sum(1 for e in events if e.metadata.get("result") == "pass")
        fails = sum(1 for e in events if e.metadata.get("result") == "fail")
        return passes, fails

    def update_procedural(self, action: str, success: bool):
        if action not in self.procedural:
            self.procedural[action] = (0.0, 0)
        rate, count = self.procedural[action]
        new_count = count + 1
        new_rate = (rate * count + (1.0 if success else 0.0)) / new_count
        self.procedural[action] = (new_rate, new_count)

    def get_procedural_success_rate(self, action: str) -> float:
        return self.procedural.get(action, (0.5, 0))[0]


class MemorySystem:
    """记忆系统门面"""
    def __init__(self, config: MemoryConfig):
        self.config = config
        self.sensory = SensoryMemory()
        self.working = WorkingMemory(capacity=config.working_memory_capacity)
        self.long_term = LongTermMemory()
        self.step_count = 0

    def perceive(self, perception: Dict[str, Any]):
        self.sensory.push(perception)
        if perception.get("priority", 5) <= 3:
            if not self.working.push(perception):
                self.working.pop_oldest()
                self.working.push(perception)

    def record_event(self, event: MemoryEvent):
        self.long_term.add_episodic(event)

    def consolidate(self):
        for item in self.working.items:
            if item.get("important"):
                event = MemoryEvent(
                    step=self.step_count,
                    action="consolidation",
                    metadata={"source": "working_memory", "data": item}
                )
                self.long_term.add_episodic(event)
        self.working.clear()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "episodic": [e.to_dict() for e in self.long_term.episodic],
            "declarative": dict(self.long_term.declarative),
            "procedural": dict(self.long_term.procedural),
            "tagged_events": {k: [e.to_dict() for e in v] 
                             for k, v in self.long_term.tagged_events.items()},
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any], config: MemoryConfig):
        ms = cls(config)
        for e_data in data.get("episodic", []):
            ms.long_term.episodic.append(MemoryEvent.from_dict(e_data))
        for tag, events in data.get("tagged_events", {}).items():
            ms.long_term.tagged_events[tag] = [MemoryEvent.from_dict(e) for e in events]
        ms.long_term.declarative = data.get("declarative", {})
        ms.long_term.procedural = {k: tuple(v) for k, v in data.get("procedural", {}).items()}
        return ms
