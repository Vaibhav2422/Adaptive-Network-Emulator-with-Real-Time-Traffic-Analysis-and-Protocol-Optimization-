"""
Simulation Controller for the Adaptive Network Emulator.
Validates: Requirements 10.1, 10.7
"""

import json
import logging
import threading
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class SimulationState(Enum):
    IDLE     = "idle"
    RUNNING  = "running"
    PAUSED   = "paused"
    STEPPING = "stepping"
    STOPPED  = "stopped"


class SpeedMode(Enum):
    REAL_TIME    = "real_time"
    FAST_FORWARD = "fast_forward"
    INSTANT      = "instant"


@dataclass
class SimulationConfig:
    """Configuration for a simulation run."""
    tick_rate: float = 10.0          # ticks per second in real-time mode
    speed_mode: str = "real_time"
    speed_multiplier: float = 1.0
    max_ticks: Optional[int] = None
    seed: Optional[int] = None


@dataclass
class SimulationCheckpoint:
    """Saved simulation state. Validates: Requirement 10.7"""
    checkpoint_id: str
    timestamp: str
    tick_count: int
    elapsed_s: float
    state: str
    config: Dict
    custom_data: Dict = field(default_factory=dict)


@dataclass
class SimulationStats:
    state: str
    tick_count: int
    elapsed_s: float
    speed_mode: str
    speed_multiplier: float
    paused_count: int
    step_count: int


