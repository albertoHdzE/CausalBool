"""Stage C cohort: re-check, generate and fingerprint seeds 980000-980199.

Parent plan section 5 and resume section 5. Order of operations (each recorded):

1. INVENTORY (before generation): every text file under ``results/``, ``plan/``,
   ``research/``, ``research_tests/``, ``tests_direct/`` and ``.reference/`` is
   scanned for any of the 200 seeds as a whole token and for generated program
   names ``additional_98xxxx``. Hits are listed with their context; a hit that is
   a generated program or an outcome record is EXPOSURE (``DESIGN_INVALID``).
   Mentions of the reservation range in plans/protocols are expected and listed.
2. PRIOR COHORTS: every seed range declared by any ``plan/*/PROTOCOL.json`` (keys
   ``first``/``last`` or ``first_seed``/``last_seed``), the direct acceptance corpus
   (public, regression, additional, stress) and the fixture recipes -- generated
   with the unchanged generator, three digests each.
3. GENERATE the 200 programs (40 per family, ``seed % 5``) and write them to
   ``cohort/programs/<seed>.json``.
4. DIGESTS per program: ``program_digest`` (full program, row identity),
   ``program_semantic_digest`` (top-level name removed) and the compilation-input
   digest (sha256 of canonical JSON without top-level ``name`` and ``cases``).
   Any duplicate compilation input within the cohort or against a prior cohort
   invalidates the design; no reseeding.
"""

from __future__ import annotations

import collections
import json
import re
from pathlib import Path
from typing import Dict, List

from research import optimization_common as oc
from research import structural_encoding as se
from research import third_round_common as tc

from tests_direct import generate_programs as gp

SCAN_ROOTS = ("results", "plan", "research", "research_tests", "tests_direct", ".reference")
TEXT_SUFFIXES = {".json", ".jsonl", ".md", ".py", ".txt", ".tsv", ".csv", ".log", ".tex"}


def compilation_digest(program: dict) -> str:
    return oc.object_sha256({k: v for k, v in program.items() if k not in ("name", "cases")})


def digests(program: dict) -> dict:
    return {"program_sha256": gp.program_digest(program),
            "semantic_sha256": se.program_semantic_digest(program),
            "compilation_input_sha256": compilation_digest(program)}


def inventory(exclude: Path) -> dict:
    seeds = range(tc.CONFIRMATION[0], tc.CONFIRMATION[1] + 1)
    # A seed is a whole token: not inside a hex digest, identifier, decimal or path.
    token = re.compile(r"(?<![0-9A-Za-z_.])(98(?:0[0-1][0-9]{2}))(?![0-9A-Za-z_.])")
    wanted = {str(s) for s in seeds}
    hits: List[dict] = []
    scanned = 0
    for root in SCAN_ROOTS:
        for path in (oc.ROOT / root).rglob("*"):
            if not path.is_file() or path.suffix not in TEXT_SUFFIXES:
                continue
            if exclude in path.parents or "__pycache__" in path.parts:
                continue
            scanned += 1
            try:
                text = path.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            for match in token.finditer(text):
                if match.group(1) in wanted:
                    start = max(0, match.start() - 60)
                    hits.append({"file": str(path.relative_to(oc.ROOT)), "seed": match.group(1),
                                 "context": text[start:match.end() + 60].replace("\n", " ")})
    by_file = collections.Counter(h["file"] for h in hits)
    exposure = [h for h in hits if "additional_98" in h["context"]
                or h["file"].endswith(".jsonl")
                or re.search(r'"seed": ?98', h["context"])]
    return {"scanned_files": scanned, "hits": len(hits), "files": dict(by_file),
            "hit_examples": hits[:40], "exposure_hits": exposure[:40],
            "exposure": bool(exposure)}


def prior_cohorts() -> Dict[str, dict]:
    ranges = set()
    for protocol in sorted((oc.ROOT / "plan").glob("*/PROTOCOL.json")):
        text = protocol.read_text()

        def walk(obj):
            if isinstance(obj, dict):
                for a, b in (("first", "last"), ("first_seed", "last_seed")):
                    if isinstance(obj.get(a), int) and isinstance(obj.get(b), int):
                        ranges.add((obj[a], obj[b]))
                for v in obj.values():
                    walk(v)
            elif isinstance(obj, list):
                for v in obj:
                    walk(v)
        walk(json.loads(text))
    ranges.discard(tc.CONFIRMATION)
    out: Dict[str, dict] = {}
    for first, last in sorted(ranges):
        for seed in range(first, last + 1):
            out[f"generated:{seed}"] = digests(gp.additional_program(seed))
    for label, programs in (("public", gp.public_programs()),
                            ("regression", gp.regression_programs()),
                            ("additional", gp.additional_programs()),
                            ("stress", gp.stress_programs())):
        for program in programs:
            out[f"corpus:{label}:{program['name']}"] = digests(program)
    out["_ranges"] = {"ranges": sorted(ranges)}
    return out


def build(run: Path) -> dict:
    run = Path(run)
    inv = inventory(exclude=run)
    prior = prior_cohorts()
    ranges = prior.pop("_ranges")["ranges"]
    prior_ci = collections.defaultdict(list)
    for label, d in prior.items():
        prior_ci[d["compilation_input_sha256"]].append(label)
    programs, seen = {}, collections.defaultdict(list)
    folder = run / "cohort" / "programs"
    folder.mkdir(parents=True, exist_ok=True)
    for seed in range(tc.CONFIRMATION[0], tc.CONFIRMATION[1] + 1):
        program = gp.additional_program(seed)
        d = digests(program)
        path = folder / f"{seed}.json"
        path.write_text(json.dumps(program, sort_keys=True))
        programs[str(seed)] = dict(d, family=tc.family_of(seed), path=str(path),
                                   file_sha256=oc.file_sha256(path))
        seen[d["compilation_input_sha256"]].append(seed)
    within = {k: v for k, v in seen.items() if len(v) > 1}
    against = {str(s): prior_ci[p["compilation_input_sha256"]] for s, p in programs.items()
               if p["compilation_input_sha256"] in prior_ci}
    families = collections.Counter(p["family"] for p in programs.values())
    valid = (not inv["exposure"] and not within and not against
             and all(families[f] == 40 for f in tc.FAMILIES) and len(programs) == 200)
    return {"inventory": inv, "prior_ranges": ranges, "prior_programs": len(prior),
            "programs": programs, "family_counts": dict(families),
            "duplicates_within": within, "duplicates_against_prior": against,
            "verdict": "VALID" if valid else "DESIGN_INVALID"}
