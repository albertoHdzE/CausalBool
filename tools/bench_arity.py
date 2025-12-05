import json
import os
import time

def xor_output(vec):
    return sum(vec) % 2

def enumerate_vectors(n):
    total = 1 << n
    out = 0
    for x in range(total):
        vec = [(x >> i) & 1 for i in range(n)]  # LSB-first
        out ^= xor_output(vec)
    return out

def measure(n, runs=5):
    ms = []
    for _ in range(runs):
        t0 = time.perf_counter()
        enumerate_vectors(n)
        t1 = time.perf_counter()
        ms.append((t1 - t0) * 1000.0)
    avg = sum(ms) / len(ms)
    var = sum((x - avg) ** 2 for x in ms) / len(ms)
    std = var ** 0.5
    return {"arity": n, "runs_ms": ms, "avg_ms": avg, "std_ms": std}

def format_ms(v):
    return f"{v:.3f}"

def make_table(data):
    lines = []
    lines.append("\\begin{center}")
    lines.append("\\begin{tabular}{lrrrrr rr}")
    lines.append("\\toprule")
    lines.append("Arity & Run 1 & Run 2 & Run 3 & Run 4 & Run 5 & Avg & Std " + "\\\\")
    lines.append("\\midrule")
    for row in data:
        label = f"{row['arity']}-ary"
        runs = [format_ms(x) for x in row["runs_ms"]]
        avg = format_ms(row["avg_ms"])
        std = format_ms(row["std_ms"])
        lines.append(f"{label} & {runs[0]} & {runs[1]} & {runs[2]} & {runs[3]} & {runs[4]} & {avg} & {std} " + "\\\\")
    lines.append("\\bottomrule")
    lines.append("\\end{tabular}")
    lines.append("\\end{center}")
    return "\n".join(lines) + "\n"

def main():
    out_dir = os.path.join("results", "tests", "tt001")
    os.makedirs(out_dir, exist_ok=True)
    results = [measure(n) for n in range(1, 7)]
    with open(os.path.join(out_dir, "ArityTiming.json"), "w") as f:
        json.dump(results, f, indent=2)
    table_tex = make_table(results)
    with open(os.path.join(out_dir, "ArityTiming.tex"), "w") as f:
        f.write(table_tex)

if __name__ == "__main__":
    main()
