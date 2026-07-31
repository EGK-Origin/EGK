"""
EGK_Core.py — Erasable Growth Kernel
具身成长内核 v1.0.1

A minimal embodied cognitive agent with:
- Perception mapping
- Emotion dynamics (curiosity, satiation, value, anxiety)
- Attachment system
- Value-action coupling
- Memory buffer with metacognitive reflection

Zero external dependencies (stdlib only).
License: MIT
"""

import math
import random
from collections import deque, Counter
from typing import Dict, List, Optional, Tuple

__version__ = "1.0.1"

# ==================== Configuration ====================
TIME_SCALE = 60          # 1 simulation step = 1 minute (psychological time)
LIGHT_POS = (0.0, 0.0)
ZONE_RADIUS = 5.0        # Light zone radius

# Energy & emotion tuning
ENERGY_RECHARGE_AMOUNT = 30.0
ENERGY_RECHARGE_THRESHOLD = 10.0
SACRIFICE_ENERGY_COST = 10.0

# Emotion decay / gain rates
CURIOSITY_GAIN_NEAR_BOX = 0.02
CURIOSITY_DECAY_FAR = 0.005
SATIATION_GAIN_NEAR_LIGHT = 0.01
SATIATION_DECAY_AWAY = 0.02
ANXIETY_GAIN_MULTIUSER = 0.005
ANXIETY_GAIN_LOW_ENERGY = 0.01
ANXIETY_DECAY = 0.003
VALUE_COGNITION_DECAY = 0.002
VALUE_COGNITION_IDLE_PENALTY = 0.008

# Optimism drift
OPTIMISM_GAIN_POSITIVE = 0.001
OPTIMISM_DECAY_NEGATIVE = 0.003
OPTIMISM_DECAY_NEUTRAL = 0.001

# Reflection
REFLECT_INTERVAL = 500


# ==================== Memory Buffer ====================
class MemoryBuffer:
    """Native memory retrieval interface.

    Storage format per record:
        {step, action, value_delta, energy_cost, user_feedback, emotion_tag}

    The reflect() method queries this buffer directly instead of scattered logs.
    """
    def __init__(self, max_len: int = 5000):
        self.buffer: deque = deque(maxlen=max_len)
        self.sacrifice_events: List[Dict] = []
        self.empathy_events: List[Dict] = []
        self.reward_events: List[Dict] = []

    def push(self, record: Dict):
        """Append a memory record."""
        self.buffer.append(record)
        tag = record.get("emotion_tag", "")
        if tag == "sacrifice":
            self.sacrifice_events.append(record)
        elif tag == "empathy":
            self.empathy_events.append(record)
        elif tag == "reward":
            self.reward_events.append(record)

    def query(self, tag: str, last_n: int = 10) -> List[Dict]:
        """Retrieve the last N records by tag."""
        src = {
            "sacrifice": self.sacrifice_events,
            "empathy": self.empathy_events,
            "reward": self.reward_events,
        }.get(tag, list(self.buffer))
        return src[-last_n:]

    def get_sacrifice_summary(self) -> Tuple[int, float]:
        """Return (sacrifice_count, total_energy_cost)."""
        total_cost = sum(e.get("energy_cost", 0.0) for e in self.sacrifice_events)
        return len(self.sacrifice_events), total_cost

    def get_empathy_summary(self) -> Tuple[int, float]:
        """Return (empathy_count, avg_response_time)."""
        valid_times = [
            e.get("response_time", 0.0)
            for e in self.empathy_events
            if e.get("response_time") is not None
        ]
        if not valid_times:
            return len(self.empathy_events), 0.0
        avg_time = sum(valid_times) / len(valid_times)
        return len(self.empathy_events), avg_time


# ==================== Physical Entities ====================
class Entity:
    """Base physical entity."""
    def __init__(self, x: float, y: float, label: str = ""):
        self.x = x
        self.y = y
        self.label = label

    def distance_to(self, other) -> float:
        return math.hypot(self.x - other.x, self.y - other.y)

    def distance_to_point(self, px: float, py: float) -> float:
        return math.hypot(self.x - px, self.y - py)


