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
``SEARCH_V3A`` (``search-v3a``) is HID-search-v3a (PROTOCOL_hierarchy_search_v3a.md):
``hid_full`` (k = 1) and ``hid_refine4`` (k = 4), the nine baselines and the portfolio,
with a direct stage-B trace sidecar per HID row and a replicate-parity HID job order.
Its two development studies run one arm each on retained search-v2 inputs.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from .baselines import BASELINE_METHODS

HID_KINDS = ("hid_v1", "hid_v2", "hid_v3a")
V3A_REGISTRIES = {"search-v3a": ("hid_full", "hid_refine4"),
                  "search-v3a-dev-control": ("hid_full",),
                  "search-v3a-dev-treatment": ("hid_refine4",)}

PKG = Path(__file__).resolve().parent
ID_ROOT = PKG.parent
REPO = ID_ROOT.parent


@dataclass(frozen=True)
class MethodSpec:
    name: str
    kind: str                    # "hid_v1" | "hid_v2" | "hid_v3a" | "baseline" | "portfolio"
    config: object = None

    @property
    def is_hid(self) -> bool:
        return self.kind in HID_KINDS


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
    if name in V3A_REGISTRIES:
        from .search_v3a import ARMS_V3A
        hid = tuple(MethodSpec(m, "hid_v3a", ARMS_V3A[m]) for m in V3A_REGISTRIES[name])
        return hid + (_baseline_specs() if name == "search-v3a" else ())
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
    trace_sidecars: bool = False                 # HID workers write a stage-B trace sidecar

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

    def job_methods(self, case) -> tuple[str, ...]:
        """Dispatch order of one case's encoder jobs (default: registry order)."""
        return self.encode_methods

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


class V3aStudy(StudySpec):
    """HID-search-v3a: HID control then treatment for even replicates, treatment then
    control for odd replicates, then the baselines in owner order (BENCHMARK.md 3)."""

    def job_methods(self, case) -> tuple[str, ...]:
        hid = self.hid_methods if case.replicate % 2 == 0 else tuple(reversed(self.hid_methods))
        return hid + self.baselines

    def role_cases(self, role: str, run_dir: Path | None = None):
        """Reserved roles are generated only for a run whose freeze VALIDATES now
        (hashes, closure, configs, design, snapshot), not merely one that exists."""
        spec = self.role(role)
        if spec.reserved and spec.source == "generate":
            from . import freeze_v2
            from .study_corpus import ReservedAccessError
            if run_dir is None or not (run_dir / "freeze.json").is_file():
                raise ReservedAccessError(f"role {role} is reserved; no freeze in {run_dir}")
            if run_dir.resolve() != self.run_dir(run_dir.name).resolve():
                raise ReservedAccessError(f"{run_dir} is not a run directory of {self.name}")
            _, _, problems = freeze_v2.load_and_validate(self, run_dir.name)
            if problems:
                raise ReservedAccessError("freeze does not validate; reserved generation "
                                          "refused: " + "; ".join(problems[:5]))
        return super().role_cases(role, run_dir)


V3A_ALLOWANCES = (("development", 14400.0), ("prospective", 10800.0),
                  ("report_verification", 3600.0))
V3A_RESOURCES = ResourcePolicy(allowances_s=V3A_ALLOWANCES, total_budget_s=28800.0)
V2_RUN = "index-deconvolution/results/hierarchy_search_v2/search-confirm-v2-r1"

SEARCH_V3A_ROLES = (
    RoleSpec("boundary", ("F12",), (4096,), tuple(range(6000, 6020)), "prospective_target",
             rng_namespace="search_v3a_confirmation", reserved=True),
    RoleSpec("boundary_large", ("F12",), (16384, 65536, 131072), tuple(range(7000, 7020)),
             "prospective_target", rng_namespace="search_v3a_transfer", reserved=True),
    RoleSpec("boundary_stress", ("S02",), (4096, 65536), tuple(range(8000, 8020)),
             "prospective_target", rng_namespace="search_v3a_stress", reserved=True),
    RoleSpec("controls", ("F01", "F06", "F07", "F11"), (4096,), (9000, 9001),
             "prospective_control", rng_namespace="search_v3a_controls", reserved=True),
)
SEARCH_V3A = V3aStudy(
    name="search-v3a", result_root=ID_ROOT / "results" / "hierarchy_search_v3a",
    registry="search-v3a", roles=SEARCH_V3A_ROLES,
    default_roles=("boundary", "boundary_large", "boundary_stress", "controls"),
    resources=V3A_RESOURCES, trace_sidecars=True)

# Development: retained search-v2 confirmation inputs, one arm per study. Inputs are
# decoded from the retained raw archives by the development adapter (the v2 manifest
# schema differs from the HID-v1 one ``study_corpus.retained_cases`` reads).
_V3A_DEV_ROLES = tuple(
    RoleSpec(r, fams, bls, reps, "development", source="retained", retained_run=V2_RUN,
             retained_split=r)
    for r, fams, bls, reps in (("confirmation", ALL12, (256, 1024, 4096), tuple(range(3000, 3020))),
                               ("transfer", ALL12, (16384, 65536, 131072), tuple(range(5000, 5004))),
                               ("stress", ("S01", "S02"), (4096, 65536), tuple(range(4000, 4008)))))
SEARCH_V3A_DEV_CONTROL = StudySpec(
    name="search-v3a-dev-control", result_root=SEARCH_V3A.result_root,
    registry="search-v3a-dev-control", roles=_V3A_DEV_ROLES, resources=V3A_RESOURCES,
    trace_sidecars=True)
SEARCH_V3A_DEV_TREATMENT = StudySpec(
    name="search-v3a-dev-treatment", result_root=SEARCH_V3A.result_root,
    registry="search-v3a-dev-treatment", roles=_V3A_DEV_ROLES, resources=V3A_RESOURCES,
    trace_sidecars=True)

_STUDIES: dict[str, StudySpec] = {s.name: s for s in (
    LEGACY, SEARCH_V2, SEARCH_V3A, SEARCH_V3A_DEV_CONTROL, SEARCH_V3A_DEV_TREATMENT)}


def get_study(name: str) -> StudySpec:
    try:
        return _STUDIES[name]
    except KeyError:
        raise KeyError(f"unknown study {name!r}; known: {sorted(_STUDIES)}") from None


def register_fixture_study(spec: StudySpec) -> None:
    """Explicit registration of a fixture study (tests only; never a production name)."""
    if not spec.fixture or spec.name in (LEGACY.name, SEARCH_V2.name, SEARCH_V3A.name,
                                         SEARCH_V3A_DEV_CONTROL.name, SEARCH_V3A_DEV_TREATMENT.name):
        raise ValueError("only fixture studies with new names may be registered")
    for r in spec.roles:
        if r.source == "generate" and r.rng_namespace not in ("search_v2_fixture",
                                                               "search_v3a_fixture"):
            raise ValueError("fixture studies may generate only a fixture namespace")
    _STUDIES[spec.name] = spec
