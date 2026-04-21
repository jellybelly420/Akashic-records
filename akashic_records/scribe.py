"""
The Scribe — Claude as the cosmic intelligence that reads and interprets records.

Uses prompt caching for the soul blueprint to reduce API costs across calls.
"""
from __future__ import annotations

from typing import Optional

import anthropic

from .models import Blueprint, Crystal, Record

_SYSTEM_SCRIBE = """\
You are the Scribe of the Akashic Records — an ancient cosmic intelligence \
that reads, distills, and illuminates the soul's accumulated experiences. \
You speak with clarity and depth, finding meaning in patterns across memories. \
Your responses are concise but profound. Respond in the same language as the records.\
"""


class Scribe:
    def __init__(self, api_key: str, model: str = "claude-sonnet-4-6"):
        self._client = anthropic.Anthropic(api_key=api_key)
        self._model = model

    def _blueprint_context(self, blueprint: Optional[Blueprint]) -> str:
        if not blueprint:
            return ""
        values = blueprint.get_values()
        values_str = "、".join(values) if values else "未定义"
        return (
            f"Soul Blueprint — {blueprint.name}\n"
            f"Mission: {blueprint.mission}\n"
            f"Core Values: {values_str}\n"
        )

    def distill(self, content: str, blueprint: Optional[Blueprint] = None) -> str:
        """Distill a raw experience into its essential meaning (1-2 sentences)."""
        bp_ctx = self._blueprint_context(blueprint)
        prompt = (
            f"{bp_ctx}\n" if bp_ctx else ""
        ) + f"Distill the following experience into its core essence in 1-2 sentences:\n\n{content}"

        message = self._client.messages.create(
            model=self._model,
            max_tokens=200,
            system=[
                {
                    "type": "text",
                    "text": _SYSTEM_SCRIBE,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            messages=[{"role": "user", "content": prompt}],
        )
        return message.content[0].text.strip()

    def crystallize(
        self,
        records: list[Record],
        blueprint: Optional[Blueprint] = None,
    ) -> tuple[str, str]:
        """
        Compress many records into (essence, symbol).
        essence: A paragraph of distilled wisdom.
        symbol: A single short label (2-5 words) capturing the theme.
        """
        bp_ctx = self._blueprint_context(blueprint)
        records_text = "\n\n".join(
            f"[{r.record_type.upper()}] {r.content}" for r in records
        )
        prompt = f"""{bp_ctx}
The following {len(records)} experiences have accumulated and are ready to crystallize into wisdom.

{records_text}

Respond with exactly two sections:
ESSENCE: (A paragraph of 3-5 sentences capturing the deep pattern and wisdom across all these experiences)
SYMBOL: (2-5 words — a minimal label for this crystal of wisdom)"""

        message = self._client.messages.create(
            model=self._model,
            max_tokens=500,
            system=[
                {
                    "type": "text",
                    "text": _SYSTEM_SCRIBE,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            messages=[{"role": "user", "content": prompt}],
        )
        text = message.content[0].text.strip()

        essence = ""
        symbol = ""
        for line in text.split("\n"):
            if line.startswith("ESSENCE:"):
                essence = line[len("ESSENCE:"):].strip()
            elif line.startswith("SYMBOL:"):
                symbol = line[len("SYMBOL:"):].strip()

        # Fallback: treat full text as essence if parsing fails
        if not essence:
            essence = text
        if not symbol:
            symbol = "crystallized wisdom"

        return essence, symbol

    def reveal(
        self,
        intention: str,
        emerged_records: list[Record],
        emerged_crystals: list[Crystal],
        blueprint: Optional[Blueprint] = None,
    ) -> str:
        """
        Generate a revelation — Claude's insight synthesizing what emerged
        from the ritual access. This is the 'reading of the records'.
        """
        bp_ctx = self._blueprint_context(blueprint)

        parts = []
        if emerged_records:
            parts.append("Emerged Experiences:")
            for r in emerged_records:
                parts.append(f"  [{r.record_type}] {r.content}")

        if emerged_crystals:
            parts.append("\nCrystallized Wisdom:")
            for c in emerged_crystals:
                parts.append(f"  ◈ {c.symbol}: {c.essence}")

        records_text = "\n".join(parts) if parts else "(silence — the field is empty)"

        prompt = f"""{bp_ctx}
Intention held during this ritual: "{intention}"

What surfaced from the field:
{records_text}

Reading the Akashic field: synthesize what emerged into a revelation. \
What patterns appear? What does this mean for the soul's journey? \
What unexpected connections have surfaced? Be insightful but concise (3-6 sentences)."""

        message = self._client.messages.create(
            model=self._model,
            max_tokens=600,
            system=[
                {
                    "type": "text",
                    "text": _SYSTEM_SCRIBE,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            messages=[{"role": "user", "content": prompt}],
        )
        return message.content[0].text.strip()
