"""Freeze: sha256 of the packet, accepted documents, declarations and every source used in
scientific computation or verification (imported owners found via sys.modules)."""
import hashlib, json, os, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, *[".."] * 4))
sys.path.insert(0, HERE)
import study  # noqa: E402
import run  # noqa: E402,F401

if os.path.exists(os.path.join(HERE, "freeze.json")):
    print("freeze.json exists; refusing"); sys.exit(2)
rel = lambda p: os.path.relpath(os.path.abspath(p), ROOT)
loaded = sorted({rel(m.__file__) for m in list(sys.modules.values())
                 if getattr(m, "__file__", None) and os.path.abspath(m.__file__).startswith(ROOT)})
DES = "index-deconvolution/results/causal_abstraction_design"
CLO = f"{DES}/review_closure/abstraction-design-v1-r1"
SUP = f"{DES}/supervision/abstraction-design-v1-r1-closure"
CT = "index-deconvolution/results/causal_target_v1/review_closure/causal-target-spec-v1-r1/corrected"
docs = [f"{SUP}/NEXT_CLAUDE.md", f"{SUP}/REVIEW.md", f"{CLO}/OWNERSHIP_TICKET.md"] + \
       [f"{CLO}/corrected/{d}.md" for d in ("DESIGN", "MODEL_AND_MAPS", "EVIDENCE_AND_LIMITS", "DECISION",
                                            "DRAFT_EXECUTION_PROTOCOL")] + \
       [f"{CT}/ABSTRACTION_CONTRACT.md", f"{CT}/EVALUATION_SPEC.md", study.EGFR]
run_local = [rel(os.path.join(HERE, f)) for f in ("fixtures.json", "study.py", "run.py", "audit_oracle.py",
             "test_study.py", "mutations.py", "verify_inputs.py", "preserve.py")]
extra = ["index-deconvolution/tests/test_abstraction.py", "index-deconvolution/src/bnet.py",
         "index-deconvolution/src/causalbool.py"]
files = sorted(set(docs + run_local + loaded + extra) - {rel(__file__)})
H = lambda p: hashlib.sha256(open(os.path.join(ROOT, p), "rb").read()).hexdigest()
fz = {"run_id": "abstraction-validation-v1-r1", "frozen_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
      "draft_protocol_sha256": H(f"{CLO}/corrected/DRAFT_EXECUTION_PROTOCOL.md"),
      "imported_modules_under_repo": loaded, "import_origins": study.import_origins(),
      "files": {p: H(p) for p in files}}
json.dump(fz, open(os.path.join(HERE, "freeze.json"), "w"), indent=1)
print("frozen", len(files), "files;", "imports:", loaded)
