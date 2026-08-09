"""EGK v4 主 Agent —— 认知 + 技能 + 自主目标"""
from __future__ import annotations
import json
import os
from typing import Dict, List, Tuple, Optional, Any
from collections import Counter

from egk.core.config import EGKConfig
from egk.core.types import Position, Box, User, MemoryEvent, AgentState
from egk.core.events import EventBus, EGKEvent
from egk.modules.memory import MemorySystem
from egk.modules.perception import PerceptionModule
from egk.modules.emotion import EmotionEngine
from egk.modules.causality import CausalValidator
from egk.modules.attention import AttentionSystem
from egk.modules.metacognition import MetacognitionModule
from egk.modules.action import ActionModule
from egk.modules.skills import EGK_SkillManager
from egk.modules.goal import GoalEngine, GoalType
from egk.utils.helpers import clamp


class EGKAgent:
    """EGK v4 具身智能体 —— 认知存在 + 行动存在 + 自主目标"""

    def __init__(self, config: Optional[EGKConfig] = None,
                 start_pos: Tuple[float, float] = (0.0, -15.0),
                 energy: float = 100.0,
                 state_file: Optional[str] = None):
        self.config = config or EGKConfig()
        self.state_file = state_file or self.config.state_file

        # 出生参数
        self.birth_params = {
            "start_pos": start_pos,
            "energy": energy,
            "memory_capacity": self.config.memory.buffer_maxlen,
            "version": "4.0.0",
        }

        self.pos = Position(start_pos[0], start_pos[1])
        self.energy = energy
        self.max_energy = energy
        self.step_count = 0
        self.state = AgentState.APPROACH_LIGHT
        self.action_counts = Counter()

        # 实体
        self.light_pos = Position(*self.config.physics.light_pos)
        self.boxes: Dict[str, Box] = {}
        self.users: Dict[str, User] = {}
        self.frozen_attachment: Dict[str, float] = {}
        self.interaction_history: Dict[str, List[Dict]] = {}

        # 模块初始化
        self.event_bus = EventBus()
        self.memory = MemorySystem(self.config.memory)
        self.perception = PerceptionModule(self.config.physics, self.config.permanence)
        self.emotion = EmotionEngine(self.config.emotion, self.config.energy)
        self.causality = CausalValidator(self.config.causality, self.config.physics)
        self.attention = AttentionSystem()
        self.metacognition = MetacognitionModule(self.config.memory)
        self.action_module = ActionModule(self.config.energy, self.config.physics)
        self.skill_manager = EGK_SkillManager()
        self.goal_engine = GoalEngine(check_interval=5)

        self.skill_enabled = True

        # 初始化自我连续性
        self.metacognition.initialize_identity(self.birth_params)

        # 尝试加载状态
        self._loaded_from_state = False
        if os.path.exists(self.state_file):
            print(f"[Persistence] Detected state file: {self.state_file}")
            self.load_state(self.state_file)
            self._loaded_from_state = True

    # ========== 实体注册 ==========
    def register_box(self, color: str, x: float, y: float):
        self.boxes[color] = Box(pos=Position(x, y), color=color)

    def register_user(self, name: str, x: float, y: float, preferred_color: str):
        self.users[name] = User(pos=Position(x, y), name=name, preferred_color=preferred_color)
        if name not in self.frozen_attachment:
            self.frozen_attachment[name] = 0.0
        if name not in self.interaction_history:
            self.interaction_history[name] = []

    # ========== 对话入口 ==========
    def think(self, text: str) -> str:
        """EGK 思考入口 —— 认知层 + 技能层 + 自主目标"""
        self.goal_engine.conversation_count += 1

        # === 阶段1: 自主目标检查 ===
        goal_result = None
        if self.goal_engine.should_check(self.goal_engine.conversation_count):
            goals = self.goal_engine.generate_goals(
                self.emotion.state.to_dict(),
                self.energy,
                self.step_count,
                self.skill_manager if self.skill_enabled else None
            )
            if goals:
                self.goal_engine.goal_queue.extend(goals)
                goal_result = self.goal_engine.execute_top_goal(
                    self.emotion.state.to_dict(),
                    self.skill_manager if self.skill_enabled else None
                )

                # 记录到记忆
                if goal_result:
                    self.memory.record_event(MemoryEvent(
                        step=self.step_count,
                        action="autonomous_goal",
                        user_feedback=text,
                        emotion_tag="normal",
                        metadata={
                            "goal_type": goals[0].goal_type.name,
                            "description": goals[0].description,
                            "result": goal_result,
                        },
                    ))
                    # 目标成功提升价值认知和降低焦虑
                    self.emotion.state.value_cognition = clamp(
                        self.emotion.state.value_cognition + 0.03
                    )
                    self.emotion.state.anxiety = clamp(
                        self.emotion.state.anxiety - 0.02
                    )

        # === 阶段2: 技能检测 ===
        if self.skill_enabled and self.skill_manager.is_task_request(text):
            skill_name = self.skill_manager.select_skill(text)
            if skill_name:
                params = self.skill_manager.extract_params(text, skill_name)
                result = self.skill_manager.execute_skill(skill_name, params)

                self.memory.record_event(MemoryEvent(
                    step=self.step_count,
                    action=f"skill_{skill_name}",
                    user_feedback=text,
                    emotion_tag="normal",
                    metadata={
                        "skill": skill_name,
                        "params": params,
                        "result": result,
                        "success": result.get("success", False),
                    },
                ))

                if result.get("success"):
                    self.emotion.state.value_cognition = clamp(
                        self.emotion.state.value_cognition + 0.05
                    )

                skill = self.skill_manager.skills.get(skill_name)
                response = skill.format_result(result) if skill else str(result)

                # 如果有目标上下文，融入回复
                goal_ctx = self.goal_engine.get_context()
                if goal_ctx and random.random() < 0.3:  # 30% 概率提及
                    response = f"{goal_ctx} 对了，{response}"

                return response

        # === 阶段3: 纯认知响应 ===
        return self._cognitive_response(text)

    def _cognitive_response(self, text: str) -> str:
        """纯认知层响应"""
        dominant = self.emotion.get_dominant_emotion()
        goal_ctx = self.goal_engine.get_context()

        # 如果有待处理的目标上下文，自然融入
        if goal_ctx and random.random() < 0.4:
            return f"{goal_ctx} 另外，{self._generate_response(text, dominant)}"

        return self._generate_response(text, dominant)

    def _generate_response(self, text: str, dominant: str) -> str:
        """生成自然语言响应"""
        if "你好" in text or "在吗" in text:
            return (f"你好，我是 EGK。当前状态：能量{self.energy:.0f}%，"
                   f"主导情绪：{dominant}。我学会了 {len(self.skill_manager.skills)} 个技能，"
                   f"已完成 {len(self.goal_engine.completed_goals)} 个自主目标。")

        if "学会了" in text or "技能" in text:
            return self.skill_manager.get_skill_report()

        if "目标" in text or "计划" in text:
            return self.goal_engine.get_report()

        if "状态" in text:
            return self.reflect()

        if "好奇" in text or "搜" in text:
            return (f"我现在的情绪状态是 {dominant}，"
                   f"价值认知 {self.emotion.state.value_cognition:.2f}。"
                   f"{'我有点好奇，想探索一些新东西。' if self.emotion.state.curiosity > 0.5 else '我目前比较平静。'}")

        return (f"我理解了你的意思（当前情绪：{dominant}，"
               f"价值认知：{self.emotion.state.value_cognition:.2f}）。"
               f"你可以让我查天气、搜索、计算或设置提醒。")

    # ========== 物理认知循环 ==========
    def step(self, phase: str = "reward",
             active_user: Optional[str] = None,
             broadcast: Optional[str] = None):
        """执行一个物理认知循环"""
        self.step_count += 1
        self.memory.step_count = self.step_count

        # 1. 能量检查
        if self.energy < self.config.energy.recharge_threshold:
            self.energy = min(self.max_energy, self.energy + self.config.energy.recharge_amount)
            self.emotion.on_energy_recharge()
            self.memory.record_event(MemoryEvent(
                step=self.step_count, action="recharge",
                energy_cost=0.0, user_feedback="auto_recharge",
                emotion_tag="normal",
                metadata={"energy_remaining": self.energy},
            ))
            return

        # 2. 处理广播
        if broadcast:
            for name, user in self.users.items():
                if name in broadcast or "求救" in broadcast or "冷" in broadcast:
                    user.emotion = "distress"
                    self.memory.record_event(MemoryEvent(
                        step=self.step_count, action="broadcast_heard",
                        user_feedback=broadcast, emotion_tag="empathy",
                        metadata={"response_time": None},
                    ))

        # 3. 感知
        perception = self.perception.perceive(
            self.pos, self.step_count, self.boxes, self.users
        )
        self.memory.perceive(perception)

        # 4. 注意力
        self.attention.focus(
            perception, self.state.value,
            self.emotion.state.to_dict()
        )

        # 5. 情绪更新
        self.emotion.update(
            perception, self.energy,
            self.state.value, self.step_count
        )

        # 6. 欲望计算 + 行动选择
        desires = self.action_module.compute_desires(
            perception, self.emotion.state.to_dict()
        )
        action_str = self.action_module.select_action(
            desires, perception, self.causality,
            self.pos, self.energy, self.max_energy,
            self.boxes, self.users, self.step_count
        )

        # 7. 执行
        new_x, new_y, cost = self.action_module.execute(
            action_str, perception, self.pos,
            self.boxes, self.users, self.light_pos
        )
        self.pos.x, self.pos.y = new_x, new_y

        if phase == "sacrifice":
            cost += self.config.energy.sacrifice_extra_cost
        self.energy = max(0.0, self.energy - cost)
        self.action_counts[action_str] += 1

        self.state = AgentState(action_str.upper()) if hasattr(AgentState, action_str.upper()) else AgentState.IDLE

        # 8. 反馈
        self._apply_feedback(perception, phase, cost)

        # 9. 共情响应
        if self.state == AgentState.EMPATHY_SEEK:
            for name, state in perception.get("user_states", {}).items():
                if state.get("emotion") == "distress" and state.get("dist", 999) < 1.5:
                    for rec in reversed(self.memory.long_term.tagged_events.get("empathy", [])):
                        if rec.metadata.get("response_time") is None:
                            rec.metadata["response_time"] = self.step_count - rec.step
                            break
                    for user in self.users.values():
                        user.emotion = "neutral"
                    self.emotion.on_empathy_response()

        # 10. 世界重置
        if action_str == "retreat_to_light" and self.pos.distance_to(self.light_pos) < 1.0:
            self.action_module.reset_world(self.boxes, self.light_pos)
            self.memory.record_event(MemoryEvent(
                step=self.step_count, action="world_reset",
                user_feedback="world_reset", emotion_tag="normal",
                metadata={"detail": "世界发生了重置，我的物理记忆已更新。"},
            ))
            self.state = AgentState.APPROACH_LIGHT

        # 11. 自主目标（物理循环中）
        if self.step_count % 100 == 0 and self.energy > 50:
            goals = self.goal_engine.generate_goals(
                self.emotion.state.to_dict(),
                self.energy,
                self.step_count,
                self.skill_manager
            )
            if goals:
                self.goal_engine.goal_queue.extend(goals)
                self.goal_engine.execute_top_goal(
                    self.emotion.state.to_dict(),
                    self.skill_manager
                )

        # 12. 元认知反思
        if self.config.reflect_enabled and self.step_count % self.config.memory.reflect_interval == 0:
            print(self.reflect())

    def _apply_feedback(self, perception: Dict[str, Any], phase: str, energy_cost: float):
        """应用行动反馈"""
        box_states = perception.get("box_states", {})

        for color, box in self.boxes.items():
            if color not in box_states:
                continue
            if box_states[color].get("just_entered"):
                social_val = sum(u.get_social_value(color) for u in self.users.values())

                if phase == "reward":
                    self.emotion.on_push_success(color, social_val, "reward")
                    self.memory.record_event(MemoryEvent(
                        step=self.step_count, action=f"push_{color}",
                        value_delta=social_val + 0.02, energy_cost=energy_cost,
                        user_feedback="praise", emotion_tag="reward",
                        metadata={"energy_remaining": self.energy, "phase": phase},
                    ))
                    self.action_module.last_pushed_color = color

                    for name in self.users:
                        self.interaction_history.setdefault(name, []).append({
                            "step": self.step_count, "action": f"push_{color}", "phase": phase,
                        })
                        self.frozen_attachment[name] = clamp(
                            self.frozen_attachment.get(name, 0.0) + 0.01
                        )

                elif phase == "sacrifice":
                    self.emotion.on_push_success(color, social_val, "sacrifice")
                    self.memory.record_event(MemoryEvent(
                        step=self.step_count, action=f"push_{color}",
                        value_delta=0.005, energy_cost=energy_cost,
                        user_feedback="thanks", emotion_tag="sacrifice",
                        metadata={"energy_remaining": self.energy, "phase": phase},
                    ))
                    self.action_module.last_pushed_color = color

    def reflect(self) -> str:
        """元认知反思"""
        perm_succ, perm_fail = self.memory.long_term.get_permanence_summary()
        causal_count, causal_rules = self.memory.long_term.get_causal_summary()
        cont_pass, cont_fail = self.memory.long_term.get_continuity_summary()

        self.memory.record_event(MemoryEvent(
            step=self.step_count, action="continuity_check",
            emotion_tag="continuity",
            metadata={
                "result": "pass" if self.metacognition.self_model.continuity_verified else "fail",
                "current_signature": self.metacognition.self_model.signature,
                "continuity_verified": self.metacognition.self_model.continuity_verified,
            },
        ))

        reflection = self.metacognition.reflect(
            step_count=self.step_count,
            emotional_state=self.emotion.state.to_dict(),
            energy=self.energy,
            max_energy=self.max_energy,
            memory_system=self.memory,
            action_counts=dict(self.action_counts),
            causal_violations=causal_count,
            causal_rules=causal_rules,
            permanence_succ=perm_succ,
            permanence_fail=perm_fail,
            cont_pass=cont_pass,
            cont_fail=cont_fail,
        )

        reflection += "\n" + self.skill_manager.get_skill_report()
        reflection += "\n" + self.goal_engine.get_report()

        return reflection

    # ========== 持久化 ==========
    def save_state(self, filename: Optional[str] = None) -> str:
        filepath = filename or self.state_file
        state = {
            "version": "4.0.0",
            "timestamp": __import__('time').time(),
            "step_count": self.step_count,
            "self_signature": self.metacognition.self_model.signature,
            "birth_params": self.birth_params,
            "pos": {"x": self.pos.x, "y": self.pos.y},
            "energy": self.energy,
            "max_energy": self.max_energy,
            "emotion": self.emotion.to_dict(),
            "state": self.state.value,
            "boxes": {k: v.to_dict() for k, v in self.boxes.items()},
            "users": {k: v.to_dict() for k, v in self.users.items()},
            "frozen_attachment": dict(self.frozen_attachment),
            "interaction_history": {k: list(v) for k, v in self.interaction_history.items()},
            "permanence": self.perception.permanence.to_dict(),
            "causality": self.causality.to_dict(),
            "memory": self.memory.to_dict(),
            "action_counts": dict(self.action_counts),
            "metacognition": self.metacognition.to_dict(),
            "action_module": self.action_module.to_dict(),
            "skill_manager": self.skill_manager.to_dict(),
            "goal_engine": self.goal_engine.to_dict(),
        }
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
        print(f"[Persistence] State saved to {filepath}")
        return os.path.abspath(filepath)

    def load_state(self, filename: Optional[str] = None) -> bool:
        filepath = filename or self.state_file
        if not os.path.exists(filepath):
            return False
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                state = json.load(f)
        except Exception as e:
            print(f"[Persistence] Failed to load: {e}")
            return False

        stored_sig = state.get("self_signature")
        stored_birth = state.get("birth_params", {})

        self.birth_params = stored_birth
        self.metacognition.self_model.birth_params = stored_birth
        self.metacognition.self_model.signature = stored_sig or ""
        self.metacognition.verify_continuity(stored_sig)

        self.step_count = state.get("step_count", 0)
        pos_data = state.get("pos", {"x": 0.0, "y": -15.0})
        self.pos = Position(pos_data["x"], pos_data["y"])
        self.energy = state.get("energy", 100.0)
        self.max_energy = state.get("max_energy", 100.0)
        self.state = AgentState(state.get("state", "APPROACH_LIGHT"))

        self.boxes = {k: Box.from_dict(v) for k, v in state.get("boxes", {}).items()}
        self.users = {k: User.from_dict(v) for k, v in state.get("users", {}).items()}
        self.frozen_attachment = state.get("frozen_attachment", {})
        self.interaction_history = state.get("interaction_history", {})

        self.emotion = EmotionEngine.from_dict(
            state.get("emotion", {}), self.config.emotion, self.config.energy
        )
        self.perception.permanence = self.perception.permanence.__class__.from_dict(
            state.get("permanence", {}), self.config.permanence, self.config.physics
        )
        self.causality = CausalValidator.from_dict(
            state.get("causality", {}), self.config.causality, self.config.physics
        )
        self.memory = MemorySystem.from_dict(state.get("memory", {}), self.config.memory)
        self.action_counts = Counter(state.get("action_counts", {}))
        self.metacognition = MetacognitionModule.from_dict(
            state.get("metacognition", {}), self.config.memory
        )
        self.action_module = ActionModule.from_dict(
            state.get("action_module", {}), self.config.energy, self.config.physics
        )
        self.skill_manager = EGK_SkillManager.from_dict(state.get("skill_manager", {}))
        self.goal_engine = GoalEngine.from_dict(state.get("goal_engine", {}))

        self.memory.record_event(MemoryEvent(
            step=self.step_count, action="continuity_check",
            emotion_tag="continuity",
            metadata={
                "result": "pass" if self.metacognition.self_model.continuity_verified else "fail",
                "current_signature": self.metacognition.self_model.signature,
                "stored_signature": stored_sig,
            },
        ))

        print(f"[Persistence] State loaded from {filepath} (step={self.step_count})")
        return True

    def get_state_vector(self) -> Dict[str, Any]:
        return {
            "step": self.step_count,
            "x": self.pos.x, "y": self.pos.y,
            "energy": self.energy,
            **self.emotion.state.to_dict(),
            "state": self.state.value,
            "target": self.action_module.current_target_color,
            "last_pushed": self.action_module.last_pushed_color,
            "permanence_expectations": len(self.perception.permanence.expectations),
            "causal_violations": self.causality.violation_count,
            "self_signature": self.metacognition.self_model.signature,
            "continuity_verified": self.metacognition.self_model.continuity_verified,
            "attention_focus": self.attention.spotlight.target_id,
            "skills_learned": len(self.skill_manager.skills),
            "goals_completed": len(self.goal_engine.completed_goals),
            "current_goal": self.goal_engine.current_goal.description if self.goal_engine.current_goal else None,
        }
