"""Explicit, immutable study specifications and method registries.

A study declares its result root, roles (the design's splits), RNG namespaces, case
design, method registry, resource policy and run plans. Orchestration (benchmark,
validation, report, cli) receives the study object explicitly; nothing is selected by
patching module globals, and method dispatch reads the registry's declared ``kind``,
never a name prefix.

``LEGACY`` (``hid-v1``) is the default and reproduces the frozen HID-v1 behaviour:
its roles are read from ``corpus.SPLITS`` and its methods from ``infer.ABLATIONS``.
``SEARCH_V2`` (``search-v2``) is HID-search-v2 (PROTOCOL_hierarchy_search_v2.md):
six cumulative HID arms, the same nine baselines and the derived portfolio row.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from .baselines import BASELINE_METHODS

PKG = Path(__file__).resolve().parent
ID_ROOT = PKG.parent
REPO = ID_ROOT.parent


@dataclass(frozen=True)
class MethodSpec:
    name: str
    kind: str                    # "hid_v1" | "hid_v2" | "baseline" | "portfolio"
    config: object = None

    @property
    def is_hid(self) -> bool:
        return self.kind in ("hid_v1", "hid_v2")


@dataclass(frozen=True)
class RoleSpec:
    name: str
    families: tuple
    base_lengths: tuple
    replicates: tuple
    evidence_role: str
    case_prefix: str | None = None
    source: str = "generate"     # "generate" | "retained"
    rng_namespace: str | None = None
    reserved: bool = False
    retained_run: str | None = None
    retained_split: str | None = None

    @property
    def prefix(self) -> str:
        return self.case_prefix or self.name

    def as_dict(self) -> dict:
        return {"families": list(self.families), "base_lengths": list(self.base_lengths),
                "replicates": list(self.replicates), "evidence_role": self.evidence_role,
                "case_prefix": self.prefix, "source": self.source,
                "rng_namespace": self.rng_namespace, "reserved": self.reserved,
                "retained_run": self.retained_run, "retained_split": self.retained_split}


# ---------------------------------------------------------------------------
# Method registries (also resolvable by name inside an isolated worker)
# ---------------------------------------------------------------------------

def _baseline_specs() -> tuple:
    return tuple(MethodSpec(m, "baseline") for m in BASELINE_METHODS) + (
        MethodSpec("baseline_best", "portfolio"),)


def method_registry(name: str) -> tuple[MethodSpec, ...]:
    if name == "hid-v1":
        from .infer import ABLATIONS
        return tuple(MethodSpec(f"hid_{k}", "hid_v1", v) for k, v in ABLATIONS.items()) + \
            _baseline_specs()
    if name == "search-v2":
        from .search_v2 import ARMS
        return tuple(MethodSpec(k, "hid_v2", v) for k, v in ARMS.items()) + _baseline_specs()
    raise KeyError(f"unknown method registry {name!r}")


# ---------------------------------------------------------------------------
# Study specification
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ResourcePolicy:
    wall_limit_s: float = 30.0
    rss_limit_bytes: int = 1 << 30
    max_workers: int = 2
    allowances_s: tuple = ()     # ((category, seconds), ...); empty: per-run budget only
    total_budget_s: float = 6 * 3600

    def allowance(self, category: str) -> float | None:
        return dict(self.allowances_s).get(category)

    def as_dict(self) -> dict:
        return {"wall_limit_s": self.wall_limit_s, "rss_limit_bytes": self.rss_limit_bytes,
                "max_workers": self.max_workers, "allowances_s": dict(self.allowances_s),
                "total_budget_s": self.total_budget_s}


@dataclass(frozen=True)
class StudySpec:
    name: str
    result_root: Path
    registry: str
    roles: tuple = ()                            # RoleSpec, ...
    run_plans: tuple = ()                        # ((run_id_prefix, (role, ...)), ...)
    default_roles: tuple = ()
    resources: ResourcePolicy = field(default_factory=ResourcePolicy)
    fixture: bool = False

    # -- methods ---------------------------------------------------------------

    def methods(self) -> tuple[MethodSpec, ...]:
        return method_registry(self.registry)

    def method(self, name: str) -> MethodSpec:
        for m in self.methods():
            if m.name == name:
                return m
        raise KeyError(f"{name!r} is not a method of study {self.name}")

    @property
    def all_methods(self) -> tuple[str, ...]:
        return tuple(m.name for m in self.methods())

    @property
    def encode_methods(self) -> tuple[str, ...]:
        return tuple(m.name for m in self.methods() if m.kind != "portfolio")

    @property
    def hid_methods(self) -> tuple[str, ...]:
        return tuple(m.name for m in self.methods() if m.is_hid)

    @property
    def baselines(self) -> tuple[str, ...]:
        return tuple(m.name for m in self.methods() if m.kind == "baseline")

    def kinds(self) -> dict:
        return {m.name: m.kind for m in self.methods()}

    # -- roles -----------------------------------------------------------------

    def role_specs(self) -> dict[str, RoleSpec]:
        return {r.name: r for r in self.roles}

    def role(self, name: str) -> RoleSpec:
        try:
            return self.role_specs()[name]
        except KeyError:
            raise KeyError(f"{name!r} is not a role of study {self.name}") from None

    def run_roles(self, run_id: str) -> list[str]:
        for prefix, roles in self.run_plans:
            if run_id.startswith(prefix):
                return list(roles)
        return list(self.default_roles)

    def case_id(self, role: str, family, base_length, replicate, ragged) -> str:
        from .corpus import case_id
        return case_id(self.role(role).prefix, family, base_length, replicate, ragged)

    def role_cases(self, role: str, run_dir: Path | None = None):
        from . import study_corpus as SC
        spec = self.role(role)
        if spec.source == "retained":
            return SC.retained_cases(self, spec, REPO)
        return SC.generated_cases(self, spec, run_dir)

    def design_splits(self, roles) -> dict:
        return {r: {"families": self.role(r).families, "base_lengths": self.role(r).base_lengths,
                    "replicates": self.role(r).replicates, "case_prefix": self.role(r).prefix}
                for r in roles}

    # -- paths -----------------------------------------------------------------

    def run_dir(self, run_id: str) -> Path:
        if not run_id or any(c not in "abcdefghijklmnopqrstuvwxyz0123456789-_." for c in run_id):
            raise ValueError(f"run id {run_id!r} must be lowercase [a-z0-9-_.]")
        if run_id.startswith("dev"):
            return self.result_root / "development" / run_id
        return self.result_root / run_id


class LegacyStudy(StudySpec):
    """HID-v1: roles read live from ``corpus.SPLITS`` (the frozen behaviour)."""

    def role_specs(self) -> dict[str, RoleSpec]:
        from . import corpus
        return {s: RoleSpec(s, tuple(v["families"]), tuple(v["base_lengths"]),
                            tuple(v["replicates"]), evidence_role=s, rng_namespace=s)
                for s, v in corpus.SPLITS.items()}

    def role_cases(self, role: str, run_dir: Path | None = None):
        from .corpus import split_cases
        return split_cases(role)

    def run_dir(self, run_id: str) -> Path:
        from . import benchmark
        return benchmark.run_dir(run_id)


ALL12 = tuple(f"F{i:02d}" for i in range(1, 13))
R1 = "index-deconvolution/results/hierarchy_v1/confirm-v1-r1"

LEGACY = LegacyStudy(name="hid-v1", result_root=ID_ROOT / "results" / "hierarchy_v1",
                     registry="hid-v1", run_plans=(("dev", ("development",)),),
                     default_roles=("confirmation", "transfer"))

SEARCH_V2_ROLES = (
    RoleSpec("pilot_confirmation", ALL12, (1024,), (1000, 1001), "development",
             case_prefix="confirmation", source="retained", retained_run=R1,
             retained_split="confirmation"),
    RoleSpec("pilot_transfer", ALL12, (65536,), (2000, 2001), "development",
             case_prefix="transfer", source="retained", retained_run=R1,
             retained_split="transfer"),
    RoleSpec("development_confirmation", ALL12, (256, 1024, 4096), tuple(range(1000, 1020)),
             "development", case_prefix="confirmation", source="retained", retained_run=R1,
             retained_split="confirmation"),
    RoleSpec("development_transfer", ALL12, (16384, 65536), tuple(range(2000, 2004)),
             "development", case_prefix="transfer", source="retained", retained_run=R1,
             retained_split="transfer"),
    RoleSpec("confirmation", ALL12, (256, 1024, 4096), tuple(range(3000, 3020)),
             "confirmation", rng_namespace="search_v2_confirmation", reserved=True),
    RoleSpec("transfer", ALL12, (16384, 65536, 131072), tuple(range(5000, 5004)),
             "transfer", rng_namespace="search_v2_transfer", reserved=True),
    RoleSpec("stress", ("S01", "S02"), (4096, 65536), tuple(range(4000, 4008)),
             "stress", rng_namespace="search_v2_stress", reserved=True),
)

SEARCH_V2 = StudySpec(
    name="search-v2", result_root=ID_ROOT / "results" / "hierarchy_search_v2",
    registry="search-v2", roles=SEARCH_V2_ROLES,
    run_plans=(("dev-search-v2-pilot", ("pilot_confirmation", "pilot_transfer")),
               ("dev-search-v2-regression", ("development_confirmation",
                                             "development_transfer"))),
    default_roles=("confirmation", "transfer", "stress"),
    resources=ResourcePolicy(allowances_s=(("development", 4 * 3600.0),
                                           ("reserved", 6 * 3600.0),
                                           ("diagnostics_verification", 2 * 3600.0)),
                             total_budget_s=12 * 3600.0))

_STUDIES: dict[str, StudySpec] = {LEGACY.name: LEGACY, SEARCH_V2.name: SEARCH_V2}


def get_study(name: str) -> StudySpec:
    try:
        return _STUDIES[name]
    except KeyError:
        raise KeyError(f"unknown study {name!r}; known: {sorted(_STUDIES)}") from None


def register_fixture_study(spec: StudySpec) -> None:
    """Explicit registration of a fixture study (tests only; never a production name)."""
    if not spec.fixture or spec.name in (LEGACY.name, SEARCH_V2.name):
        raise ValueError("only fixture studies with new names may be registered")
    for r in spec.roles:
        if r.source == "generate" and r.rng_namespace != "search_v2_fixture":
            raise ValueError("fixture studies may generate only the search_v2_fixture namespace")
    _STUDIES[spec.name] = spec
