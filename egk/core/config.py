"""EGK v4 配置系统 —— 解决 v1.4 硬编码常量问题"""
from dataclasses import dataclass, field
from typing import Tuple, Dict


@dataclass
class PhysicsConfig:
    """物理世界参数"""
    time_scale: int = 60                    # 步数/小时
    light_pos: Tuple[float, float] = (0.0, 0.0)
    zone_radius: float = 5.0
    perception_range: float = 20.0
    max_position_jump: float = 1.0          # 因果: 最大位置跳跃
    overlap_tolerance: float = 0.1          # 因果: 重叠容差


@dataclass
class EnergyConfig:
    """能量系统参数 —— 修复 v1.4 能量不真实问题"""
    max_energy: float = 100.0
    recharge_threshold: float = 10.0
    recharge_amount: float = 30.0
    # v4 新增: 每步基础代谢消耗
    metabolic_cost_per_step: float = 0.15
    # v4 新增: 移动消耗系数
    movement_cost_factor: float = 0.05
    # v4 新增: 推箱子消耗
    push_cost: float = 2.0
    # 牺牲阶段额外消耗
    sacrifice_extra_cost: float = 8.0


@dataclass
class EmotionConfig:
    """情绪动力学参数 —— 修复 v1.4 情绪锁死问题"""
    curiosity_gain_near_box: float = 0.02
    curiosity_decay_far: float = 0.005
    satiation_gain_near_light: float = 0.01
    satiation_decay_away: float = 0.02
    # v4 修复: 焦虑衰减增强，避免锁死
    anxiety_gain_multiuser: float = 0.005
    anxiety_gain_low_energy: float = 0.01
    anxiety_decay: float = 0.008            # v1.4: 0.003 → v4: 0.008
    anxiety_gain_uncertainty: float = 0.003
    # v4 修复: 价值认知衰减降低，增益提高
    value_cognition_decay: float = 0.0008   # v1.4: 0.002 → v4: 0.0008
    value_cognition_idle_penalty: float = 0.003  # v1.4: 0.008 → v4: 0.003
    value_cognition_push_reward: float = 0.08    # v4 新增: 推箱子直接奖励
    loneliness_decay: float = 0.002
    loneliness_gain_alone: float = 0.005
    morality_gain_sacrifice: float = 0.001
    morality_decay: float = 0.0005
    optimism_gain_positive: float = 0.002
    optimism_decay_negative: float = 0.003
    optimism_decay_neutral: float = 0.001


@dataclass
class PermanenceConfig:
    """对象恒存性参数"""
    uncertainty_decay_rate: float = 0.05
    uncertainty_recovery_rate: float = 0.15
    confidence_threshold: float = 0.3
    prediction_success_bonus: float = 0.2
    prediction_success_radius: float = 3.0


@dataclass
class CausalityConfig:
    """因果验证参数"""
    violation_penalty: float = 0.20
    conflict_threshold: int = 3


@dataclass
class MemoryConfig:
    """记忆系统参数"""
    buffer_maxlen: int = 5000
    reflect_interval: int = 500
    # v4 新增: 工作记忆容量
    working_memory_capacity: int = 7


@dataclass
class PersonalityConfig:
    """人格基线参数"""
    stability: float = 0.5
    openness: float = 0.5
    conscientiousness: float = 0.5
    extraversion: float = 0.5
    optimism: float = 0.5


@dataclass
class EGKConfig:
    """EGK v4 总配置"""
    physics: PhysicsConfig = field(default_factory=PhysicsConfig)
    energy: EnergyConfig = field(default_factory=EnergyConfig)
    emotion: EmotionConfig = field(default_factory=EmotionConfig)
    permanence: PermanenceConfig = field(default_factory=PermanenceConfig)
    causality: CausalityConfig = field(default_factory=CausalityConfig)
    memory: MemoryConfig = field(default_factory=MemoryConfig)
    personality: PersonalityConfig = field(default_factory=PersonalityConfig)
    # v4 新增: 默认状态文件
    state_file: str = "egk_state.json"
    # v4 新增: 是否启用元认知反思
    reflect_enabled: bool = True
    # v4 新增: 是否启用因果验证
    causality_enabled: bool = True
    # v4 新增: 是否启用对象恒存性
    permanence_enabled: bool = True
