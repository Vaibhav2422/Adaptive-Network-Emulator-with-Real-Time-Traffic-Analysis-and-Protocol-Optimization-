"""
Experiment Manager for the Adaptive Network Emulator.
Validates: Requirements 10.4, 10.7
"""

import itertools
import json
import logging
import random
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class ExperimentConfig:
    """Configuration for a single experiment. Validates: Requirements 10.4, 10.7"""
    experiment_id: str
    parameters: Dict[str, Any]
    random_seed: int = 42
    max_ticks: int = 100
    tick_interval_s: float = 0.0


@dataclass
class ExperimentResult:
    """Result of a single experiment run."""
    experiment_id: str
    parameters: Dict[str, Any]
    random_seed: int
    metrics: Dict[str, Any]
    tick_count: int
    elapsed_s: float
    timestamp: str
    success: bool = True
    error: str = ""


@dataclass
class BatchResult:
    """Results of a batch experiment execution."""
    batch_id: str
    timestamp: str
    total_experiments: int
    successful: int
    failed: int
    results: List[ExperimentResult] = field(default_factory=list)
    elapsed_s: float = 0.0


class ExperimentManager:
    """
    Manages batch experiment execution and parameter sweeps.
    Validates: Requirements 10.4, 10.7
    """

    def __init__(self, results_dir: str = "experiments"):
        self._results_dir = Path(results_dir)
        self._results_dir.mkdir(parents=True, exist_ok=True)
        self._results: List[ExperimentResult] = []
        self._batch_counter = 0

    def run_experiment(
        self,
        config: ExperimentConfig,
        experiment_fn: Callable[[ExperimentConfig, random.Random], Dict[str, Any]],
    ) -> ExperimentResult:
        """Execute a single experiment with a fixed-seed RNG."""
        rng     = random.Random(config.random_seed)
        t_start = time.time()
        metrics: Dict[str, Any] = {}
        success = True
        error   = ""
        try:
            metrics = experiment_fn(config, rng)
        except Exception as exc:
            success = False
            error   = str(exc)
        elapsed = time.time() - t_start
        result  = ExperimentResult(
            experiment_id=config.experiment_id,
            parameters=config.parameters,
            random_seed=config.random_seed,
            metrics=metrics,
            tick_count=config.max_ticks,
            elapsed_s=elapsed,
            timestamp=datetime.now(timezone.utc).isoformat(),
            success=success,
            error=error,
        )
        self._results.append(result)
        return result

    def run_batch(
        self,
        configs: List[ExperimentConfig],
        experiment_fn: Callable[[ExperimentConfig, random.Random], Dict[str, Any]],
    ) -> BatchResult:
        """Run a list of experiments sequentially."""
        self._batch_counter += 1
        batch_id = f"batch_{self._batch_counter}_{int(time.time())}"
        t_start  = time.time()
        results  = [self.run_experiment(cfg, experiment_fn) for cfg in configs]
        elapsed  = time.time() - t_start
        successful = sum(1 for r in results if r.success)
        return BatchResult(
            batch_id=batch_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            total_experiments=len(configs),
            successful=successful,
            failed=len(configs) - successful,
            results=results,
            elapsed_s=elapsed,
        )

    def create_parameter_sweep(
        self,
        base_config: ExperimentConfig,
        sweep_params: Dict[str, List[Any]],
    ) -> List[ExperimentConfig]:
        """Generate all combinations of sweep_params (grid search)."""
        keys   = list(sweep_params.keys())
        combos = list(itertools.product(*sweep_params.values()))
        configs = []
        for i, combo in enumerate(combos):
            params = dict(zip(keys, combo))
            configs.append(ExperimentConfig(
                experiment_id=f"{base_config.experiment_id}_sweep_{i}",
                parameters={**base_config.parameters, **params},
                random_seed=base_config.random_seed,
                max_ticks=base_config.max_ticks,
                tick_interval_s=base_config.tick_interval_s,
            ))
        return configs

    def parameter_sweep(
        self,
        base_config: ExperimentConfig,
        sweep_params: Dict[str, List[Any]],
        experiment_fn: Callable[[ExperimentConfig, random.Random], Dict[str, Any]],
    ) -> BatchResult:
        """Create and run a full parameter sweep."""
        return self.run_batch(
            self.create_parameter_sweep(base_config, sweep_params),
            experiment_fn,
        )

    def check_reproducibility(
        self,
        config: ExperimentConfig,
        experiment_fn: Callable[[ExperimentConfig, random.Random], Dict[str, Any]],
        n_runs: int = 2,
    ) -> bool:
        """Verify identical results across n_runs with same seed."""
        results   = [self.run_experiment(config, experiment_fn) for _ in range(n_runs)]
        reference = results[0].metrics
        for result in results[1:]:
            if result.metrics != reference:
                return False
        return True

    def save_results(self, results: List[ExperimentResult], filename: Optional[str] = None) -> Path:
        fname = filename or f"results_{int(time.time())}.json"
        path  = self._results_dir / fname
        with open(path, "w", encoding="utf-8") as fh:
            json.dump([asdict(r) for r in results], fh, indent=2)
        return path

    def load_results(self, filename: str) -> List[ExperimentResult]:
        path = self._results_dir / filename
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        return [ExperimentResult(**d) for d in data]

    def get_all_results(self) -> List[ExperimentResult]:
        return list(self._results)
