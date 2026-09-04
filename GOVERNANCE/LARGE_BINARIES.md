# LARGE_BINARIES — what may enter git history, and why the rule is worth keeping

**Status:** ACTIVE · Established by **AUDIT03 / decision E** (2026-09-04).

## The rule

Do not commit a file larger than **10 MB** unless it is an input that cannot be
regenerated and cannot be fetched. In practice this means:

| kind | rule |
|---|---|
| external datasets (DepMap, omics, price feeds) | **never committed.** `.gitignore` them and commit a manifest plus a fetch script |
| generated results, figures, PDFs of our own making | committed only if small and cited by a paper; otherwise regenerate |
| vendored third-party source | committed, because a dependency boundary must be pinned |
| notebooks | strip outputs before committing if they embed large images |

`data/DepMap/*` is already ignored, with `README.txt` and
`manifest_24Q4.json` as the deliberate exceptions.

## Why this is a rule and not a preference

Measured 2026-09-04:

```
.git       11 GB          (8.8 GB when first measured, 2026-09-03)
data/      85 MB tracked
results/   3.0 MB tracked
```

The working tree is **88 MB**. The repository is **11 GB**. The difference is
entirely DepMap CSVs that were committed before they were ignored, and they are
still in history:

```
3974 MB  data/DepMap/OmicsExpressionTranscriptsTPMLogp1Profile.csv
3243 MB  data/DepMap/AvanaLogfoldChange.csv
1782 MB  data/DepMap/OmicsExpressionTranscriptsExpectedCountProfile.csv
1517 MB  data/DepMap/KYLogfoldChange.csv
1483 MB  data/DepMap/OmicsExpressionTranscriptsTPMLogp1StrandedProfile.csv
...  top eight blobs alone ~15.6 GB raw
```

## Why it has not been repaired, and why that is the right call

**AUDIT03/R7 originally proposed moving `data/` and `results/` out of the
repository. That premise was false and the task was dropped.** Deleting or
relocating them today reclaims **nothing**: they are already untracked, and the
size is in history, not in the working tree.

Only a history rewrite (`git filter-repo` or equivalent) reclaims the 11 GB, and
it **rewrites every commit SHA in the project**. Those SHAs are load-bearing:
`audit/METHOD_ACCOUNT.md`, `tests/MUnit/BASELINE.md`, `audit/AUDIT03_PLAN.md`
and a long series of commit messages cite specific commits as evidence for
specific claims. A rewrite would invalidate every one of those citations at
once, in a programme whose whole discipline is that a claim names the evidence
that settles it.

**The provenance chain is worth more than the disk.** 11 GB is cheap; an audit
trail that no longer resolves is not.

This is therefore a **forward-looking** rule: it prevents the next 11 GB, and it
accepts the existing one as a sunk cost that is cheaper to carry than to fix.

## If a rewrite ever becomes necessary

It is a one-way door and needs, in this order:

1. an author decision recorded with a date;
2. a mapping table `old SHA -> new SHA` committed **before** the rewrite, so
   existing citations remain resolvable;
3. every citing document updated in the same operation;
4. a mirror of the pre-rewrite repository retained.

Without step 2 the rewrite destroys the evidence base, which is a worse outcome
than the disk usage it fixes.