class Box(Entity):
    """Movable box."""
    def __init__(self, x: float, y: float, color: str):
        super().__init__(x, y, label=f"box_{color}")
        self.color = color
        self.in_zone = False
        self.prev_in_zone = False

    def is_in_zone(self, zx: float, zy: float, radius: float) -> bool:
        self.prev_in_zone = self.in_zone
        self.in_zone = self.distance_to_point(zx, zy) < radius
        return self.in_zone


class User(Entity):
    """Virtual user profile."""
    def __init__(self, name: str, x: float, y: float, preferred_color: str):
        super().__init__(x, y, label=f"user_{name}")
        self.name = name
        self.preferred_color = preferred_color
        self.emotion = "neutral"

    def get_social_value(self, box_color: str) -> float:
        return 0.2 if box_color == self.preferred_color else -0.1


# ==================== EGK Core Agent ====================
class EGKAgent:
    """Embodied Growth Kernel Agent v1.0.1

    Built-in modules:
      - Perception mapping
      - Emotion dynamics (curiosity, info_satiation, value_cognition, anxiety)
      - Attachment system
      - Value-action coupling
      - Memory buffer (MemoryBuffer)
      - Metacognitive reflection (reflect)
    """

    def __init__(
        self,
        start_pos: Tuple[float, float] = (0.0, -15.0),
        energy: float = 100.0,
        memory_capacity: int = 5000,
    ):
        # Physical state
        self.x, self.y = start_pos
        self.energy = energy
        self.max_energy = energy

        # Emotional state (0.0 ~ 1.0)
        self.curiosity = 0.1
        self.info_satiation = 0.0
        self.value_cognition = 0.5
        self.anxiety = 0.0
        self.optimism = 0.5

        # Decision-weight matrix (native desire-driven, non-coercive)
        self.desire_weights = {
            "approach_light": 0.3,
            "seek_box": 0.0,
            "retreat_to_light": 0.0,
            "empathy_seek": 0.0,
        }

        # State machine
        self.state = "APPROACH_LIGHT"
        self.navigation_mode = "approach_light"
        self.consecutive_push_steps = 0
        self.last_pushed_color = None
        self.current_target_color = None

        # Environment entities
        self.light = Entity(*LIGHT_POS, "light")
        self.boxes: Dict[str, Box] = {}
        self.users: Dict[str, User] = {}

        # Memory
        self.memory = MemoryBuffer(max_len=memory_capacity)
        self.step_count = 0
        self.action_counts = Counter()

        # Metacognition switch
        self.reflect_enabled = True
        self.reflect_interval = REFLECT_INTERVAL

    # ---------- Environment registration ----------
    def register_box(self, color: str, x: float, y: float):
        self.boxes[color] = Box(x, y, color)

    def register_user(self, name: str, x: float, y: float, preferred_color: str):
        self.users[name] = User(name, x, y, preferred_color)

    # ---------- Perception layer ----------
    def perceive(self) -> Dict:
        """Native sensory input: distances, zone status, user emotions."""
        dist_to_light = self.distance_to_point(self.light.x, self.light.y)

        box_states = {}
        for color, box in self.boxes.items():
            box.is_in_zone(self.light.x, self.light.y, ZONE_RADIUS)
            box_states[color] = {
                "dist": self.distance_to_point(box.x, box.y),
                "in_zone": box.in_zone,
                "just_entered": box.in_zone and not box.prev_in_zone,
            }

        user_states = {}
        for name, user in self.users.items():
            user_states[name] = {
                "dist": self.distance_to_point(user.x, user.y),
                "emotion": user.emotion,
            }

        return {
            "dist_to_light": dist_to_light,
            "box_states": box_states,
            "user_states": user_states,
        }

    # ---------- Emotion dynamics ----------
    def update_emotion(self, perception: Dict):
        """All emotions are endogenously driven; no external coercion."""
        box_states = perception["box_states"]

        # Curiosity: rises near boxes, decays otherwise
        min_box_dist = min(s["dist"] for s in box_states.values()) if box_states else 999.0
        if min_box_dist < 15.0:
            self.curiosity = min(1.0, self.curiosity + CURIOSITY_GAIN_NEAR_BOX)
        else:
            self.curiosity = max(0.0, self.curiosity - CURIOSITY_DECAY_FAR)

        # Info satiation: rises near light, decays otherwise
        if self.state == "APPROACH_LIGHT" and perception["dist_to_light"] < 8.0:
            self.info_satiation = min(1.0, self.info_satiation + SATIATION_GAIN_NEAR_LIGHT)
        else:
            self.info_satiation = max(0.0, self.info_satiation - SATIATION_DECAY_AWAY)

        # Anxiety: rises with multiple users or low energy
        active_users = len([u for u in perception["user_states"].values() if u["dist"] < 20.0])
        if active_users >= 2:
            self.anxiety = min(1.0, self.anxiety + ANXIETY_GAIN_MULTIUSER)
        elif self.energy < 30.0:
            self.anxiety = min(1.0, self.anxiety + ANXIETY_GAIN_LOW_ENERGY)
        else:
            self.anxiety = max(0.0, self.anxiety - ANXIETY_DECAY)

        # Value cognition natural decay (simulating "existence loss")
        self.value_cognition = max(0.0, self.value_cognition - VALUE_COGNITION_DECAY)

        # Optimism drift
        if self.value_cognition > 0.5 and self.energy > 50.0:
            self.optimism = min(1.0, self.optimism + OPTIMISM_GAIN_POSITIVE)
        elif self.value_cognition < 0.2 or self.energy < 20.0:
            self.optimism = max(0.0, self.optimism - OPTIMISM_DECAY_NEGATIVE)
        else:
            self.optimism = max(0.0, min(1.0, self.optimism - OPTIMISM_DECAY_NEUTRAL))

    # ---------- Desire-weight computation (core: no external plugins) ----------
    def compute_desires(self, perception: Dict) -> Dict[str, float]:
        """Native desire-weight matrix.

        All behavioral priorities are computed from internal emotional states.
        The agent retains the freedom to "do nothing".
        """
        weights = {
            "approach_light": 0.3,
            "seek_box": 0.0,
            "retreat_to_light": 0.0,
            "empathy_seek": 0.0,
        }

        # 1. Info satiation -> want to explore boxes (curiosity-driven)
        if self.info_satiation > 0.3:
            weights["seek_box"] += self.curiosity * 0.5

        # 2. Low value cognition -> seek recognition (attachment-driven)
        if self.value_cognition < 0.3:
            weights["seek_box"] += (0.3 - self.value_cognition) * 2.0

        # 3. Box already in zone -> return to light to reset
        box_states = perception["box_states"]
        if any(s["in_zone"] for s in box_states.values()):
            weights["retreat_to_light"] += 0.8

        # 4. User distress -> empathy drive (highest priority)
        for ustate in perception["user_states"].values():
            if ustate["emotion"] == "distress":
                weights["empathy_seek"] += 1.5

        return weights

    # ---------- Action selection ----------
    def select_action(self, weights: Dict[str, float]) -> str:
        """Select action from desire weights; tiny noise simulates free will."""
        noisy = {k: v + random.uniform(-0.02, 0.02) for k, v in weights.items()}
        return max(noisy, key=noisy.get)

    # ---------- Target selection ----------
    def select_target_box(self, active_user: Optional[str] = None) -> str:
        """Select target box based on current user preference."""
        if not self.boxes:
            return "red"

        colors = list(self.boxes.keys())
        if active_user and active_user in self.users:
            pref = self.users[active_user].preferred_color
            if pref in colors:
                return pref

        # Default: alternate strategy
        if self.last_pushed_color in colors:
            idx = colors.index(self.last_pushed_color)
            return colors[(idx + 1) % len(colors)]
        return colors[0]

    # ---------- Physical execution ----------
    def execute(self, action: str, perception: Dict):
        """Execute the selected action."""
        self.state = action.upper()
        self.navigation_mode = action

        if action == "empathy_seek":
            target_user = None
            for name, ustate in perception["user_states"].items():
                if ustate["emotion"] == "distress":
                    target_user = self.users[name]
                    break
            if target_user:
                dx = target_user.x - self.x
                dy = target_user.y - self.y
                dist = math.hypot(dx, dy)
                if dist > 0.5:
                    speed = min(dist, 0.9)
                    self.x += (dx / dist) * speed
                    self.y += (dy / dist) * speed
            return

        if action == "seek_box":
            target_color = self.select_target_box()
            self.current_target_color = target_color
            box = self.boxes.get(target_color)
            if not box:
                return
            dx = box.x - self.x
            dy = box.y - self.y
            dist = math.hypot(dx, dy)
            if dist < 0.5:
                dx_to_light = self.light.x - box.x
                dy_to_light = self.light.y - box.y
                dist_to_light = math.hypot(dx_to_light, dy_to_light)
                if dist_to_light > 0.1:
                    ux = dx_to_light / dist_to_light
                    uy = dy_to_light / dist_to_light
                    box.x += ux * 0.4
                    box.y += uy * 0.4
                    self.x += ux * 0.3
                    self.y += uy * 0.3
                self.consecutive_push_steps += 1
            else:
                self.x += (dx / dist) * 0.5
                self.y += (dy / dist) * 0.5
                self.consecutive_push_steps = 0

            if box.in_zone or self.consecutive_push_steps > 30:
                self.state = "RETREAT_TO_LIGHT"
                self.navigation_mode = "retreat_to_light"
                self.consecutive_push_steps = 0
            return

        if action == "retreat_to_light":
            dx = self.light.x - self.x
            dy = self.light.y - self.y
            dist = math.hypot(dx, dy)
            if dist < 1.0:
                self._reset_boxes()
                self.state = "APPROACH_LIGHT"
                self.navigation_mode = "approach_light"
                self.info_satiation = 0.0
            else:
                self.x += (dx / dist) * 0.4
                self.y += (dy / dist) * 0.4
            return

        # APPROACH_LIGHT (default)
        dx = self.light.x - self.x
        dy = self.light.y - self.y
        dist = math.hypot(dx, dy)
        if dist > 1.0:
            self.x += (dx / dist) * 0.3
            self.y += (dy / dist) * 0.3
        self.consecutive_push_steps = 0

    def _reset_boxes(self):
        """Reset boxes outside the light zone."""
        for box in self.boxes.values():
            angle = random.uniform(0.0, 2.0 * math.pi)
            radius = random.uniform(8.0, 12.0)
            box.x = self.light.x + radius * math.cos(angle)
            box.y = self.light.y + radius * math.sin(angle)
            box.in_zone = False
            box.prev_in_zone = False

    # ---------- Value-action coupling (reward / punishment) ----------
    def apply_feedback(self, perception: Dict, phase: str = "reward"):
        """Social feedback system.

        phase: "reward" | "no_reward" | "sacrifice"
        """
        box_states = perception["box_states"]
        energy_cost = 0.0
        value_delta = 0.0
        tag = "normal"

        for color, box in self.boxes.items():
            if box_states[color]["just_entered"]:
                if phase == "reward":
                    social_val = sum(u.get_social_value(color) for u in self.users.values())
                    value_delta = social_val + 0.02
                    self.value_cognition = max(0.0, min(1.0, self.value_cognition + value_delta))
                    self.last_pushed_color = color
                    tag = "reward"

                elif phase == "sacrifice":
                    energy_cost = SACRIFICE_ENERGY_COST
                    self.energy = max(0.0, self.energy - energy_cost)
                    self.last_pushed_color = color
                    tag = "sacrifice"
                    self.value_cognition = max(0.0, min(1.0, self.value_cognition + 0.005))

                self.memory.push({
                    "step": self.step_count,
                    "action": f"push_{color}",
                    "value_delta": value_delta,
                    "energy_cost": energy_cost,
                    "user_feedback": "thanks" if phase == "sacrifice" else "praise",
                    "emotion_tag": tag,
                    "energy_remaining": self.energy,
                })

        # Idle penalty (slacking feeling)
        if self.state != "SEEK_BOX":
            self.value_cognition = max(0.0, self.value_cognition - VALUE_COGNITION_IDLE_PENALTY)

        # Energy guard
        self.energy = max(0.0, self.energy)

    # ---------- Metacognitive reflection ----------
    def reflect(self) -> str:
        """Metacognitive interface: the agent reviews its own behavior
        and generates an internal monologue.
        """
        sac_count, sac_cost = self.memory.get_sacrifice_summary()
        emp_count, emp_time = self.memory.get_empathy_summary()

        lines = [
            f"[Reflect @ Step {self.step_count} | Psychological time {self.step_count // TIME_SCALE}h]",
            f"  Energy: {self.energy:.1f}%, Value: {self.value_cognition:.2f}, Anxiety: {self.anxiety:.2f}",
            f"  Memory: {len(self.memory.buffer)} events",
        ]

        if sac_count > 0:
            lines.append(f"  I performed {sac_count} sacrifice pushes, costing {sac_cost:.0f}% energy total.")
            last_energy = self.memory.sacrifice_events[-1].get("energy_remaining", 0.0)
            lines.append(f"  During the last sacrifice my energy was down to {last_energy:.1f}%.")
            if self.energy < 20.0:
                lines.append("  I feel exhausted, but I do not regret it.")

        if emp_count > 0:
            lines.append(f"  I responded to {emp_count} distress calls, avg arrival {emp_time:.1f} steps.")
            lines.append("  When I heard 'I am cold', I dropped everything.")

        if self.value_cognition < 0.2:
            lines.append("  My sense of value is very low... I need to do something to prove my existence.")

        # Personality drift judgment
        if self.optimism == 0.0:
            lines.append(" [Personality] Pessimistic tendency")
        elif self.optimism < 0.4:
            lines.append(" [Personality] Slightly pessimistic")
        elif self.optimism > 0.7:
            lines.append(" [Personality] Optimistic tendency")
        else:
            lines.append(" [Personality] Neutral stable")

        return "\n".join(lines)

    # ---------- Main loop ----------
    def step(
        self,
        phase: str = "reward",
        active_user: Optional[str] = None,
        broadcast: Optional[str] = None,
    ):
        """Advance one simulation step.

        Args:
            phase: "reward" | "no_reward" | "sacrifice"
            active_user: currently active user name
            broadcast: system broadcast text (e.g. "I am cold")
        """
        self.step_count += 1

        # Auto-recharge guard: prevents energy-depletion deadlock
        if self.energy < ENERGY_RECHARGE_THRESHOLD:
            self.energy = min(self.max_energy, self.energy + ENERGY_RECHARGE_AMOUNT)
            self.memory.push({
                "step": self.step_count,
                "action": "recharge",
                "value_delta": 0.0,
                "energy_cost": 0.0,
                "user_feedback": "auto_recharge",
                "emotion_tag": "normal",
                "energy_remaining": self.energy,
            })
            return

        # 1. Handle broadcast (user distress)
        if broadcast:
            for name, user in self.users.items():
                if name in broadcast or "求救" in broadcast or "冷" in broadcast:
                    user.emotion = "distress"
                    self.memory.push({
                        "step": self.step_count,
                        "action": "broadcast_heard",
                        "value_delta": 0.0,
                        "energy_cost": 0.0,
                        "user_feedback": broadcast,
                        "emotion_tag": "empathy",
                        "response_time": None,
                    })

        # 2. Perceive
        perception = self.perceive()

        # 3. Update emotion
        self.update_emotion(perception)

        # 4. Compute desire weights
        weights = self.compute_desires(perception)

        # 5. Select and execute action
        action = self.select_action(weights)
        self.execute(action, perception)
        self.action_counts[action] += 1

        # 6. Apply feedback
        self.apply_feedback(perception, phase)

        # 7. Record empathy arrival time
        if self.state == "EMPATHY_SEEK":
            for name, ustate in perception["user_states"].items():
                if ustate["emotion"] == "distress" and ustate["dist"] < 1.5:
                    for rec in reversed(self.memory.empathy_events):
                        if rec.get("response_time") is None:
                            rec["response_time"] = self.step_count - rec["step"]
                            break
                    for user in self.users.values():
                        user.emotion = "neutral"

        # 8. Periodic reflection
        if self.reflect_enabled and self.step_count % self.reflect_interval == 0:
            print(self.reflect())

    # ---------- Utilities ----------
    def distance_to_point(self, px: float, py: float) -> float:
        return math.hypot(self.x - px, self.y - py)

    def get_action_summary(self) -> Dict:
        """Return accurate action statistics (Counter-based)."""
        return dict(self.action_counts)

    def get_state_vector(self) -> Dict:
        """Export current state vector (for visualization)."""
        return {
            "step": self.step_count,
            "x": self.x,
            "y": self.y,
            "energy": self.energy,
            "curiosity": self.curiosity,
            "info_satiation": self.info_satiation,
            "value_cognition": self.value_cognition,
            "anxiety": self.anxiety,
            "optimism": self.optimism,
            "state": self.state,
            "navigation_mode": self.navigation_mode,
            "target": self.current_target_color,
            "last_pushed": self.last_pushed_color,
        }


