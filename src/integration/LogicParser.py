import re
from typing import List, Dict, Any

import numpy as np


class LogicParser:
    """
    Parse Boolean rules into truth tables and classify them into gate types.
    """

    def truth_table(self, rule: str, inputs: List[str]) -> np.ndarray:
        """
        Generate a truth table for a Boolean rule over a fixed input ordering.

        Args:
            rule: Boolean expression (e.g., "A AND NOT B").
            inputs: Ordered list of input variable names.

        Returns:
            Array of shape (2^k, k+1) with input bits and output bit.
        """
        k = len(inputs)
        rows = 2**k
        table = np.zeros((rows, k + 1), dtype=int)

        for idx in range(rows):
            bits = [int(b) for b in format(idx, f"0{k}b")]
            table[idx, :k] = bits
            env = {name: bool(value) for name, value in zip(inputs, bits)}
            out = self._evaluate(rule, env)
            table[idx, k] = int(bool(out))

        return table

    def classify_truth_table(self, table: np.ndarray) -> Dict[str, Any]:
        """
        Classify a truth table into a gate type and parameters.

        Args:
            table: Array of shape (2^k, k+1).

        Returns:
            Mapping with keys:
                - gate: gate label (e.g., "AND", "CANALISING", "CUSTOM").
                - parameters: gate-specific parameters (possibly empty).
        """
        arr = np.asarray(table, dtype=int)
        if arr.ndim != 2 or arr.shape[1] < 2:
            raise ValueError("Truth table must have shape (2^k, k+1).")

        inputs = arr[:, :-1]
        outputs = arr[:, -1]
        k = inputs.shape[1]

        if k == 1:
            vals = outputs.tolist()
            if vals == [1, 0]:
                return {"gate": "NOT", "parameters": {}}
            if vals == [0, 1]:
                return {"gate": "IDENTITY", "parameters": {}}
            if vals == [0, 0]:
                return {"gate": "CONST0", "parameters": {}}
            if vals == [1, 1]:
                return {"gate": "CONST1", "parameters": {}}
            return {"gate": "CUSTOM", "parameters": {}}

        for name in ("AND", "OR", "XOR", "NAND", "NOR", "XNOR"):
            expected = self._standard_gate_outputs(name, inputs)
            if np.array_equal(outputs, expected):
                return {"gate": name, "parameters": {}}

        k_int = int(k)
        for i in range(k_int):
            for v in (0, 1):
                mask = inputs[:, i] == v
                if not np.any(mask):
                    continue
                subset = outputs[mask]
                if subset.size > 0 and np.all(subset == subset[0]):
                    return {
                        "gate": "CANALISING",
                        "parameters": {
                            "canalisingIndex": i + 1,
                            "canalisingValue": int(v),
                            "canalisedOutput": int(subset[0]),
                        },
                    }

        return {"gate": "CUSTOM", "parameters": {}}

    def parse_and_classify(self, rule: str, inputs: List[str]) -> Dict[str, Any]:
        """
        Convenience wrapper: build truth table and classify gate.

        Args:
            rule: Boolean expression.
            inputs: Ordered list of input variable names.

        Returns:
            Dictionary with:
                - inputs
                - truth_table
                - gate
                - parameters
        """
        table = self.truth_table(rule, inputs)
        info = self.classify_truth_table(table)
        return {
            "inputs": list(inputs),
            "truth_table": table,
            "gate": info["gate"],
            "parameters": info["parameters"],
        }

    def _evaluate(self, rule: str, env: Dict[str, bool]) -> bool:
        if self._uses_functional_syntax(rule):
            return self._eval_functional(rule, env)
        return self._eval_infix(rule, env)

    @staticmethod
    def _uses_functional_syntax(rule: str) -> bool:
        tokens = (
            "AND(",
            "OR(",
            "XOR(",
            "NAND(",
            "NOR(",
            "XNOR(",
            "IMPLIES(",
            "NIMPLIES(",
            "KOFN(",
            "CANALISING(",
        )
        return any(t in rule for t in tokens)

    def _eval_infix(self, rule: str, env: Dict[str, bool]) -> bool:
        expr = rule
        expr = re.sub(r"\bAND\b", " and ", expr)
        expr = re.sub(r"\bOR\b", " or ", expr)
        expr = re.sub(r"\bNOT\b", " not ", expr)
        expr = re.sub(r"\bXOR\b", " ^ ", expr)
        try:
            return bool(eval(expr, {"__builtins__": {}}, env))
        except Exception as exc:
            raise ValueError(f"Failed to evaluate rule '{rule}' in infix mode.") from exc

    def _eval_functional(self, rule: str, env: Dict[str, bool]) -> bool:
        def AND(*args: bool) -> bool:
            return all(bool(a) for a in args)

        def OR(*args: bool) -> bool:
            return any(bool(a) for a in args)

        def NOT(x: bool) -> bool:
            return not bool(x)

        def XOR(*args: bool) -> bool:
            return bool(sum(bool(a) for a in args) % 2)

        def NAND(*args: bool) -> bool:
            return not AND(*args)

        def NOR(*args: bool) -> bool:
            return not OR(*args)

        def XNOR(*args: bool) -> bool:
            return not XOR(*args)

        def IMPLIES(a: bool, b: bool) -> bool:
            return (not bool(a)) or bool(b)

        def NIMPLIES(a: bool, b: bool) -> bool:
            return bool(a) and (not bool(b))

        def KOFN(*args: bool, k: int = 1) -> bool:
            return sum(bool(a) for a in args) >= k

        safe_env: Dict[str, Any] = {}
        safe_env.update(env)
        safe_env.update(
            {
                "AND": AND,
                "OR": OR,
                "NOT": NOT,
                "XOR": XOR,
                "NAND": NAND,
                "NOR": NOR,
                "XNOR": XNOR,
                "IMPLIES": IMPLIES,
                "NIMPLIES": NIMPLIES,
                "KOFN": KOFN,
            }
        )
        try:
            return bool(eval(rule, {"__builtins__": {}}, safe_env))
        except Exception as exc:
            raise ValueError(f"Failed to evaluate rule '{rule}' in functional mode.") from exc

    @staticmethod
    def _standard_gate_outputs(name: str, inputs: np.ndarray) -> np.ndarray:
        x = inputs.astype(int)
        if name == "AND":
            return np.all(x == 1, axis=1).astype(int)
        if name == "OR":
            return np.any(x == 1, axis=1).astype(int)
        if name == "XOR":
            return (np.sum(x == 1, axis=1) % 2).astype(int)
        if name == "NAND":
            return 1 - LogicParser._standard_gate_outputs("AND", x)
        if name == "NOR":
            return 1 - LogicParser._standard_gate_outputs("OR", x)
        if name == "XNOR":
            return 1 - LogicParser._standard_gate_outputs("XOR", x)
        raise ValueError(f"Unsupported standard gate '{name}'.")


__all__ = ["LogicParser"]
