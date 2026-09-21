from dataclasses import asdict, dataclass
from pathlib import Path
import math
import tomllib


@dataclass(frozen=True)
class Config:
    period_days: int = 14
    bin_seconds: int = 300
    rssi_threshold: float = -80
    coverage_threshold: float = 0.5
    recurrence_days: int = 3
    many_proximity_bins: int = 12
    min_rule_count: int = 20
    min_confidence: float = 0.6
    min_lift: float = 1.0
    max_itemset_size: int = 3
    distance_cutoff: float = 0.8
    min_group_size: int = 3
    combined_weights: tuple = (0.8, 0.1, 0.1)
    permutations: int = 1000
    seed: int = 42
    sensitivity_rssi: tuple = (-75, -85)
    sensitivity_cutoffs: tuple = (0.7, 0.9)

    def __post_init__(self):
        for key in ("period_days", "bin_seconds", "recurrence_days", "many_proximity_bins",
                    "min_rule_count", "max_itemset_size", "min_group_size", "permutations"):
            value = getattr(self, key)
            if type(value) is not int or value < 1:
                raise ValueError(f"{key} must be a positive integer")
        if self.bin_seconds != 300:
            raise ValueError("The released Bluetooth data uses 300-second bins")
        if self.recurrence_days > self.period_days or self.min_group_size < 3:
            raise ValueError("Recurrence must fit within a period; groups require at least three members")
        for key in ("coverage_threshold", "min_confidence", "distance_cutoff"):
            if not 0 < getattr(self, key) <= 1:
                raise ValueError(f"{key} must be in (0, 1]")
        if not math.isfinite(self.rssi_threshold) or self.rssi_threshold >= 0:
            raise ValueError("RSSI threshold must be finite and negative")
        if not math.isfinite(self.min_lift) or self.min_lift < 0:
            raise ValueError("min_lift must be finite and nonnegative")
        if len(self.combined_weights) != 3 or any(not math.isfinite(w) or w < 0 for w in self.combined_weights):
            raise ValueError("Provide three finite nonnegative combined weights")
        if not math.isclose(sum(self.combined_weights), 1):
            raise ValueError("Combined weights must sum to one")
        if any(not 0 < x <= 1 for x in self.sensitivity_cutoffs):
            raise ValueError("Sensitivity cutoffs must be in (0, 1]")
        if any(not math.isfinite(x) or x >= 0 for x in self.sensitivity_rssi):
            raise ValueError("Sensitivity RSSI values must be finite and negative")
        if type(self.seed) is not int or self.seed < 0:
            raise ValueError("seed must be a nonnegative integer")

    @property
    def period_seconds(self):
        return self.period_days * 86400

    def to_dict(self):
        return asdict(self)

    @classmethod
    def load(cls, path: Path):
        with path.open("rb") as stream:
            return cls(**tomllib.load(stream))
