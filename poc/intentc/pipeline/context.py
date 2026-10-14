"""State threaded through the IntentCompile stages."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from intentc.verify.cbmc import Result
from intentc.contract import Contract
from intentc.syntax import Sketch


@dataclass
class Candidate:
    name: str
    code: str
    params: dict[str, int]
    proofs: list[Result]           # one CBMC result per harness, all "proved"
    applied: tuple[str, ...] = ()
    static_memory: int | None = None
    measured: float | None = None  # median of the objective metric
    measured_stats: object | None = None


@dataclass
class StepRecord:
    stage: str
    ok: bool
    seconds: float
    details: str


@dataclass
class Context:
    contract: Contract
    workdir: Path
    output: Path | None = None
    baseline_code: str = ""
    baseline_params: dict[str, int] = field(default_factory=dict)
    sketches: list[Sketch] = field(default_factory=list)
    lower_report: str = ""
    seeds: list[Candidate] = field(default_factory=list)
    pool: list[Candidate] = field(default_factory=list)
    winner: Candidate | None = None
    baseline_measured: float | None = None
    baseline_stats: object | None = None
    steps: list[StepRecord] = field(default_factory=list)
    log: list[str] = field(default_factory=list)