class SimulationController:
    """
    Controls simulation lifecycle: start, pause, resume, stop, step.
    Validates: Requirements 10.1, 10.7
    """

    def __init__(
        self,
        config: Optional[SimulationConfig] = None,
        checkpoint_dir: str = "checkpoints",
    ):
        self.config = config or SimulationConfig()
        self._checkpoint_dir = Path(checkpoint_dir)
        self._checkpoint_dir.mkdir(parents=True, exist_ok=True)

        self._state = SimulationState.IDLE
        self._tick_count = 0
        self._start_time: Optional[float] = None
        self._pause_start: Optional[float] = None
        self._total_paused_s: float = 0.0
        self._paused_count = 0
        self._step_count = 0

        self._thread: Optional[threading.Thread] = None
        self._pause_event = threading.Event()
        self._pause_event.set()
        self._stop_event  = threading.Event()

        self._tick_callbacks: List[Callable[[int, float], None]] = []
        self._state_callbacks: List[Callable[[SimulationState], None]] = []
        self._custom_state: Dict = {}

    # ── Lifecycle ─────────────────────────────────────────────────────────

    def start(self) -> bool:
        if self._state not in (SimulationState.IDLE, SimulationState.STOPPED):
            return False
        self._state = SimulationState.RUNNING
        self._tick_count = 0
        self._start_time = time.time()
        self._total_paused_s = 0.0
        self._stop_event.clear()
        self._pause_event.set()
        self._notify_state()
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        return True

    def pause(self) -> bool:
        if self._state != SimulationState.RUNNING:
            return False
        self._state = SimulationState.PAUSED
        self._pause_event.clear()
        self._pause_start = time.time()
        self._paused_count += 1
        self._notify_state()
        return True

    def resume(self) -> bool:
        if self._state != SimulationState.PAUSED:
            return False
        if self._pause_start:
            self._total_paused_s += time.time() - self._pause_start
            self._pause_start = None
        self._state = SimulationState.RUNNING
        self._pause_event.set()
        self._notify_state()
        return True

    def stop(self) -> bool:
        if self._state == SimulationState.STOPPED:
            return False
        self._state = SimulationState.STOPPED
        self._stop_event.set()
        self._pause_event.set()
        self._notify_state()
        if self._thread:
            self._thread.join(timeout=5.0)
        return True

    def step(self) -> bool:
        """Advance exactly one tick (debug mode)."""
        if self._state not in (SimulationState.PAUSED, SimulationState.IDLE,
                                SimulationState.STEPPING):
            return False
        if self._start_time is None:
            self._start_time = time.time()
        self._state = SimulationState.STEPPING
        self._step_count += 1
        sim_time = self._sim_time()
        self._invoke_tick_callbacks(self._tick_count, sim_time)
        self._tick_count += 1
        self._state = SimulationState.PAUSED
        self._pause_event.clear()
        self._notify_state()
        return True

    # ── Speed control ─────────────────────────────────────────────────────

    def set_speed(self, mode: SpeedMode, multiplier: float = 1.0) -> None:
        self.config.speed_mode       = mode.value
        self.config.speed_multiplier = max(0.01, multiplier)

    def set_real_time(self) -> None:
        self.set_speed(SpeedMode.REAL_TIME, 1.0)

    def set_fast_forward(self, multiplier: float = 10.0) -> None:
        self.set_speed(SpeedMode.FAST_FORWARD, multiplier)

    def set_instant(self) -> None:
        self.set_speed(SpeedMode.INSTANT, 1.0)

    # ── Checkpoint ────────────────────────────────────────────────────────

    def save_checkpoint(
        self,
        checkpoint_id: Optional[str] = None,
        custom_data: Optional[Dict] = None,
    ) -> SimulationCheckpoint:
        cid = checkpoint_id or f"ckpt_{int(time.time() * 1000)}"
        checkpoint = SimulationCheckpoint(
            checkpoint_id=cid,
            timestamp=datetime.now(timezone.utc).isoformat(),
            tick_count=self._tick_count,
            elapsed_s=self._sim_time(),
            state=self._state.value,
            config=asdict(self.config),
            custom_data=custom_data or self._custom_state,
        )
        path = self._checkpoint_dir / f"{cid}.json"
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(asdict(checkpoint), fh, indent=2)
        return checkpoint

    def load_checkpoint(self, checkpoint_id: str) -> Optional[SimulationCheckpoint]:
        path = self._checkpoint_dir / f"{checkpoint_id}.json"
        if not path.exists():
            return None
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        checkpoint = SimulationCheckpoint(**data)
        self._tick_count   = checkpoint.tick_count
        self._custom_state = checkpoint.custom_data
        self.config        = SimulationConfig(**checkpoint.config)
        return checkpoint

    def list_checkpoints(self) -> List[str]:
        return [p.stem for p in self._checkpoint_dir.glob("*.json")]

    # ── Callbacks & query ─────────────────────────────────────────────────

    def add_tick_callback(self, cb: Callable[[int, float], None]) -> None:
        self._tick_callbacks.append(cb)

    def add_state_callback(self, cb: Callable[[SimulationState], None]) -> None:
        self._state_callbacks.append(cb)

    def get_state(self) -> SimulationState:
        return self._state

    def get_tick_count(self) -> int:
        return self._tick_count

    def get_stats(self) -> SimulationStats:
        return SimulationStats(
            state=self._state.value,
            tick_count=self._tick_count,
            elapsed_s=self._sim_time(),
            speed_mode=self.config.speed_mode,
            speed_multiplier=self.config.speed_multiplier,
            paused_count=self._paused_count,
            step_count=self._step_count,
        )

    def set_custom_state(self, key: str, value: Any) -> None:
        self._custom_state[key] = value

    # ── Internal ─────────────────────────────────────────────────────────

    def _run_loop(self) -> None:
        while not self._stop_event.is_set():
            self._pause_event.wait()
            if self._stop_event.is_set():
                break
            if self.config.max_ticks and self._tick_count >= self.config.max_ticks:
                self.stop()
                break
            self._invoke_tick_callbacks(self._tick_count, self._sim_time())
            self._tick_count += 1
            sleep_s = self._tick_sleep()
            if sleep_s > 0:
                time.sleep(sleep_s)

    def _tick_sleep(self) -> float:
        mode = self.config.speed_mode
        if mode == SpeedMode.INSTANT.value:
            return 0.0
        base = 1.0 / max(self.config.tick_rate, 0.001)
        if mode == SpeedMode.FAST_FORWARD.value:
            return base / max(self.config.speed_multiplier, 0.01)
        return base

    def _sim_time(self) -> float:
        if self._start_time is None:
            return 0.0
        return max(0.0, time.time() - self._start_time - self._total_paused_s)

    def _invoke_tick_callbacks(self, tick: int, sim_time: float) -> None:
        for cb in self._tick_callbacks:
            try:
                cb(tick, sim_time)
            except Exception as exc:
                logger.error("Tick callback error: %s", exc)

    def _notify_state(self) -> None:
        for cb in self._state_callbacks:
            try:
                cb(self._state)
            except Exception as exc:
                logger.error("State callback error: %s", exc)
