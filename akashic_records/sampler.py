"""
Resonance-weighted random sampler — the serendipity engine.

Knowledge does not arrive on demand; it surfaces through resonance.
High-resonance records are more likely to emerge, but never guaranteed.
Temperature controls the wandering: low = focused, high = serendipitous.
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass
class SamplerEntry:
    id: str
    resonance: float
    timestamp: datetime
    semantic_score: float = 0.0   # 0-1, higher = more similar to intention


def _time_decay(timestamp: datetime, half_life_days: float = 30.0) -> float:
    """Exponential decay: resonance halves every half_life_days."""
    now = datetime.utcnow()
    if timestamp.tzinfo is not None:
        now = datetime.now(timezone.utc)
    age_days = max(0.0, (now - timestamp).total_seconds() / 86400)
    return math.exp(-math.log(2) * age_days / half_life_days)


def _softmax(values: list[float], temperature: float) -> list[float]:
    if not values:
        return []
    if temperature <= 0:
        temperature = 1e-9
    scaled = [v / temperature for v in values]
    max_v = max(scaled)
    exps = [math.exp(v - max_v) for v in scaled]
    total = sum(exps)
    return [e / total for e in exps]


def resonance_sample(
    entries: list[SamplerEntry],
    k: int,
    temperature: float = 0.7,
    half_life_days: float = 30.0,
    semantic_weight: float = 0.4,
) -> list[SamplerEntry]:
    """
    Sample k entries using combined resonance × time-decay × semantic score.

    temperature:
        Low  (0.1-0.3) → high-resonance records dominate (focused recall)
        Mid  (0.5-0.8) → balanced (default)
        High (1.0-2.0) → near-uniform random (maximum serendipity)

    semantic_weight:
        How much the intention/query similarity pulls the sampling.
        0.0 = pure resonance; 1.0 = pure semantic similarity.
    """
    if not entries:
        return []

    k = min(k, len(entries))
    weights = []
    for e in entries:
        decay = _time_decay(e.timestamp, half_life_days)
        combined = (
            (1 - semantic_weight) * e.resonance * decay
            + semantic_weight * e.semantic_score
        )
        weights.append(max(combined, 1e-9))

    probs = _softmax(weights, temperature)
    chosen_idx = random.choices(range(len(entries)), weights=probs, k=k)
    seen = set()
    result = []
    for i in chosen_idx:
        if i not in seen:
            seen.add(i)
            result.append(entries[i])
    # If duplicates reduced count, pad from remaining
    if len(result) < k:
        remaining = [e for j, e in enumerate(entries) if j not in seen]
        random.shuffle(remaining)
        result.extend(remaining[: k - len(result)])
    return result
