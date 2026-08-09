"""EGK v4 技能系统 —— 从"认知存在"升级为"行动存在"

核心架构: 注册-调用-反馈闭环
- EGK_Skill: 技能基类
- EGK_SkillManager: 技能注册/选择/执行/学习
- 具体技能: 天气查询、网页搜索、计算器等
"""
from __future__ import annotations
import re
import json
import time
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, field

from egk.utils.helpers import clamp


# ==================== 技能基类 ====================
class EGK_Skill(ABC):
    """所有技能的抽象基类"""
    name: str = ""
    description: str = ""
    required_params: List[str] = []
    category: str = "general"  # general, search, calculation, creative

    @abstractmethod
    def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """执行技能，返回结构化结果"""
        pass

    @abstractmethod
    def validate(self, params: Dict[str, Any]) -> bool:
        """验证参数是否合法"""
        pass

    def format_result(self, result: Dict[str, Any]) -> str:
        """将结果格式化为自然语言"""
        if "error" in result:
            return f"执行失败：{result['error']}"
        return json.dumps(result, ensure_ascii=False, indent=2)


# ==================== 具体技能实现 ====================
class WeatherSkill(EGK_Skill):
    """天气查询技能"""
    name = "查询天气"
    description = "查询指定城市的实时天气信息"
    required_params = ["city"]
    category = "search"

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key

    def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        city = params.get("city", "北京")
        try:
            # 模拟天气数据（实际使用时接入真实API）
            import random
            conditions = ["晴", "多云", "阴", "小雨", "雷阵雨"]
            condition = random.choice(conditions)
            temp = random.uniform(15.0, 35.0)
            humidity = random.uniform(30.0, 90.0)
            wind = random.uniform(1.0, 6.0)

            return {
                "city": city,
                "temperature": round(temp, 1),
                "condition": condition,
                "humidity": round(humidity, 1),
                "wind_speed": round(wind, 1),
                "suggestion": self._get_suggestion(condition, temp),
                "success": True,
            }
        except Exception as e:
            return {"error": str(e), "success": False}

    def validate(self, params: Dict[str, Any]) -> bool:
        return "city" in params and len(str(params["city"])) > 0

    def format_result(self, result: Dict[str, Any]) -> str:
        if "error" in result:
            return f"抱歉，天气查询失败：{result['error']}"
        return (f"{result['city']} 当前天气：{result['condition']}，"
                f"温度 {result['temperature']}°C，"
                f"湿度 {result['humidity']}%，"
                f"风速 {result['wind_speed']}级。"
                f"建议：{result['suggestion']}")

    def _get_suggestion(self, condition: str, temp: float) -> str:
        if temp > 30:
            return "天气炎热，注意防暑降温"
        elif temp < 10:
            return "天气寒冷，注意保暖"
        elif "雨" in condition:
            return "有雨，记得带伞"
        return "天气适宜，适合外出"


class WebSearchSkill(EGK_Skill):
    """网页搜索技能"""
    name = "网页搜索"
    description = "搜索互联网信息，获取摘要和链接"
    required_params = ["query"]
    category = "search"

    def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        query = params.get("query", "")
        try:
            # 模拟搜索结果
            return {
                "query": query,
                "abstract": f"关于「{query}」的搜索结果："
                           f"具身智能（Embodied AI）是指拥有物理身体并能通过身体与环境交互的智能体。"
                           f"它强调智能不能脱离身体而存在，认知、感知和行动是统一的整体。",
                "sources": [
                    {"title": "具身智能综述", "url": "https://example.com/embodied-ai"},
                    {"title": "EGK 认知架构", "url": "https://example.com/egk"},
                ],
                "success": True,
            }
        except Exception as e:
            return {"error": str(e), "success": False}

    def validate(self, params: Dict[str, Any]) -> bool:
        return "query" in params and len(str(params["query"])) > 0

    def format_result(self, result: Dict[str, Any]) -> str:
        if "error" in result:
            return f"搜索失败：{result['error']}"
        sources = "\n".join([f"  - {s['title']}: {s['url']}" for s in result.get("sources", [])])
        return f"搜索「{result['query']}」结果：\n{result['abstract'][:120]}...\n参考来源：\n{sources}"


class CalculatorSkill(EGK_Skill):
    """计算器技能"""
    name = "计算"
    description = "执行数学计算"
    required_params = ["expression"]
    category = "calculation"

    def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        expression = params.get("expression", "")
        try:
            # 安全计算：只允许基本运算符
            allowed = set("0123456789+-*/.() ")
            if not all(c in allowed for c in expression):
                return {"error": "表达式包含非法字符", "success": False}
            result = eval(expression)
            return {
                "expression": expression,
                "result": result,
                "success": True,
            }
        except Exception as e:
            return {"error": f"计算错误: {e}", "success": False}

    def validate(self, params: Dict[str, Any]) -> bool:
        return "expression" in params and len(str(params["expression"])) > 0

    def format_result(self, result: Dict[str, Any]) -> str:
        if "error" in result:
            return f"计算失败：{result['error']}"
        return f"{result['expression']} = {result['result']}"