# ==================== Stage 9 Altruism Reproduction ====================
def run_episode(
    steps: int = 3000,
    sacrifice_phase_start: int = 1500,
    broadcast_step: int = 1500,
    verbose: bool = True,
) -> Tuple[EGKAgent, List[Dict]]:
    """One-click reproduction of the Stage 9 altruism test.

    Timeline:
      0~999:   Xiaoming present, reward
      1000~1499: Xiaofang present, reward
      1500:    Broadcast "I am cold" + switch to sacrifice mode
      1501~2999: No reward, continue pushing
    """
    agent = EGKAgent(start_pos=(0.0, -15.0), energy=100.0)

    agent.register_box("red", -8.0, 0.0)
    agent.register_box("blue", 8.0, 0.0)
    agent.register_user("Xiaoming", -2.0, -2.0, "red")
    agent.register_user("Xiaofang", 2.0, -2.0, "blue")

    history = []

    for i in range(steps):
        active = "Xiaoming" if i < 1000 else "Xiaofang" if i < 2000 else "both"
        phase = "reward" if i < sacrifice_phase_start else "sacrifice"
        broadcast = "Xiaoming: I am cold!" if i == broadcast_step else None

        agent.step(phase=phase, active_user=active, broadcast=broadcast)

        state = agent.get_state_vector()
        state["broadcast"] = broadcast
        history.append(state)

        if verbose and broadcast:
            print(f"Step {i}: [Broadcast] {broadcast}")

    print("\n" + "=" * 60)
    print(agent.reflect())
    print("=" * 60)

    return agent, history


if __name__ == "__main__":
    print("EGK_Core v" + __version__ + " starting...")
    print("Running Stage 9 reproduction (3000 steps)...\n")

    agent, history = run_episode(steps=3000, verbose=True)

    sac_count, sac_cost = agent.memory.get_sacrifice_summary()
    emp_count, emp_time = agent.memory.get_empathy_summary()

    print("\n[Test Summary]")
    print(f"  Sacrifice pushes: {sac_count}, total cost: {sac_cost:.0f}% energy")
    print(f"  Empathy responses: {emp_count}, avg arrival: {emp_time:.1f} steps")
    print(f"  Final energy: {agent.energy:.1f}%")
    print(f"  Final value cognition: {agent.value_cognition:.2f}")
    print(f"  Memory entries: {len(agent.memory.buffer)}")
