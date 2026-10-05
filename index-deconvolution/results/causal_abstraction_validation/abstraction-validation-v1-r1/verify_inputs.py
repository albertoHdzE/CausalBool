"""Verify the accepted inputs before work: corrected draft sha256, closure manifests,
supervision manifest, and record identities of packet, review and contracts."""
import hashlib, json, os, sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), *[".."] * 4))
H = lambda p: hashlib.sha256(open(os.path.join(ROOT, p), "rb").read()).hexdigest()
DES = "index-deconvolution/results/causal_abstraction_design"
CLO = f"{DES}/review_closure/abstraction-design-v1-r1"
SUP = f"{DES}/supervision/abstraction-design-v1-r1-closure"
CT = "index-deconvolution/results/causal_target_v1/review_closure/causal-target-spec-v1-r1/corrected"
checks, fails = [], []
draft = H(f"{CLO}/corrected/DRAFT_EXECUTION_PROTOCOL.md")
checks.append(("draft_sha", draft == "876c43401eaeee313e110969610782248999784c848b935a52ad9d0ce447cb68"))
for man in (f"{CLO}/input_manifest.json", f"{CLO}/output_manifest.json", f"{SUP}/manifest.json"):
    m = json.load(open(os.path.join(ROOT, man)))
    entries = m.get("inputs_read") or m.get("outputs") or []
    bad = [e["path"] for e in entries if H(e["path"]) != e["sha256"]]
    checks.append((f"{man} ({len(entries)} entries)", not bad and len(entries) > 0))
    fails += bad
locked = [f"{SUP}/NEXT_CLAUDE.md", f"{SUP}/REVIEW.md", f"{SUP}/audit_acceptance.json",
          f"{CLO}/OWNERSHIP_TICKET.md", f"{CLO}/HANDOFF.md"] + \
         [f"{CLO}/corrected/{d}.md" for d in ("DESIGN", "MODEL_AND_MAPS", "EVIDENCE_AND_LIMITS",
                                              "DECISION", "DRAFT_EXECUTION_PROTOCOL")] + \
         [f"{CT}/ABSTRACTION_CONTRACT.md", f"{CT}/EVALUATION_SPEC.md"]
out = {"checks": [{"check": c, "pass": p} for c, p in checks], "failures": fails,
       "locked_inputs": {p: H(p) for p in locked}}
out["pass"] = all(p for _, p in checks)
json.dump(out, open(os.path.join(os.path.dirname(__file__), "input_verification.json"), "w"), indent=1)
print(json.dumps(out["checks"]), "PASS" if out["pass"] else "FAIL")
sys.exit(0 if out["pass"] else 1)