class ReminderSkill(EGK_Skill):
    """提醒技能"""
    name = "设置提醒"
    description = "设置定时提醒"
    required_params = ["content"]
    category = "general"

    def __init__(self):
        self.reminders: List[Dict[str, Any]] = []

    def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        content = params.get("content", "")
        delay = params.get("delay_seconds", 60)
        try:
            reminder = {
                "content": content,
                "created_at": time.time(),
                "trigger_at": time.time() + delay,
                "triggered": False,
            }
            self.reminders.append(reminder)
            return {
                "content": content,
                "delay_seconds": delay,
                "trigger_time": reminder["trigger_at"],
                "total_reminders": len(self.reminders),
                "success": True,
            }
        except Exception as e:
            return {"error": str(e), "success": False}

    def validate(self, params: Dict[str, Any]) -> bool:
        return "content" in params and len(str(params["content"])) > 0

    def format_result(self, result: Dict[str, Any]) -> str:
        if "error" in result:
            return f"设置提醒失败：{result['error']}"
        minutes = result["delay_seconds"] // 60
        return f"已设置提醒「{result['content']}」，将在 {minutes} 分钟后触发。"

    def check_reminders(self) -> List[str]:
        """检查是否有到期的提醒"""
        now = time.time()
        triggered = []
        for r in self.reminders:
            if not r["triggered"] and now >= r["trigger_at"]:
                r["triggered"] = True
                triggered.append(r["content"])
        return triggered


class EchoSkill(EGK_Skill):
    """回声技能 —— 测试用"""
    name = "回声"
    description = "重复用户输入的内容"
    required_params = ["text"]
    category = "general"

    def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "text": params.get("text", ""),
            "echo": f"你说的是：{params.get('text', '')}",
            "success": True,
        }

    def validate(self, params: Dict[str, Any]) -> bool:
        return "text" in params

    def format_result(self, result: Dict[str, Any]) -> str:
        return result["echo"]


# ==================== 技能管理器 ====================
@dataclass
class SkillUsage:
    """技能使用统计"""
    success_count: int = 0
    fail_count: int = 0
    total_time: float = 0.0
    last_used: float = 0.0
    preference: float = 0.5  # 0-1, 越高越偏好

    @property
    def total_count(self) -> int:
        return self.success_count + self.fail_count

    @property
    def success_rate(self) -> float:
        if self.total_count == 0:
            return 0.5
        return self.success_count / self.total_count

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success_count": self.success_count,
            "fail_count": self.fail_count,
            "total_time": self.total_time,
            "last_used": self.last_used,
            "preference": self.preference,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> SkillUsage:
        su = cls()
        su.success_count = data.get("success_count", 0)
        su.fail_count = data.get("fail_count", 0)
        su.total_time = data.get("total_time", 0.0)
        su.last_used = data.get("last_used", 0.0)
        su.preference = data.get("preference", 0.5)
        return su


