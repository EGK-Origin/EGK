"""EGK v4 工具函数"""
from __future__ import annotations
import hashlib
import json
import math
import random
from typing import Dict, Any, Tuple, Optional


def generate_signature(birth_params: Dict[str, Any]) -> str:
    """基于出生参数生成自我签名"""
    sig_str = json.dumps(birth_params, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(sig_str.encode("utf-8")).hexdigest()[:32]


def clamp(value: float, min_val: float = 0.0, max_val: float = 1.0) -> float:
    """限制值在范围内"""
    return max(min_val, min(max_val, value))


def sigmoid(x: float, k: float = 10.0, x0: float = 0.5) -> float:
    """Sigmoid 函数"""
    return 1.0 / (1.0 + math.exp(-k * (x - x0)))


def noisy_value(value: float, noise_range: float = 0.02) -> float:
    """添加随机噪声"""
    return value + random.uniform(-noise_range, noise_range)


def weighted_choice(options: Dict[str, float]) -> str:
    """基于权重的随机选择"""
    if not options:
        return ""
    total = sum(max(0, v) for v in options.values())
    if total <= 0:
        return random.choice(list(options.keys()))
    r = random.uniform(0, total)
    cumulative = 0.0
    for key, weight in options.items():
        cumulative += max(0, weight)
        if r <= cumulative:
            return key
    return list(options.keys())[-1]


def format_time(psychological_hours: int) -> str:
    """格式化心理时间"""
    days = psychological_hours // 24
    hours = psychological_hours % 24
    if days > 0:
        return f"{days}d {hours}h"
    return f"{hours}h"
