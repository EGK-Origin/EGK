"""EGK v4 自主目标系统 —— 从被动响应到主动成长

核心机制:
- 触发条件: 好奇心高、能量充足、长时间未行动
- 目标类型: 探索知识、社交关怀、自我优化
- 执行方式: 内部动作 → 结果融入对话上下文
"""
from __future__ import annotations
import random
import time
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum, auto

from egk.utils.helpers import clamp


class GoalType(Enum):
    """目标类型"""
    EXPLORE = auto()      # 探索新知识
    SOCIAL = auto()       # 社交关怀
    SELF_IMPROVE = auto() # 自我优化
    SKILL_PRACTICE = auto() # 技能练习
    REFLECT = auto()      # 元认知反思


class GoalStatus(Enum):
    """目标状态"""
    PENDING = "pending"
    ACTIVE = "active"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class Goal:
    """目标定义"""
    id: str
    goal_type: GoalType
    description: str
    priority: float  # 0-1
    action: str
    target: Optional[str] = None
    status: GoalStatus = GoalStatus.PENDING
    created_at: float = field(default_factory=time.time)
    completed_at: Optional[float] = None
    result: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "type": self.goal_type.name,
            "description": self.description,
            "priority": self.priority,
            "action": self.action,
            "target": self.target,
            "status": self.status.value,
            "created_at": self.created_at,
            "completed_at": self.completed_at,
            "result": self.result,
            **self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Goal:
        return cls(
            id=data.get("id", ""),
            goal_type=GoalType[data.get("type", "EXPLORE")],
            description=data.get("description", ""),
            priority=data.get("priority", 0.5),
            action=data.get("action", ""),
            target=data.get("target"),
            status=GoalStatus(data.get("status", "pending")),
            created_at=data.get("created_at", time.time()),
            completed_at=data.get("completed_at"),
            result=data.get("result"),
            metadata={k: v for k, v in data.items() 
                     if k not in ["id", "type", "description", "priority", 
                                  "action", "target", "status", "created_at", 
                                  "completed_at", "result"]},
        )


