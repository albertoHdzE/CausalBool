"""Builder for notebook 00 -- the forward method and deconvolution."""
import os
from _nblib import md, code, write_notebook, BOOTSTRAP

HERE = os.path.dirname(os.path.abspath(__file__))

cells = [
md(r"""
# 00 · The Forward Method and Deconvolution

**A gentle, visual tour of the whole programme — from the ground up.**

This is the first of a series of notebooks that teach, step by step, everything we
discovered. No prior knowledge is assumed. We build the ideas with pictures.

The story in one line: we invented an *exact inverse* for a certain kind of system.
Given only the *behaviour* of a network, we recover the network itself — who is
wired to whom, and what rule each node follows — with no error. Later notebooks
apply this to cellular automata, to biology, and finally to financial markets,
where the exact method fails honestly and points us to a deeper, statistical kind
of order.

> **How to run.** Pick the kernel called **CausalBool** (top-right). Then run the
> cells in order. The first cell makes the notebook work from any folder.
"""),
code(BOOTSTRAP),

md(r"""
## 1. What is a Boolean network?

Imagine a row of light switches. Each switch is a **node**. At every tick of a
clock, each switch looks at a few of the *other* switches and decides whether to be
ON (1) or OFF (0), following a fixed rule called a **gate** (AND, OR, XOR, …).

A network is therefore three things:

* **who listens to whom** — the wiring (a matrix `C`, where `C[k][i] = 1` means node
  *i* feeds node *k*);
* **the rule at each node** — its gate;
* nothing else. The future is a deterministic function of the present.

Let us build a tiny 3-node network by hand.
"""),
code(r"""
from causalbool import Network, repertoire, node_output_column

# C[k][i] = 1  means node i is an input of node k
net = Network(
    n=3,
    C=[[0, 1, 1],    # node 0 listens to nodes 1 and 2
       [1, 0, 1],    # node 1 listens to nodes 0 and 2
       [1, 1, 0]],   # node 2 listens to nodes 0 and 1
    gates=["AND", "OR", "XOR"],
)
for k in range(net.n):
    print(f"node {k}: gate {net.gates[k]:4s}  inputs {net.connected_inputs(k)}")
"""),

md(r"""
## 2. The forward method: the *repertoire*

If we feed the network **every possible input state** (for 3 nodes there are
$2^3 = 8$ of them) and write down what each node outputs, we get a table called the
**repertoire**: 8 rows (one per input state), 3 columns (one per node). This table
is the network's complete *behaviour* — everything it can ever do.
"""),
code(r"""
rep = repertoire(net)          # 2**n rows x n columns
rep = np.array(rep)

fig, ax = plt.subplots(figsize=(4.6, 5))
ax.imshow(rep, cmap="Greys", vmin=0, vmax=1, aspect="auto")
ax.set_xticks(range(net.n)); ax.set_xticklabels([f"node {k}\n{net.gates[k]}" for k in range(net.n)])
ax.set_yticks(range(2**net.n)); ax.set_yticklabels([f"state {r}" for r in range(2**net.n)])
ax.set_title("The repertoire\n(black = 1, white = 0)")
for (i, j), v in np.ndenumerate(rep):
    ax.text(j, i, v, ha="center", va="center", color=HL if v else "#bbb", fontweight="bold")
plt.tight_layout(); plt.show()
print("Each column is one node's complete behaviour. That is all the deconvolution sees.")
"""),

md(r"""
## 3. The inverse problem

Now play the game the other way round. **Hide the network. Show only the
repertoire.** Can we recover the wiring and the gates from the behaviour alone?

Yes — exactly. The trick is that the behaviour *factorises*: column *k* of the
repertoire depends only on the inputs of node *k*. So we solve one column at a
time.
"""),

md(r"""
### Step 1 — which inputs actually matter (perturbation)

To find the inputs of a node we use a simple, exact test. Take its output column.
**Flip one input bit** (with everything else fixed) and see whether the output ever
changes. If it does, that input is *essential* (a real wire). If flipping it never
changes anything, it is not connected. This is a causal test, not a statistical
one.
"""),
code(r"""
from causalbool import input_vector
from deconvolution import essential_variables

k = 0                                  # inspect node 0 (an AND of nodes 1 and 2)
col = node_output_column(net, k)
ess = essential_variables(col, net.n)
print(f"node {k}: recovered essential inputs = {ess}   (true inputs = {net.connected_inputs(k)})")

# show one witness: a pair of input states differing only in bit `ess[0]`
i = ess[0]
for x in range(2**net.n):
    if not (x >> i) & 1:
        x2 = x | (1 << i)
        if col[x] != col[x2]:
            print(f"  flipping input {i}: state {input_vector(x,net.n)} -> out {col[x]}, "
                  f"state {input_vector(x2,net.n)} -> out {col[x2]}   (the output moved: input {i} is real)")
            break
"""),

md(r"""
### Step 2 — name the gate, and Step 3 — verify

Once we know a node's real inputs, we reduce its column to just those inputs and
match the small truth table against the family of known gates (AND, OR, XOR, …).
Doing this for every node reconstructs the whole network. Then we **verify** by
running the recovered network forward and checking its repertoire equals the
original — cell for cell.
"""),
code(r"""
from deconvolution import deconvolve, verify, verify_forward

net2, reports = deconvolve(rep.tolist())          # recover network from behaviour ALONE
print("recovered network:")
for r in reports:
    print(f"  node {r.node}: inputs {r.connected_inputs}  gate {r.canonical.gate}")

check = verify(rep.tolist(), reports)
fwd   = verify_forward(rep.tolist(), net2)
print("\nrepertoire reproduced exactly :", check.get("exact", check))
print("independent forward rebuild ok :", fwd)
"""),
code(r"""
# The picture of equivalence: original vs recovered repertoire, and their difference
rep2 = np.array(repertoire(net2))
diff = np.abs(rep - rep2)

fig, axes = plt.subplots(1, 3, figsize=(10, 4.5))
for ax, M, title in zip(axes, [rep, rep2, diff],
                        ["original behaviour", "recovered behaviour", "difference"]):
    ax.imshow(M, cmap="Greys", vmin=0, vmax=1, aspect="auto")
    ax.set_title(title); ax.set_xlabel("node"); ax.set_yticks([])
axes[2].set_title(f"difference (max = {diff.max()})", color=OK)
plt.tight_layout(); plt.show()
print("The difference is all zero: the recovered network is behaviourally identical to the original.")
"""),

md(r"""
## 4. It is exact at scale, and it does **not** fit noise

Two facts make this trustworthy. First, the recovery is exact for *any* such
network, not just our toy — we test many random ones. Second, the method does not
"explain" randomness: a random column needs a long, incompressible description,
whereas a structured one collapses to a short rule. Order is recovered only where
it exists.
"""),
code(r"""
from network_generator import random_network

n, trials = 8, 60
exact = 0
for seed in range(trials):
    g = random_network(n, seed=seed)
    rg = repertoire(g)
    gr, reps = deconvolve(rg)
    exact += (repertoire(gr) == rg)

fig, ax = plt.subplots(figsize=(6, 1.6))
ax.barh([0], [exact], color=OK); ax.barh([0], [trials-exact], left=[exact], color=BAD)
ax.set_xlim(0, trials); ax.set_yticks([]); ax.set_xlabel("random 8-node networks")
ax.set_title(f"exact repertoire recovery: {exact}/{trials}")
plt.tight_layout(); plt.show()
print(f"{exact}/{trials} random networks recovered exactly from their behaviour alone.")
"""),

md(r"""
## Takeaways

* A Boolean network's **behaviour** (its repertoire) is a table we can read.
* From that table alone we recover the **wiring** (by a causal flip-a-bit test) and
  the **gate** at each node — exactly, and verifiably.
* The method recovers order where it exists and refuses to compress randomness.

**Next (01):** we let the network be a *cellular automaton* — a whole space-time
picture — and recover its rule from the pattern it paints.
"""),
]

write_notebook(cells, os.path.join(HERE, "00_forward_method_and_deconvolution.ipynb"))
