"""Circom export and execution helpers for serialized quadratic systems."""

import json
import os
import re
import resource
import subprocess
import sys
import time
from pathlib import Path

from . import FIELD_PRIME


_CIRCOM_VERSION = "2.2.3"
_SNARKJS_VERSION = "0.7.6"
_DECIMAL = re.compile(r"^[+-]?\d+$")


def _as_dict(system):
    if hasattr(system, "to_dict"):
        system = system.to_dict()
    if not isinstance(system, dict):
        raise ValueError("system must be a serialized constraint system")
    if system.get("version") != "oxparc-r1cs-v1":
        raise ValueError("unsupported constraint system version")
    if system.get("prime") != str(FIELD_PRIME):
        raise ValueError("challenge constraint field required")
    names = []
    for group in ("public_inputs", "private_inputs", "auxiliary_signals"):
        values = system.get(group)
        if not isinstance(values, list) or any(not isinstance(x, str) or not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*", x) for x in values):
            raise ValueError(f"{group} must be a list of names")
        names.extend(values)
    if len(set(names)) != len(names):
        raise ValueError("duplicate signal name")
    constraints = system.get("constraints")
    if not isinstance(constraints, list):
        raise ValueError("constraints must be a list")
    return system, names


def _linear(expression):
    if not isinstance(expression, dict) or set(expression) != {"constant", "terms"}:
        raise ValueError("malformed linear expression")
    constant = expression["constant"]
    terms = expression["terms"]
    if not isinstance(constant, str) or not _DECIMAL.fullmatch(constant):
        raise ValueError("linear constant must be decimal")
    if not isinstance(terms, dict):
        raise ValueError("linear terms must be an object")
    pieces = [f"({constant})"]
    for name, coefficient in terms.items():
        if not isinstance(name, str) or not isinstance(coefficient, str) or not _DECIMAL.fullmatch(coefficient):
            raise ValueError("linear terms must contain decimal coefficients")
        pieces.append(f"({coefficient})*{name}")
    # Balanced syntax preserves the linear expression while avoiding a deep
    # parser tree for the 4095-bit nontrivial-factor sums in Q8.
    while len(pieces) > 1:
        pieces = ['(' + pieces[i] + '+' + pieces[i+1] + ')'
                  if i+1 < len(pieces) else pieces[i]
                  for i in range(0, len(pieces), 2)]
    return pieces[0]


def export_circom(system, path):
    """Write a generic Circom 2.2.3 source file and return its path."""
    system, names = _as_dict(system)
    public = system["public_inputs"]
    rows = system["constraints"]
    # Hoisted: this set was rebuilt three times per row, which made the export
    # quadratic in the row count and cost 327s on the 64-bit Q7 system.
    declared = set(names)
    for row in rows:
        if not isinstance(row, dict) or set(row) != {"A", "B", "C", "label"}:
            raise ValueError("malformed constraint row")
        if not isinstance(row["label"], str):
            raise ValueError("constraint label must be a string")
        for key in ("A", "B", "C"):
            _linear(row[key])
            if not set(row[key]['terms']) <= declared:
                raise ValueError('undeclared signal in constraint')
    lines = [f"pragma circom {_CIRCOM_VERSION};", "", "template Main() {"]
    lines.extend(f"    signal input {name};" for name in names)
    lines.append("")
    for row in rows:
        lines.append(f"    {_linear(row['A'])} * {_linear(row['B'])} === {_linear(row['C'])};")
    lines.append("}")
    lines.append("")
    if public:
        lines.append("component main {public [" + ", ".join(public) + "]} = Main();")
    else:
        lines.append("component main = Main();")
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return destination


def _run(command, *, timeout):
    started = time.monotonic()
    try:
        result = subprocess.run(command, check=False, capture_output=True, text=True, timeout=timeout)
    except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
        raise RuntimeError(f"command failed: {' '.join(map(str, command))}") from exc
    elapsed = time.monotonic() - started
    peak = resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss * (1 if sys.platform == 'darwin' else 1024)
    if peak > 4 * 1024**3:
        raise RuntimeError('child peak memory exceeded the 4 GiB budget')
    if result.returncode:
        detail = result.stderr.strip() or result.stdout.strip()
        raise RuntimeError(f"command exited {result.returncode}: {' '.join(map(str, command))}: {detail}")
    return {"command": [str(x) for x in command], "exit": result.returncode, "elapsed": elapsed,
            "peak_child_rss_bytes": peak, "resource_outcome": "within limits",
            "stdout": result.stdout, "stderr": result.stderr}


def _version(tool, expected, flag="--version"):
    command = [str(tool), flag]
    started = time.monotonic()
    try:
        result = subprocess.run(command, check=False, capture_output=True, text=True, timeout=30)
    except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
        raise RuntimeError(f"version check failed: {' '.join(command)}") from exc
    output = result.stdout + result.stderr
    match = re.search(r"(?:circom compiler |snarkjs@)(\d+\.\d+\.\d+)(?![\d.])", output)
    if match is None or match.group(1) != expected:
        raise RuntimeError(f"unsupported tool version for {tool}; expected {expected}")
    allowed_exits = (0, 99) if 'snarkjs@' in output else (0,)
    if result.returncode not in allowed_exits:
        raise RuntimeError(f'version command failed: {result.returncode}')
    # snarkjs prints its version but exits 99 when invoked without a command.
    return {"command": command, "exit": result.returncode, "elapsed": time.monotonic() - started, "stdout": result.stdout, "stderr": result.stderr}


def _default_tool(name):
    return Path(__file__).resolve().parents[2] / ".tools" / name


def compile_circuit(source, output_dir, *, circom=None):
    """Compile Circom source, requiring the pinned compiler and artifacts."""
    source = Path(source)
    output_dir = Path(output_dir)
    compiler = Path(circom) if circom is not None else _default_tool("circom")
    if not compiler.is_file() or not os.access(compiler, os.X_OK):
        raise RuntimeError(f"Circom compiler unavailable: {compiler}")
    _version(compiler, _CIRCOM_VERSION)
    if not source.is_file():
        raise ValueError(f"source file not found: {source}")
    output_dir.mkdir(parents=True, exist_ok=True)
    command = [str(compiler), str(source), "--r1cs", "--wasm", "--sym", "--O0", "--sanity_check", "0", "--prime", "bn128", "-o", str(output_dir)]
    record = _run(command, timeout=600)
    stem = source.stem
    artifacts = {"r1cs": output_dir / f"{stem}.r1cs", "wasm": output_dir / f"{stem}_js" / f"{stem}.wasm", "sym": output_dir / f"{stem}.sym"}
    missing = [str(path) for path in artifacts.values() if not path.is_file()]
    if missing:
        raise RuntimeError("Circom completed without expected artifacts: " + ", ".join(missing))
    artifacts["command"] = record
    return artifacts


def run_witness(compiled, witness, output_dir):
    """Generate and independently export a witness using pinned snarkjs."""
    if not isinstance(compiled, dict):
        raise ValueError("compiled artifacts must be a mapping")
    required = ("wasm", "r1cs")
    if any(key not in compiled for key in required):
        raise ValueError("compiled artifacts require wasm and r1cs paths")
    wasm = Path(compiled["wasm"])
    r1cs = Path(compiled["r1cs"])
    if not wasm.is_file() or not r1cs.is_file():
        raise RuntimeError("compiled artifacts are missing")
    witness = dict(witness) if isinstance(witness, dict) else None
    if witness is None or any(type(value) is not int or not 0 <= value < FIELD_PRIME for value in witness.values()):
        raise ValueError("witness values must be canonical field integers")
    snarkjs = _default_tool("node_modules/.bin/snarkjs")
    if not snarkjs.is_file():
        raise RuntimeError(f"snarkjs unavailable: {snarkjs}")
    version_record = _version(snarkjs, _SNARKJS_VERSION)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    stem = wasm.stem
    input_path = output_dir / "input.json"
    input_path.write_text(json.dumps({key: str(value) for key, value in sorted(witness.items())}, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")
    wtns = output_dir / f"{stem}.wtns"
    json_path = output_dir / f"{stem}.json"
    r1cs_json = output_dir / f"{r1cs.stem}.r1cs.json"
    generator = wasm.parent / "generate_witness.js"
    if not generator.is_file():
        raise RuntimeError(f"witness generator unavailable: {generator}")
    records = [version_record]
    records.append(_run(["node", str(generator), str(wasm), str(input_path), str(wtns)], timeout=600))
    records.append(_run([str(snarkjs), "wtns", "check", str(r1cs), str(wtns)], timeout=600))
    records.append(_run([str(snarkjs), "wtns", "export", "json", str(wtns), str(json_path)], timeout=600))
    records.append(_run([str(snarkjs), "r1cs", "export", "json", str(r1cs), str(r1cs_json)], timeout=600))
    artifacts = {"input": input_path, "wtns": wtns, "json": json_path, "r1cs_json": r1cs_json, "commands": records}
    missing = [str(path) for key, path in artifacts.items() if key != "commands" and not path.is_file()]
    if missing:
        raise RuntimeError("snarkjs completed without expected artifacts: " + ", ".join(missing))
    return artifacts