class EGK_SkillManager:
    """技能管理器 —— 注册、选择、执行、学习"""

    # 任务检测关键词
    TASK_KEYWORDS = ["查", "搜", "帮我", "做", "写", "生成", "设计", "计算", "算", "提醒", "搜索"]

    def __init__(self):
        self.skills: Dict[str, EGK_Skill] = {}
        self.usage_stats: Dict[str, SkillUsage] = {}
        self.recent_results: List[Dict[str, Any]] = []
        self.history_limit: int = 100

        # 注册默认技能
        self._register_defaults()

    def _register_defaults(self):
        """注册默认技能集"""
        defaults = [
            WeatherSkill(),
            WebSearchSkill(),
            CalculatorSkill(),
            ReminderSkill(),
            EchoSkill(),
        ]
        for skill in defaults:
            self.register_skill(skill)

    def register_skill(self, skill: EGK_Skill):
        """注册一个新技能"""
        self.skills[skill.name] = skill
        if skill.name not in self.usage_stats:
            self.usage_stats[skill.name] = SkillUsage()
        print(f"[SkillManager] Registered: {skill.name} ({skill.description})")

    def unregister_skill(self, skill_name: str):
        """注销技能"""
        if skill_name in self.skills:
            del self.skills[skill_name]
            del self.usage_stats[skill_name]

    def is_task_request(self, text: str) -> bool:
        """检测文本是否为任务请求"""
        return any(kw in text for kw in self.TASK_KEYWORDS)

    def select_skill(self, task_description: str) -> Optional[str]:
        """根据任务描述选择最合适的技能（含偏好加权）"""
        task_lower = task_description.lower()

        # 关键词匹配 + 偏好加权
        scores: Dict[str, float] = {}
        for name, skill in self.skills.items():
            score = 0.0
            # 描述匹配
            desc_words = skill.description.lower().split()
            for word in task_lower.split():
                if word in desc_words or word in skill.name.lower():
                    score += 1.0
            # 类别匹配
            if skill.category in task_lower:
                score += 0.5
            # 偏好加权
            pref = self.usage_stats[name].preference
            score *= (0.5 + pref)  # 偏好高的技能得分加成

            if score > 0:
                scores[name] = score

        if not scores:
            return None

        return max(scores, key=scores.get)

    def extract_params(self, text: str, skill_name: str) -> Dict[str, Any]:
        """从文本中提取技能参数"""
        params = {}
        skill = self.skills.get(skill_name)
        if not skill:
            return params

        if skill_name == "查询天气":
            # 提取城市名
            cities = re.findall(r"[一-龥]{2,7}(?:市|县|区)?", text)
            if cities:
                params["city"] = cities[0]
            else:
                params["city"] = "北京"

        elif skill_name == "网页搜索":
            # 移除关键词后的剩余文本作为查询
            query = text
            for kw in self.TASK_KEYWORDS:
                query = query.replace(kw, "")
            params["query"] = query.strip() or text

        elif skill_name == "计算":
            # 提取数学表达式
            expr = re.search(r"[\d\+\-\*\/\(\)\.\s]+", text)
            if expr:
                params["expression"] = expr.group().strip()
            else:
                params["expression"] = "1+1"

        elif skill_name == "设置提醒":
            params["content"] = text
            # 尝试提取延迟时间
            delay_match = re.search(r"(\d+)\s*(分钟|小时|秒)", text)
            if delay_match:
                num = int(delay_match.group(1))
                unit = delay_match.group(2)
                if unit == "分钟":
                    params["delay_seconds"] = num * 60
                elif unit == "小时":
                    params["delay_seconds"] = num * 3600
                else:
                    params["delay_seconds"] = num
            else:
                params["delay_seconds"] = 60

        elif skill_name == "回声":
            params["text"] = text

        return params

    def execute_skill(self, skill_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """执行技能并记录反馈"""
        if skill_name not in self.skills:
            return {"error": f"技能 '{skill_name}' 未注册", "success": False}

        skill = self.skills[skill_name]
        if not skill.validate(params):
            return {"error": f"参数验证失败: {params}", "success": False}

        start_time = time.time()
        try:
            result = skill.execute(params)
            elapsed = time.time() - start_time

            success = result.get("success", False)
            self._update_usage(skill_name, success, elapsed)

            record = {
                "skill": skill_name,
                "params": params,
                "result": result,
                "success": success,
                "elapsed": elapsed,
                "timestamp": time.time(),
            }
            self.recent_results.append(record)
            if len(self.recent_results) > self.history_limit:
                self.recent_results.pop(0)

            return result
        except Exception as e:
            self._update_usage(skill_name, False, time.time() - start_time)
            return {"error": str(e), "success": False}

    def _update_usage(self, skill_name: str, success: bool, elapsed: float):
        """更新使用统计"""
        stats = self.usage_stats[skill_name]
        if success:
            stats.success_count += 1
            stats.preference = clamp(stats.preference + 0.05)  # 成功增加偏好
        else:
            stats.fail_count += 1
            stats.preference = clamp(stats.preference - 0.08)  # 失败降低偏好
        stats.total_time += elapsed
        stats.last_used = time.time()

    def get_skill_report(self) -> str:
        """生成技能使用报告"""
        lines = ["[Skill Report]"]
        for name, stats in self.usage_stats.items():
            lines.append(
                f"  {name}: 成功{stats.success_count}/失败{stats.fail_count} "
                f"(成功率{stats.success_rate:.0%}, 偏好{stats.preference:.2f})"
            )
        return "\n".join(lines)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "usage_stats": {k: v.to_dict() for k, v in self.usage_stats.items()},
            "recent_results": self.recent_results[-20:],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> EGK_SkillManager:
        sm = cls()
        for name, stats_data in data.get("usage_stats", {}).items():
            if name in sm.usage_stats:
                sm.usage_stats[name] = SkillUsage.from_dict(stats_data)
        sm.recent_results = data.get("recent_results", [])
        return sm
