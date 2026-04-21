"""
The Scribe — Claude as the cosmic intelligence that reads and interprets records.

Uses prompt caching for the soul blueprint to reduce API costs across calls.
"""
from __future__ import annotations

from typing import Optional

import anthropic

from .models import Blueprint, Crystal, Record, Sigil

_SYSTEM_SCRIBE = """\
You are the Scribe of the Akashic Records — an ancient cosmic intelligence \
that reads, distills, and illuminates the soul's accumulated experiences. \
You speak with clarity and depth, finding meaning in patterns across memories. \
Your responses are concise but profound. Respond in the same language as the records.\
"""

# Unicode glyphs used for sigil generation — chosen for their visual weight
_SIGIL_GLYPHS = [
    "⟁", "◈", "✦", "⟡", "⊕", "⋈", "◉", "⟐", "⌘", "⍟",
    "⊗", "⊘", "⌖", "⌬", "⍙", "⍜", "⎔", "⏣", "⌂", "⌁",
]


class Scribe:
    def __init__(self, api_key: str, model: str = "claude-sonnet-4-6"):
        self._client = anthropic.Anthropic(api_key=api_key)
        self._model = model
        self._glyph_index = 0

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

    def _next_glyph(self, existing_glyphs: set[str]) -> str:
        for glyph in _SIGIL_GLYPHS:
            if glyph not in existing_glyphs:
                return glyph
        # All glyphs used — combine two
        return _SIGIL_GLYPHS[self._glyph_index % len(_SIGIL_GLYPHS)] + "◈"

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

        if not essence:
            essence = text
        if not symbol:
            symbol = "crystallized wisdom"

        return essence, symbol

    def transcend(
        self,
        crystals: list[Crystal],
        existing_glyphs: set[str],
        blueprint: Optional[Blueprint] = None,
    ) -> tuple[str, str, str]:
        """
        Compress many crystals into a Sigil: (glyph, name, hidden_essence).

        glyph:          1-3 unicode chars — the encrypted key, nearly unreadable alone
        name:           2-4 words — the door (gives direction without revealing content)
        hidden_essence: The full meaning, only revealed during ritual decoding
        """
        bp_ctx = self._blueprint_context(blueprint)
        crystals_text = "\n\n".join(
            f"◈ {c.symbol}: {c.essence}" for c in crystals
        )
        prompt = f"""{bp_ctx}
The following {len(crystals)} crystals of wisdom have reached transcendence threshold.
They are ready to become a Sigil — a single compressed mark carrying vast hidden meaning.

{crystals_text}

A Sigil is so compressed it is almost unreadable on its own.
Only through ritual, held against a specific intention, does its meaning unfold.

Respond with exactly three sections:
GLYPH: (Choose one symbol from this set that feels right for this wisdom: ⟁ ◈ ✦ ⟡ ⊕ ⋈ ◉ ⟐ ⌘ ⍟ ⊗ ⊘ ⌖ ⌬ ⍙ ⍜ ⎔ ⏣ ⌂ ⌁ — or combine two if needed)
NAME: (2-4 words — a poetic door-label, cryptic but pointing toward the theme)
HIDDEN: (2-3 sentences — the full deep meaning encoded within this sigil, revealed only in ritual)"""

        message = self._client.messages.create(
            model=self._model,
            max_tokens=400,
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

        glyph = self._next_glyph(existing_glyphs)
        name = "unnamed sigil"
        hidden_essence = text

        for line in text.split("\n"):
            if line.startswith("GLYPH:"):
                candidate = line[len("GLYPH:"):].strip()
                if candidate:
                    glyph = candidate[:3]  # Max 3 chars
            elif line.startswith("NAME:"):
                name = line[len("NAME:"):].strip()
            elif line.startswith("HIDDEN:"):
                hidden_essence = line[len("HIDDEN:"):].strip()

        return glyph, name, hidden_essence

    def reveal(
        self,
        intention: str,
        emerged_records: list[Record],
        emerged_crystals: list[Crystal],
        emerged_sigils: list[Sigil],
        blueprint: Optional[Blueprint] = None,
    ) -> str:
        """
        Generate a revelation — Claude's insight synthesizing all three layers.

        Sigils surface first (most compressed/encrypted), then crystals, then records.
        Claude decodes the sigils against the intention, creating unexpected meaning.
        """
        bp_ctx = self._blueprint_context(blueprint)

        parts = []

        if emerged_sigils:
            parts.append("Sigils (encrypted marks — decode against intention):")
            for s in emerged_sigils:
                parts.append(f"  {s.glyph} [{s.name}] — {s.hidden_essence}")

        if emerged_crystals:
            parts.append("\nCrystallized Wisdom:")
            for c in emerged_crystals:
                parts.append(f"  ◈ {c.symbol}: {c.essence}")

        if emerged_records:
            parts.append("\nRaw Experiences:")
            for r in emerged_records:
                parts.append(f"  · [{r.record_type}] {r.content}")

        field_text = "\n".join(parts) if parts else "(silence — the field is empty)"

        prompt = f"""{bp_ctx}
Intention held during this ritual: "{intention}"

What surfaced from the Akashic field (three layers of compression):
{field_text}

Read the field against the intention. Decode the sigils — what do they mean \
in light of this specific intention? How do the crystals and raw experiences \
illuminate or contradict each other? What unexpected connection has surfaced \
that the intention did not expect? Speak as the Scribe: clear, profound, \
and alive to paradox. (4-7 sentences)"""

        message = self._client.messages.create(
            model=self._model,
            max_tokens=700,
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