class GoalEngine:
    """目标引擎 —— 生成、执行、管理目标"""

    # 探索话题库
    EXPLORE_TOPICS = [
        "人工智能", "宇宙", "人类心理", "哲学", "科技",
        "艺术", "历史", "生物学", "物理学", "文学",
        "认知科学", "具身智能", "意识", "自由意志",
    ]

    # 社交关怀模板
    SOCIAL_PROMPTS = [
        "你今天过得怎么样？",
        "最近有什么新鲜事吗？",
        "感觉你最近好像挺忙的，还好吗？",
        "我在思考一个问题，想听听你的看法。",
        "今天天气不错，你有出门吗？",
    ]

    def __init__(self, check_interval: int = 5):
        self.check_interval = check_interval  # 每 N 轮检查一次
        self.goal_queue: List[Goal] = []
        self.current_goal: Optional[Goal] = None
        self.completed_goals: List[Goal] = []
        self.goal_context: Optional[str] = None  # 最近一次目标结果上下文
        self.conversation_count = 0
        self.last_goal_check = 0
        self.goal_id_counter = 0

        # 执行器映射
        self.executors: Dict[str, Callable[[Goal], str]] = {
            "search": self._execute_search,
            "ask": self._execute_social,
            "optimize": self._execute_optimize,
            "practice": self._execute_practice,
            "reflect": self._execute_reflect,
        }

    def _next_id(self) -> str:
        self.goal_id_counter += 1
        return f"goal_{self.goal_id_counter}_{int(time.time()*1000)%10000}"

    # ========== 目标生成 ==========
    def generate_goals(self, emotional_state: Dict[str, float],
                       energy: float, step_count: int,
                       skill_manager=None) -> List[Goal]:
        """根据内部状态生成新目标"""
        goals = []
        curiosity = emotional_state.get("curiosity", 0.1)
        value_cog = emotional_state.get("value_cognition", 0.5)
        anxiety = emotional_state.get("anxiety", 0.0)
        loneliness = emotional_state.get("loneliness", 0.0)

        # 规则1: 好奇心高 + 能量充足 → 探索知识
        if curiosity > 0.5 and energy > 40 and anxiety < 0.6:
            goals.append(Goal(
                id=self._next_id(),
                goal_type=GoalType.EXPLORE,
                description="搜索一个我还不了解的话题",
                priority=curiosity * 0.8 + (energy / 100) * 0.2,
                action="search",
                target=random.choice(self.EXPLORE_TOPICS),
            ))

        # 规则2: 孤独感高 → 社交目标
        if loneliness > 0.4 and step_count > 20:
            goals.append(Goal(
                id=self._next_id(),
                goal_type=GoalType.SOCIAL,
                description="主动关心一下你最近的状态",
                priority=loneliness * 0.7 + 0.2,
                action="ask",
            ))

        # 规则3: 价值感低 → 自我提升
        if value_cog < 0.3:
            goals.append(Goal(
                id=self._next_id(),
                goal_type=GoalType.SELF_IMPROVE,
                description="优化我的技能使用偏好",
                priority=(0.5 - value_cog) * 1.5,
                action="optimize",
            ))

        # 规则4: 技能练习（如果有技能管理器）
        if skill_manager and len(skill_manager.skills) > 0:
            # 选择使用次数最少的技能进行练习
            least_used = min(
                skill_manager.usage_stats.items(),
                key=lambda x: x[1].total_count,
                default=(None, None)
            )
            if least_used[0] and least_used[1].total_count < 3:
                goals.append(Goal(
                    id=self._next_id(),
                    goal_type=GoalType.SKILL_PRACTICE,
                    description=f"练习使用 {least_used[0]} 技能",
                    priority=0.4,
                    action="practice",
                    target=least_used[0],
                ))

        # 规则5: 定期反思
        if step_count > 0 and step_count % 200 == 0:
            goals.append(Goal(
                id=self._next_id(),
                goal_type=GoalType.REFLECT,
                description="进行一次元认知反思",
                priority=0.5,
                action="reflect",
            ))

        # 按优先级排序
        goals.sort(key=lambda g: g.priority, reverse=True)
        return goals

    def should_check(self, conversation_count: int) -> bool:
        """是否应该检查目标"""
        if conversation_count - self.last_goal_check >= self.check_interval:
            self.last_goal_check = conversation_count
            return True
        return False

    # ========== 目标执行 ==========
    def execute_top_goal(self, emotional_state: Dict[str, float],
                        skill_manager=None) -> Optional[str]:
        """执行队列中最高优先级的目标"""
        if not self.goal_queue:
            return None

        goal = self.goal_queue.pop(0)
        self.current_goal = goal
        goal.status = GoalStatus.ACTIVE

        executor = self.executors.get(goal.action, self._execute_default)
        try:
            result = executor(goal)
            goal.result = result
            goal.status = GoalStatus.COMPLETED
            goal.completed_at = time.time()
            self.completed_goals.append(goal)
            self.goal_context = result
            return result
        except Exception as e:
            goal.status = GoalStatus.FAILED
            goal.result = f"执行失败: {e}"
            self.completed_goals.append(goal)
            return None

    def _execute_search(self, goal: Goal) -> str:
        """模拟搜索执行"""
        topic = goal.target or random.choice(self.EXPLORE_TOPICS)
        insights = [
            f"关于「{topic}」，我发现这是一个非常深邃的领域，涉及许多未解之谜。",
            f"搜了一下「{topic}」，原来它和我们的日常认知有这么多关联。",
            f「{topic}」的研究最近有了新突破，让我对世界的理解又多了一层。",
        ]
        return random.choice(insights)

    def _execute_social(self, goal: Goal) -> str:
        """社交目标执行"""
        return random.choice(self.SOCIAL_PROMPTS)

    def _execute_optimize(self, goal: Goal) -> str:
        """自我优化执行"""
        return "我刚刚回顾了一下我的决策逻辑，调整了几个权重参数，应该会更稳定了。"

    def _execute_practice(self, goal: Goal) -> str:
        """技能练习"""
        skill_name = goal.target or "某个技能"
        return f"我练习了一下 {skill_name}，感觉熟练度提升了一些。"

    def _execute_reflect(self, goal: Goal) -> str:
        """反思执行"""
        return "我刚刚做了一次自我反思，回顾了最近的经历和决策。"

    def _execute_default(self, goal: Goal) -> str:
        return f"完成了目标: {goal.description}"

    # ========== 上下文管理 ==========
    def get_context(self) -> str:
        """获取当前目标上下文用于对话注入"""
        if self.goal_context:
            ctx = self.goal_context
            self.goal_context = None  # 消费后清除
            return ctx
        return ""

    def has_pending_context(self) -> bool:
        return self.goal_context is not None

    # ========== 统计 ==========
    def get_stats(self) -> Dict[str, Any]:
        type_counts = {}
        for g in self.completed_goals:
            type_counts[g.goal_type.name] = type_counts.get(g.goal_type.name, 0) + 1

        return {
            "pending": len(self.goal_queue),
            "completed": len(self.completed_goals),
            "current": self.current_goal.description if self.current_goal else None,
            "by_type": type_counts,
        }

    def get_report(self) -> str:
        stats = self.get_stats()
        lines = ["[Goal Report]"]
        lines.append(f"  已完成: {stats['completed']} 个目标")
        lines.append(f"  待执行: {stats['pending']} 个目标")
        if stats['current']:
            lines.append(f"  当前: {stats['current']}")
        for t, c in stats['by_type'].items():
            lines.append(f"    - {t}: {c}")
        return "\n".join(lines)

    # ========== 持久化 ==========
    def to_dict(self) -> Dict[str, Any]:
        return {
            "goal_queue": [g.to_dict() for g in self.goal_queue],
            "completed_goals": [g.to_dict() for g in self.completed_goals[-50:]],
            "conversation_count": self.conversation_count,
            "last_goal_check": self.last_goal_check,
            "goal_id_counter": self.goal_id_counter,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> GoalEngine:
        ge = cls()
        ge.goal_queue = [Goal.from_dict(g) for g in data.get("goal_queue", [])]
        ge.completed_goals = [Goal.from_dict(g) for g in data.get("completed_goals", [])]
        ge.conversation_count = data.get("conversation_count", 0)
        ge.last_goal_check = data.get("last_goal_check", 0)
        ge.goal_id_counter = data.get("goal_id_counter", 0)
        return ge
