"""Load and hash the bounded versioned prompt files."""

from __future__ import annotations

import hashlib
from enum import Enum
from pathlib import Path


class PromptName(str, Enum):
    SHARED = "shared_editorial_context.v1.md"
    CANONICAL_STANDARD = "canonical_editorial_standard.v1.md"
    CONDITION_A = "condition_a.v1.md"
    CONDITION_B = "condition_b.v1.md"
    CONDITION_B_SELF_REVIEW = "condition_b_self_review.v1.md"
    CONDITION_C_CREATOR = "condition_c_creator.v1.md"
    CONDITION_C_EVALUATOR = "condition_c_evaluator.v1.md"
    CONDITION_C_REVISION = "condition_c_revision.v1.md"


_PROMPT_ROOT = Path(__file__).with_name("prompts")


def load_prompt(name: PromptName) -> str:
    """Load exactly one checked-in prompt asset as UTF-8 text."""
    return (_PROMPT_ROOT / name.value).read_text(encoding="utf-8")


def load_prompt_body(name: PromptName) -> str:
    """Load model-visible prompt text with the metadata frontmatter removed."""
    return strip_prompt_frontmatter(load_prompt(name))


def strip_prompt_frontmatter(payload: str) -> str:
    """Remove the repository's small, required YAML-style metadata envelope."""
    lines = payload.splitlines(keepends=True)
    if not lines or lines[0].strip() != "---":
        msg = "prompt asset is missing opening frontmatter delimiter"
        raise ValueError(msg)
    closing_index = next((index for index, line in enumerate(lines[1:], start=1) if line.strip() == "---"), None)
    if closing_index is None:
        msg = "prompt asset is missing closing frontmatter delimiter"
        raise ValueError(msg)
    metadata = "".join(lines[1:closing_index])
    if "prompt_version:" not in metadata:
        msg = "prompt asset frontmatter is missing prompt_version"
        raise ValueError(msg)
    body = "".join(lines[closing_index + 1 :]).lstrip("\r\n")
    if not body.strip():
        msg = "prompt asset body is empty"
        raise ValueError(msg)
    return body


def prompt_digest(name: PromptName) -> str:
    """Hash the exact prompt bytes; line endings are part of the freeze."""
    payload = (_PROMPT_ROOT / name.value).read_bytes()
    return f"sha256:{hashlib.sha256(payload).hexdigest()}"


def all_prompt_digests() -> dict[str, str]:
    """Return manifest-compatible prompt keys and content digests."""
    return {
        "shared_editorial_context": prompt_digest(PromptName.SHARED),
        "canonical_editorial_standard": prompt_digest(PromptName.CANONICAL_STANDARD),
        "condition_a": prompt_digest(PromptName.CONDITION_A),
        "condition_b": prompt_digest(PromptName.CONDITION_B),
        "condition_b_self_review": prompt_digest(PromptName.CONDITION_B_SELF_REVIEW),
        "condition_c_creator": prompt_digest(PromptName.CONDITION_C_CREATOR),
        "condition_c_evaluator": prompt_digest(PromptName.CONDITION_C_EVALUATOR),
        "condition_c_revision": prompt_digest(PromptName.CONDITION_C_REVISION),
    }
