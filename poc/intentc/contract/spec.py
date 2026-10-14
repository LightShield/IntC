"""Intent specification Phi = <Phi_func, B, O> loaded from YAML.

Phi_func = <Pre, Post, I>:
- I    : `parameters` - named #define constants of the program with constraints
         (expressions over parameter names, e.g. "CAPACITY >= 1000").
- Pre, Post: `harnesses` - C files whose nondet_*/assume express Pre and whose
         assertions express Post. Each harness sees the candidate's parameter values
         through a generated header `intent_params.h`.
- B    : `budget` - e.g. {static_memory_bytes: 8000}
- O    : `objective` - a benchmark driver measured by winner selection.
"""

from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, field_validator


class Parameter(BaseModel):
    model_config = ConfigDict(frozen=True)
    name: str
    bits: int = 64
    constraints: list[str]


class Harness(BaseModel):
    model_config = ConfigDict(frozen=True)
    file: Path
    entry: str = "harness"
    unwind: int
    defines: dict[str, str] = {}
    note: str = ""


class Objective(BaseModel):
    model_config = ConfigDict(frozen=True)
    metric: str = "latency_ns"
    bench: Path          # C driver printing one number per run (lower is better)
    trials: int = 15


class Contract(BaseModel):
    model_config = ConfigDict(frozen=True)
    name: str
    baseline: Path
    parameters: list[Parameter]
    harnesses: list[Harness]
    budget: dict[str, int] = {}
    objective: Objective | None = None
    verify_timeout_s: float = 120.0
    kappa_threshold: int = 2  # TheoryLower stops once kappa_V <= this
    cegis_max_tries: int = 16  # Appendix B.1 attempt cap

    @field_validator("harnesses")
    @classmethod
    def _non_empty(cls, v: list[Harness]) -> list[Harness]:
        if not v:
            raise ValueError("a contract needs at least one harness (Post)")
        return v

    @field_validator("cegis_max_tries")
    @classmethod
    def _positive_cap(cls, v: int) -> int:
        if v < 1:
            raise ValueError("cegis_max_tries must be at least 1")
        return v


def load(path: Path) -> Contract:
    """Load a contract; relative paths are resolved against the contract's directory."""
    path = Path(path)
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    base = path.parent

    def rel(p: str | Path) -> Path:
        q = Path(p)
        return q if q.is_absolute() else (base / q).resolve()

    data["baseline"] = rel(data["baseline"])
    for h in data.get("harnesses", []):
        h["file"] = rel(h["file"])
    if data.get("objective"):
        data["objective"]["bench"] = rel(data["objective"]["bench"])
    return Contract.model_validate(data)
