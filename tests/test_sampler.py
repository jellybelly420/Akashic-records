"""Tests for the resonance sampler — the serendipity engine."""
import math
from datetime import datetime, timedelta

import pytest

from akashic_records.sampler import SamplerEntry, _softmax, _time_decay, resonance_sample


def _entry(id: str, resonance: float, days_ago: float = 0.0, semantic: float = 0.5):
    ts = datetime.utcnow() - timedelta(days=days_ago)
    return SamplerEntry(id=id, resonance=resonance, timestamp=ts, semantic_score=semantic)


class TestTimeDecay:
    def test_fresh_record_minimal_decay(self):
        ts = datetime.utcnow()
        entry = SamplerEntry(id="x", resonance=1.0, timestamp=ts)
        decay = _time_decay(entry.timestamp, half_life_days=30)
        assert decay > 0.99

    def test_half_life_halves_weight(self):
        ts = datetime.utcnow() - timedelta(days=30)
        entry = SamplerEntry(id="x", resonance=1.0, timestamp=ts)
        decay = _time_decay(entry.timestamp, half_life_days=30)
        assert abs(decay - 0.5) < 0.02

    def test_old_record_very_low_weight(self):
        ts = datetime.utcnow() - timedelta(days=365)
        entry = SamplerEntry(id="x", resonance=1.0, timestamp=ts)
        decay = _time_decay(entry.timestamp, half_life_days=30)
        assert decay < 0.01


class TestSoftmax:
    def test_sum_to_one(self):
        values = [1.0, 2.0, 3.0]
        probs = _softmax(values, temperature=1.0)
        assert abs(sum(probs) - 1.0) < 1e-9

    def test_empty(self):
        assert _softmax([], temperature=1.0) == []

    def test_low_temperature_concentrates(self):
        values = [1.0, 10.0, 1.0]
        probs = _softmax(values, temperature=0.01)
        assert probs[1] > 0.99

    def test_high_temperature_flattens(self):
        values = [1.0, 10.0, 1.0]
        probs = _softmax(values, temperature=100.0)
        # All should be close to 1/3
        for p in probs:
            assert abs(p - 1 / 3) < 0.05


class TestResonanceSample:
    def test_returns_correct_count(self):
        entries = [_entry(str(i), 0.5) for i in range(20)]
        result = resonance_sample(entries, k=5)
        assert len(result) == 5

    def test_no_duplicates(self):
        entries = [_entry(str(i), 0.5) for i in range(20)]
        result = resonance_sample(entries, k=10)
        ids = [e.id for e in result]
        assert len(ids) == len(set(ids))

    def test_empty_input(self):
        result = resonance_sample([], k=5)
        assert result == []

    def test_k_larger_than_pool(self):
        entries = [_entry(str(i), 0.5) for i in range(3)]
        result = resonance_sample(entries, k=10)
        assert len(result) == 3

    def test_high_resonance_favored_at_low_temperature(self):
        """At low temperature, high-resonance entries should win most of the time."""
        low = [_entry(f"low_{i}", 0.1, semantic=0.0) for i in range(9)]
        high = [_entry("high", 0.99, semantic=1.0)]
        entries = low + high

        wins = 0
        trials = 50
        for _ in range(trials):
            result = resonance_sample(entries, k=1, temperature=0.01, semantic_weight=0.5)
            if result[0].id == "high":
                wins += 1
        assert wins >= 30, f"High-resonance entry won only {wins}/{trials} times"

    def test_high_temperature_allows_low_resonance(self):
        """At high temperature, low-resonance entries should occasionally surface."""
        low = [_entry(f"low_{i}", 0.01, semantic=0.0) for i in range(1)]
        high = [_entry(f"high_{i}", 0.99, semantic=1.0) for i in range(9)]
        entries = low + high

        low_wins = 0
        trials = 100
        for _ in range(trials):
            result = resonance_sample(entries, k=1, temperature=5.0, semantic_weight=0.0)
            if result[0].id.startswith("low"):
                low_wins += 1
        assert low_wins >= 2, f"Low-resonance entry never surfaced in {trials} trials"

    def test_time_decay_affects_old_records(self):
        """Very old records should surface less than fresh ones at moderate temperature."""
        fresh = [_entry(f"fresh_{i}", 0.5, days_ago=0) for i in range(5)]
        old = [_entry(f"old_{i}", 0.5, days_ago=365) for i in range(5)]
        entries = fresh + old

        fresh_wins = 0
        trials = 100
        for _ in range(trials):
            result = resonance_sample(
                entries, k=3, temperature=0.5,
                half_life_days=30, semantic_weight=0.0
            )
            fresh_wins += sum(1 for e in result if e.id.startswith("fresh"))
        # Fresh should dominate
        assert fresh_wins > trials * 1.5, f"Fresh records only got {fresh_wins} slots"
