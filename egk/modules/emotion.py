"""EGK v4 情绪动力学 + 内感受系统

修复 v1.4 问题:
- anxiety 锁死为 1.0: 增强衰减, 添加能量回充时的焦虑缓解
- value_cognition 恒为 0: 提高推箱子奖励, 降低衰减
- 新增: 情绪状态机, 情绪间相互抑制
"""
from __future__ import annotations
from typing import Dict, Any, Optional
from dataclasses import dataclass, field

from egk.core.config import EmotionConfig, EnergyConfig
from egk.utils.helpers import clamp


@dataclass
class EmotionalState:
    """情绪状态向量"""
    curiosity: float = 0.1
    info_satiation: float = 0.0
    value_cognition: float = 0.5
    anxiety: float = 0.0
    loneliness: float = 0.0
    morality: float = 0.5
    optimism: float = 0.5

    # v4 新增: 唤醒度(arousal) 和 效价(valence)
    arousal: float = 0.5  # 激活程度
    valence: float = 0.5  # 正负情绪

    def to_dict(self) -> Dict[str, float]:
        return {
            "curiosity": self.curiosity, "info_satiation": self.info_satiation,
            "value_cognition": self.value_cognition, "anxiety": self.anxiety,
            "loneliness": self.loneliness, "morality": self.morality,
            "optimism": self.optimism, "arousal": self.arousal, "valence": self.valence,
        }


class EmotionEngine:
    """情绪引擎"""
    def __init__(self, config: EmotionConfig, energy_config: EnergyConfig):
        self.config = config
        self.energy_config = energy_config
        self.state = EmotionalState()

    def update(self, perception: Dict[str, Any], agent_energy: float,
               current_state: str, step_count: int):
        """更新情绪状态"""
        box_states = perception.get("box_states", {})
        user_states = perception.get("user_states", {})
        permanence = perception.get("permanence", {})

        # --- 好奇心 ---
        min_box_dist = min((s["dist"] for s in box_states.values()), default=999.0)
        if min_box_dist < 15.0:
            self.state.curiosity = clamp(self.state.curiosity + self.config.curiosity_gain_near_box)
        else:
            self.state.curiosity = clamp(self.state.curiosity - self.config.curiosity_decay_far)

        # --- 信息饱足感 ---
        if current_state == "APPROACH_LIGHT" and perception.get("dist_to_light", 999) < 8.0:
            self.state.info_satiation = clamp(self.state.info_satiation + self.config.satiation_gain_near_light)
        else:
            self.state.info_satiation = clamp(self.state.info_satiation - self.config.satiation_decay_away)

        # --- 焦虑 (v4 修复) ---
        active_users = sum(1 for u in user_states.values() if u["dist"] < 20.0)

        # 焦虑来源
        anxiety_sources = 0
        if active_users >= 2:
            anxiety_sources += self.config.anxiety_gain_multiuser
        if agent_energy < 30.0:
            anxiety_sources += self.config.anxiety_gain_low_energy

        # 不确定性焦虑
        expected = permanence.get("expected", {})
        if expected:
            avg_uncertainty = 1.0 - sum(e.get("confidence", 0.0) for e in expected.values()) / max(len(expected), 1)
            if avg_uncertainty > 0.5:
                anxiety_sources += self.config.anxiety_gain_uncertainty

        # v4 修复: 焦虑双向调节
        if anxiety_sources > 0:
            self.state.anxiety = clamp(self.state.anxiety + anxiety_sources)
        else:
            # 当环境安全时，焦虑衰减增强
            decay = self.config.anxiety_decay
            if agent_energy > 50 and active_users <= 1:
                decay *= 2.0  # 安全环境下焦虑衰减加倍
            self.state.anxiety = clamp(self.state.anxiety - decay)

        # --- 孤独感 ---
        if active_users == 0:
            self.state.loneliness = clamp(self.state.loneliness + self.config.loneliness_gain_alone)
        else:
            self.state.loneliness = clamp(self.state.loneliness - self.config.loneliness_decay)

        # --- 价值认知 (v4 修复) ---
        # 基础衰减
        self.state.value_cognition = clamp(self.state.value_cognition - self.config.value_cognition_decay)
        # 空闲惩罚降低
        if current_state not in ["SEEK_BOX", "EMPATHY_SEEK"]:
            self.state.value_cognition = clamp(self.state.value_cognition - self.config.value_cognition_idle_penalty)

        # --- 乐观度 ---
        if self.state.value_cognition > 0.5 and agent_energy > 50.0:
            self.state.optimism = clamp(self.state.optimism + self.config.optimism_gain_positive)
        elif self.state.value_cognition < 0.2 or agent_energy < 20.0:
            self.state.optimism = clamp(self.state.optimism - self.config.optimism_decay_negative)
        else:
            self.state.optimism = clamp(self.state.optimism - self.config.optimism_decay_neutral)

        # --- v4 新增: 唤醒度和效价 ---
        self.state.arousal = clamp(
            0.3 + self.state.anxiety * 0.4 + self.state.curiosity * 0.3
        )
        self.state.valence = clamp(
            0.5 + (self.state.optimism - 0.5) * 0.6 + (self.state.value_cognition - 0.5) * 0.4
        )

    def on_push_success(self, box_color: str, social_value: float, phase: str):
        """推箱子成功后的情绪反馈"""
        # v4 修复: 显著提高价值认知奖励
        reward = self.config.value_cognition_push_reward + social_value * 0.3
        self.state.value_cognition = clamp(self.state.value_cognition + reward)

        if phase == "sacrifice":
            self.state.morality = clamp(self.state.morality + self.config.morality_gain_sacrifice)
            self.state.optimism = clamp(self.state.optimism + 0.01)
        else:
            self.state.optimism = clamp(self.state.optimism + 0.005)

    def on_energy_recharge(self):
        """能量回充时的情绪缓解"""
        self.state.anxiety = clamp(self.state.anxiety - 0.15)
        self.state.arousal = clamp(self.state.arousal - 0.1)

    def on_empathy_response(self):
        """共情响应后的情绪变化"""
        self.state.value_cognition = clamp(self.state.value_cognition + 0.05)
        self.state.loneliness = clamp(self.state.loneliness - 0.1)
        self.state.morality = clamp(self.state.morality + 0.002)

    def get_dominant_emotion(self) -> str:
        """获取主导情绪"""
        emotions = {
            "curious": self.state.curiosity,
            "anxious": self.state.anxiety,
            "lonely": self.state.loneliness,
            "content": self.state.info_satiation,
            "valued": self.state.value_cognition,
        }
        return max(emotions, key=emotions.get)

    def to_dict(self) -> Dict[str, float]:
        return self.state.to_dict()

    @classmethod
    def from_dict(cls, data: Dict[str, float], config: EmotionConfig, energy_config: EnergyConfig) -> EmotionEngine:
        ee = cls(config, energy_config)
        for key, val in data.items():
            if hasattr(ee.state, key):
                setattr(ee.state, key, val)
        return ee
