"""Builder for notebook 02 -- biological networks, regulatory gates, reprogramming."""
import os
from _nblib import md, code, write_notebook, BOOTSTRAP

HERE = os.path.dirname(os.path.abspath(__file__))

cells = [
md(r"""
# 02 · Biological Networks, Regulatory Gates, and Reprogramming

The same exact inverse now meets **real biology**. Genes switch each other on and
off; a *gene-regulatory network* is a Boolean network whose nodes are genes. We
take a published model of the **fission-yeast cell cycle**, recover it from its
behaviour, meet the special **regulatory gate** that biology needs, and then ask
the question a biologist cares about: *which genes, if knocked out, reprogramme the
cell?*
"""),
code(BOOTSTRAP),

md(r"""
## 1. A real gene network

We load a standard model (Davidich & Bornholdt's yeast cell cycle). Its nodes are
real genes and proteins — Cdc25, Cdc2/Cdc13, Wee1, and so on.
"""),
code(r"""
from bnet import parse_bnet
from causalbool import repertoire

net, names = parse_bnet(os.path.join(BIO, "pyboolnet_davidich_yeast.bnet"))
print(f"{net.n} genes:", ", ".join(names))
rep = repertoire(net)                 # 2**10 = 1024 states x 10 genes: the full behaviour
print("behaviour table:", len(rep), "states x", len(rep[0]), "genes")
"""),

md(r"""
## 2. Recover the network, and meet the regulatory gate

Deconvolving the behaviour recovers each gene's regulators and its logic. Biology
rarely uses tidy AND/OR gates; its workhorse is **activators AND NOT inhibitors** —
a gene turns on when its activators are present *and* its repressors are absent.
Our method names this the **REGULATORY** gate, and unions of such clauses the
**REGULATORY_DNF** gate.
"""),
code(r"""
from deconvolution import deconvolve, verify_forward
from collections import Counter

net2, reports = deconvolve(rep)
gate_counts = Counter(r.canonical.gate for r in reports)

print("recovered logic, gene by gene:")
for r, nm in zip(reports, names):
    regs = [names[i] for i in r.connected_inputs]
    print(f"  {nm:14s} <- {r.canonical.gate:14s} of {regs}")
print("\nexact behavioural match:", repertoire(net2) == rep, "| independent rebuild:", verify_forward(rep, net2))
"""),
code(r"""
fig, ax = plt.subplots(figsize=(7, 3))
labels, vals = zip(*gate_counts.most_common())
ax.bar(labels, vals, color=[HL if "REGULATORY" in l else INK for l in labels])
ax.set_ylabel("number of genes"); ax.set_title("Recovered gate types (biology favours the regulatory gate)")
plt.xticks(rotation=20, ha="right"); plt.tight_layout(); plt.show()
"""),

md(r"""
### What a regulatory gate looks like

For a gene named **REGULATORY**, the recovered rule marks each regulator as an
*activator* or an *inhibitor*. The gene fires only when every activator is ON and
every inhibitor is OFF.
"""),
code(r"""
for r, nm in zip(reports, names):
    if r.canonical.gate == "REGULATORY":
        acts = [names[r.connected_inputs[j]] for j in r.canonical.params["activators"]]
        inhs = [names[r.connected_inputs[j]] for j in range(len(r.connected_inputs))
                if j not in r.canonical.params["activators"]]
        print(f"{nm}  fires when  activators {acts} are ON  AND  inhibitors {inhs} are OFF")
"""),

md(r"""
## 3. Behavioural equivalence, in a picture

The recovered network reproduces all 1024 states. We show the two behaviour tables
and their difference (a thin slice, so it fits on screen).
"""),
code(r"""
rep_a = np.array(rep); rep_b = np.array(repertoire(net2))
sl = slice(0, 120)                          # first 120 of 1024 states, to see the pixels
fig, axes = plt.subplots(1, 3, figsize=(10, 4.6))
for ax, M, t in zip(axes, [rep_a[sl], rep_b[sl], np.abs(rep_a[sl]-rep_b[sl])],
                    ["original behaviour", "recovered behaviour", "difference"]):
    ax.imshow(M, cmap="Greys", vmin=0, vmax=1, aspect="auto")
    ax.set_title(t); ax.set_xlabel("gene"); ax.set_yticks([])
axes[2].set_title(f"difference (max over ALL 1024 = {int(np.abs(rep_a-rep_b).max())})", color=OK)
plt.tight_layout(); plt.show()
"""),

md(r"""
## 4. Reprogramming: which genes are the drivers?

Because we hold the *exact* dynamics, we can ask a causal question directly. Fix a
gene OFF (a **knockout**) and re-measure two things:

* the **image size** — how many distinct next-states the system can reach (its
  dynamical richness);
* the **number of attractors** — the stable fates (cell-cycle phases) it can settle
  into.

Genes whose knockout changes these the most are the **drivers** — the levers of the
cell. This reproduces the logic of cellular-reprogramming studies, exactly.
"""),
code(r"""
from reprogramming import spectrum, image_size, num_attractors

base_img, base_att = image_size(net), num_attractors(net)
info_img = spectrum(net, measure=image_size)          # drop in image size per knockout
info_att = spectrum(net, measure=num_attractors)      # drop in #attractors per knockout
order = np.argsort(info_img)[::-1]

fig, ax = plt.subplots(figsize=(9, 3.4))
xs = np.arange(net.n)
ax.bar(xs, [info_img[i] for i in order], color=HL)
ax.set_xticks(xs); ax.set_xticklabels([names[i] for i in order], rotation=40, ha="right")
ax.set_ylabel("loss of image size\n(dynamical richness)")
ax.set_title(f"Reprogrammability spectrum  (base image {base_img}, {base_att} attractors)")
plt.tight_layout(); plt.show()
drivers = [names[i] for i in order if info_img[i] > 0][:3]
print("top drivers by dynamical impact:", drivers)
"""),

md(r"""
## Takeaways

* Real gene networks are recovered **exactly** from their behaviour, gene by gene.
* Biology's natural logic is the **regulatory gate** (activators AND NOT
  inhibitors); we name it, and compress unions of such clauses as REGULATORY_DNF.
* Holding the exact dynamics lets us **reprogramme** *in silico*: knock a gene out,
  watch the attractor landscape move, and read off the driver genes.

**Next (03):** we point the very same machine at **financial markets** — and get an
honest, informative *failure* that reshapes the whole question.
"""),
]

write_notebook(cells, os.path.join(HERE, "02_biological_networks.ipynb"))
