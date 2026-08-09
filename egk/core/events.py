"""EGK v4 事件总线 —— 模块间解耦通信"""
from __future__ import annotations
from typing import Dict, List, Callable, Any, Optional
from dataclasses import dataclass, field
from collections import defaultdict
import time


@dataclass
class EGKEvent:
    """EGK 事件"""
    event_type: str
    source: str
    data: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    priority: int = 5  # 1-10, 数字越小优先级越高


class EventBus:
    """异步事件总线"""
    def __init__(self):
        self._handlers: Dict[str, List[Callable[[EGKEvent], None]]] = defaultdict(list)
        self._history: List[EGKEvent] = []
        self._history_limit: int = 1000

    def subscribe(self, event_type: str, handler: Callable[[EGKEvent], None]):
        """订阅事件"""
        self._handlers[event_type].append(handler)

    def unsubscribe(self, event_type: str, handler: Callable[[EGKEvent], None]):
        """取消订阅"""
        if handler in self._handlers[event_type]:
            self._handlers[event_type].remove(handler)

    def emit(self, event: EGKEvent):
        """发射事件"""
        self._history.append(event)
        if len(self._history) > self._history_limit:
            self._history.pop(0)

        handlers = self._handlers.get(event.event_type, [])
        for handler in handlers:
            try:
                handler(event)
            except Exception as e:
                print(f"[EventBus] Handler error for {event.event_type}: {e}")

    def emit_simple(self, event_type: str, source: str, data: Optional[Dict[str, Any]] = None):
        """简化发射"""
        self.emit(EGKEvent(event_type=event_type, source=source, data=data or {}))

    def get_history(self, event_type: Optional[str] = None, last_n: int = 10) -> List[EGKEvent]:
        """获取事件历史"""
        events = self._history
        if event_type:
            events = [e for e in events if e.event_type == event_type]
        return events[-last_n:]

    def clear_history(self):
        self._history.clear()
