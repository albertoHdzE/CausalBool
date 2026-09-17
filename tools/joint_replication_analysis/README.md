# Final replication analysis

This namespace is downstream of the frozen final replication. It performs a
fresh network replay and catalogue audit before deriving descriptive results.
The previous experiment, its failed first analysis release, and the recovered
replication records remain unchanged.

```sh
PYTHONPATH=doppel-challenge/src python tools/joint_replication_analysis/analyze.py --action audit
PYTHONPATH=doppel-challenge/src python tools/joint_replication_analysis/analyze.py --action analyze
PYTHONPATH=doppel-challenge/src python tools/joint_replication_analysis/analyze.py --action verify
```

The audit checks every ordered output row, exact dynamics, BDM, historical
Wolfram digest, all 2,400 catalogues and every declared frontier. Effects are
weighted by base draw within each family/N/kind stratum. The new study is
compared with the previous release by stratum and is not pooled with it.
