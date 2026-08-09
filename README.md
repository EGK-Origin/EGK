# EGK v4 — Enhanced General Kernel
具身成长内核 v4.0.0

> 从"认知存在"升级为"行动存在"的 AI Agent 框架

## 架构概览

```
感知(Perception) → 注意(Attention) → 情绪(Emotion) → 推理(Reasoning)
                                                    ↓
                                              技能系统(Skills)
                                                    ↓
行动(Action) → 反馈(Feedback) → 学习(Learning) → 元认知(Metacognition)
```

### 核心模块

| 模块 | 功能 | 认知科学对应 |
|------|------|-------------|
| **Perception** | 多模态输入、对象恒存性 | 感觉皮层 |
| **Attention** | 显著性检测、目标导向聚焦 | 注意力网络 |
| **Memory** | 感觉/工作/长期记忆三层 | 海马体/前额叶 |
| **Emotion** | 情绪动力学、内感受 | 岛叶/杏仁核 |
| **Causality** | 物理因果验证 | 前额叶推理 |
| **Metacognition** | 自我监控、自我连续性 | 内侧前额叶 |
| **Skills** | 工具使用、自主学习 | 顶叶运动皮层 |
| **Action** | 欲望计算、物理执行 | 运动皮层 |

## 技能系统

EGK v4 新增技能系统，实现"注册-调用-反馈"闭环：

```python
agent = EGKAgent()
agent.think("帮我查一下北京天气")  # → 自动调用 WeatherSkill
agent.think("计算 15 * 23")       # → 自动调用 CalculatorSkill
agent.think("搜索什么是具身智能")  # → 自动调用 WebSearchSkill
```

### 内置技能

- **查询天气** — 模拟天气查询
- **网页搜索** — 信息检索
- **计算** — 安全数学计算
- **设置提醒** — 定时提醒
- **回声** — 测试用

### 技能偏好学习

EGK 会根据技能执行成功率自动调整偏好：
- 成功 → 偏好 +0.05
- 失败 → 偏好 -0.08

## v4 修复（从 v1.4）

| 问题 | v1.4 | v4 |
|------|------|-----|
| 自我连续性签名 | ❌ 基于当前状态（Bug） | ✅ 基于 birth_params |
| 能量系统 | ❌ 不消耗 | ✅ 代谢+移动+推箱子 |
| 焦虑锁死 | ❌ 只增不减 | ✅ 安全环境加速衰减 |
| 价值认知 | ❌ 恒为 0 | ✅ 提高奖励降低衰减 |
| 模块化 | ❌ 单文件 | ✅ 12+ 独立模块 |
| 技能系统 | ❌ 无 | ✅ 5 个内置技能 |
| 配置系统 | ❌ 硬编码 | ✅ dataclass 配置 |
| 测试覆盖 | ❌ 无 | ✅ 6 大测试套件 |

## 快速开始

```bash
# 运行测试
python tests/test_egk.py

# 运行演示
python examples/demo.py

# 交互式对话
python -c "
from egk.main import EGKAgent
agent = EGKAgent()
print(agent.think('帮我查一下北京天气'))
print(agent.think('计算 123 * 456'))
print(agent.think('你学会了什么？'))
"
```

## 许可证

MIT License
