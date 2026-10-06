"""The naive matcher — the identity element of the operator group, over the whole corpus.

Phase 1 asks one question of every target: *is there an OEIS entry that contains a long
run of this sequence verbatim?* No transforms, no fuzz, no tolerance. Exact contiguous
windows only. Phase 2 replaces this with a transform closure and must beat it in bits.

The corpus is flattened once into three parallel arrays (term value, owning sequence,
position within that sequence) and a sorted table of k-gram hashes over it. A query
hashes each k-gram of the target, binary-searches the seed table, verifies candidates
exactly (hashes may collide; the verification means the result never can), and extends
each surviving candidate maximally in both directions.

Two properties matter for honesty:

* **Verification is exact.** A reported window is a genuine element-for-element
  equality, checked, not a similarity above a threshold.
* **The candidate cap is one-sided.** A seed matching more than
  ``MAX_CANDIDATES_PER_SEED`` positions is truncated deterministically, which can only
  cause the matcher to *miss* a long window, never to invent one. Every result records
  how often the cap bound.
* **Overflow discontinuities cannot be bridged — on either side.** A term that does not
  fit int64 is dropped individually and marks a break: seed formation requires all k
  terms valid, and window extension requires validity at every step, in the corpus and
  in the query alike (`bitacora/01` §5's bignum policy, enforced rather than promised).
  Found by the Phase 2 runtime smoke: transform products overflow int64, and the
  pre-fix extension code could have bridged a corpus-side break where the target held a
  zero.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path

import duckdb
import numpy as np

#: Seed length. A window must save more bits than the ~34 it costs to name an entry and
#: address the window; at 5-9 bits per gap term that needs roughly 6 terms, so shorter
#: seeds only generate candidates that cannot win under G1.
SEED_K = 6

#: Deterministic truncation for pathologically common seeds (e.g. 1,1,1,1,1,1).
#: One-sided: it can only shorten a reported match.
MAX_CANDIDATES_PER_SEED = 20_000

#: A low-alphabet target repeats the same k-gram many times — an all-1s sequence of
#: length 100 has 95 seeds but only **one** distinct value, so the identical
#: 20,000-candidate query was being run 95 times, and the cost grew quadratically in
#: target length. Distinct seed values are queried at most this many times, at
#: deterministically spread positions.
#:
#: Like the candidate cap this is **one-sided** — it can only shorten a reported match,
#: never lengthen one — and it is applied identically to observed and surrogate targets,
#: so it cannot bias the excess-over-null statistic, which is what is reported.
MAX_POSITIONS_PER_DISTINCT_SEED = 4

_I64_MIN, _I64_MAX = -(2**63), 2**63 - 1
_MASK = np.uint64(0xFFFFFFFFFFFFFFFF)
_MULT = np.uint64(0x9E3779B97F4A7C15)


def _hash_kgrams(terms: np.ndarray, valid: np.ndarray, k: int) -> np.ndarray:
    """Rolling polynomial hash of every length-``k`` window, ``0`` where invalid."""
    m = len(terms)
    h = np.zeros(m, dtype=np.uint64)
    ok = np.ones(m, dtype=bool)
    for j in range(k):
        sl = slice(j, m - k + 1 + j)
        h[: m - k + 1] = (h[: m - k + 1] * _MULT) ^ terms[sl].astype(np.uint64)
        ok[: m - k + 1] &= valid[sl]
    h[m - k + 1 :] = 0
    ok[m - k + 1 :] = False
    return np.where(ok, h | np.uint64(1), np.uint64(0))


def _to_int64(target: list[int]) -> tuple[np.ndarray, np.ndarray]:
    """Target terms as int64 plus a validity mask; overflow positions become invalid.

    Mirrors the corpus-side bignum policy (`bitacora/01` §5): an overflowing term is
    dropped *individually* and marks a position discontinuity a window cannot bridge.
    """
    n = len(target)
    vals = np.zeros(n, dtype=np.int64)
    valid = np.zeros(n, dtype=bool)
    for i, v in enumerate(target):
        try:
            iv = int(v)
        except (TypeError, ValueError):
            continue
        if _I64_MIN <= iv <= _I64_MAX:
            vals[i] = iv
            valid[i] = True
    return vals, valid


@dataclass
class Match:
    """One exact contiguous window shared by the target and an OEIS entry."""

    seq_id: int
    a_number: str
    target_offset: int
    entry_offset: int
    match_len: int


class CorpusIndex:
    """Flattened corpus plus a k-gram seed table, built once and cached to disk."""

    def __init__(
        self,
        terms: np.ndarray,
        seq_of: np.ndarray,
        pos_in_seq: np.ndarray,
        seq_ids: np.ndarray,
        seed_hash: np.ndarray,
        seed_pos: np.ndarray,
        n_sequences: int,
        valid: np.ndarray | None = None,
    ) -> None:
        self.terms = terms
        self.seq_of = seq_of
        self.pos_in_seq = pos_in_seq
        self.seq_ids = seq_ids
        self.valid = (
            valid if valid is not None else np.ones(len(terms), dtype=bool)
        )
        self.seed_hash = seed_hash
        self.seed_pos = seed_pos
        self.n_sequences = int(n_sequences)
        self.cap_hits = 0
        self.seeds_probed = 0
        self.seeds_total = 0

    # -- construction -------------------------------------------------------

    @staticmethod
    def build(db_path: Path, quiet: bool = False) -> CorpusIndex:
        """Flatten every int64-representable term in the corpus and hash its k-grams.

        Terms that overflow int64 (16.4% of entries carry at least one) are dropped
        *individually* and mark a position discontinuity, so a window can never silently
        bridge across one. Dropping whole sequences instead would be an unstated
        selection effect on every null that follows.
        """
        t0 = time.time()
        con = duckdb.connect(str(db_path), read_only=True)
        n_sequences = con.execute("SELECT count(*) FROM sequences").fetchone()[0]
        rows = con.execute(
            "SELECT seq_id, terms_raw FROM sequences WHERE terms_raw IS NOT NULL "
            "ORDER BY seq_id"
        ).fetchall()
        con.close()

        vals: list[int] = []
        sq: list[int] = []
        ps: list[int] = []
        vd: list[bool] = []
        for seq_id, raw in rows:
            for p, tok in enumerate(raw.split(",")):
                try:
                    v = int(tok)
                except ValueError:
                    continue
                fits = _I64_MIN <= v <= _I64_MAX
                vals.append(v if fits else 0)
                sq.append(seq_id)
                ps.append(p)
                vd.append(fits)

        terms = np.asarray(vals, dtype=np.int64)
        seq_of = np.asarray(sq, dtype=np.int32)
        pos_in_seq = np.asarray(ps, dtype=np.int32)
        valid = np.asarray(vd, dtype=bool)
        # a k-gram is only real if it stays inside one sequence and is contiguous there
        same = np.zeros(len(terms), dtype=bool)
        same[:-1] = (seq_of[1:] == seq_of[:-1]) & (pos_in_seq[1:] == pos_in_seq[:-1] + 1)
        valid_start = valid.copy()
        h = _hash_kgrams(terms, valid, SEED_K)
        run = np.ones(len(terms), dtype=bool)
        for j in range(SEED_K - 1):
            run[: len(terms) - j - 1] &= same[j:][: len(terms) - j - 1]
        h = np.where(run & valid_start, h, np.uint64(0))

        keep = np.nonzero(h)[0]
        order = np.argsort(h[keep], kind="stable")
        seed_pos = keep[order].astype(np.int64)
        seed_hash = h[seed_pos]

        seq_ids = np.unique(seq_of)
        idx = CorpusIndex(terms, seq_of, pos_in_seq, seq_ids, seed_hash, seed_pos,
                          n_sequences, valid=valid)
        if not quiet:
            print(f"index: {len(terms):,} terms, {len(seed_pos):,} seeds, "
                  f"{time.time() - t0:.1f}s", flush=True)
        return idx

    def save(self, path: Path) -> None:
        np.savez(
            path,
            terms=self.terms,
            seq_of=self.seq_of,
            pos_in_seq=self.pos_in_seq,
            seq_ids=self.seq_ids,
            valid=self.valid,
            seed_hash=self.seed_hash,
            seed_pos=self.seed_pos,
            n_sequences=np.int64(self.n_sequences),
        )

    @staticmethod
    def load(path: Path) -> CorpusIndex:
        z = np.load(path)
        if "valid" not in z.files:
            raise ValueError("index cache predates the validity mask; rebuild it")
        return CorpusIndex(
            z["terms"], z["seq_of"], z["pos_in_seq"], z["seq_ids"],
            z["seed_hash"], z["seed_pos"], int(z["n_sequences"]), valid=z["valid"],
        )

    @staticmethod
    def open(db_path: Path, cache: Path, quiet: bool = False) -> CorpusIndex:
        if cache.exists():
            try:
                return CorpusIndex.load(cache)
            except ValueError:
                pass  # stale cache format: rebuild and re-save below
        idx = CorpusIndex.build(db_path, quiet=quiet)
        cache.parent.mkdir(parents=True, exist_ok=True)
        idx.save(cache)
        return idx

    # -- query --------------------------------------------------------------

    def _extend(
        self, cand: np.ndarray, tgt: np.ndarray, tgt_valid: np.ndarray, j: int
    ) -> tuple:
        """Grow every candidate window maximally left and right. Vectorized, compacting.

        A window can never bridge an overflow discontinuity on either side: extension
        requires the corpus position AND the target position to be valid at every step.
        """
        n = len(tgt)
        right = np.zeros(len(cand), dtype=np.int32)
        alive = np.arange(len(cand))
        step = SEED_K
        while len(alive) and j + step < n:
            p = cand[alive] + step
            ok = (
                (p < len(self.terms))
                & self.valid[np.minimum(p, len(self.terms) - 1)]
                & tgt_valid[j + step]
                & (self.seq_of[np.minimum(p, len(self.terms) - 1)] == self.seq_of[cand[alive]])
                & (self.pos_in_seq[np.minimum(p, len(self.terms) - 1)]
                   == self.pos_in_seq[cand[alive]] + step)
                & (self.terms[np.minimum(p, len(self.terms) - 1)] == tgt[j + step])
            )
            alive = alive[ok]
            right[alive] = step + 1 - SEED_K
            step += 1

        left = np.zeros(len(cand), dtype=np.int32)
        alive = np.arange(len(cand))
        step = 1
        while len(alive) and j - step >= 0:
            p = cand[alive] - step
            ok = (
                (p >= 0)
                & self.valid[np.maximum(p, 0)]
                & tgt_valid[j - step]
                & (self.seq_of[np.maximum(p, 0)] == self.seq_of[cand[alive]])
                & (self.pos_in_seq[np.maximum(p, 0)] == self.pos_in_seq[cand[alive]] - step)
                & (self.terms[np.maximum(p, 0)] == tgt[j - step])
            )
            alive = alive[ok]
            left[alive] = step
            step += 1
        return left, right

    def best_match(self, target: list[int]) -> Match | None:
        """The longest exact contiguous window the corpus shares with ``target``.

        Ties are broken by lowest A-number, then earliest target offset, so the result
        is deterministic and independent of array order.
        """
        windows = self.best_windows(target, 1)
        return windows[0] if windows else None

    def best_windows(self, target: list[int], k: int = 1) -> list[Match]:
        """The ``k`` best distinct windows, best first — Phase 3's expansion instrument.

        Ranking: match length descending, then lowest A-number, then earliest target
        offset — the same deterministic order as :meth:`best_match`, extended to a list.
        One maximal window per probed seed position; the same caps as ``best_match``
        apply, so this is exactly as one-sided as the single-window search. Added
        additively in Phase 3: ``best_match`` is untouched, so every Phase 1/2 number
        remains reproducible bit-for-bit.
        """
        n = len(target)
        if n < SEED_K or k < 1:
            return []
        tgt, tgt_valid = _to_int64(target)
        tgt_h = _hash_kgrams(tgt, tgt_valid, SEED_K)

        by_hash: dict[int, list[int]] = {}
        for j in range(n - SEED_K + 1):
            if tgt_h[j]:
                by_hash.setdefault(int(tgt_h[j]), []).append(j)
        probes: list[int] = []
        for pos in by_hash.values():
            if len(pos) <= MAX_POSITIONS_PER_DISTINCT_SEED:
                probes.extend(pos)
            else:
                step = len(pos) / MAX_POSITIONS_PER_DISTINCT_SEED
                probes.extend(pos[int(i * step)] for i in range(MAX_POSITIONS_PER_DISTINCT_SEED))
        self.seeds_probed += len(probes)
        self.seeds_total += sum(len(p) for p in by_hash.values())

        found: dict[tuple, Match] = {}
        for j in sorted(probes):
            h = tgt_h[j]

            lo = np.searchsorted(self.seed_hash, h, side="left")
            hi = np.searchsorted(self.seed_hash, h, side="right")
            if hi == lo:
                continue
            if hi - lo > MAX_CANDIDATES_PER_SEED:
                self.cap_hits += 1
                hi = lo + MAX_CANDIDATES_PER_SEED
            cand = self.seed_pos[lo:hi]

            okc = np.ones(len(cand), dtype=bool)
            for d in range(SEED_K):
                okc &= self.terms[cand + d] == tgt[j + d]
            cand = cand[okc]
            if not len(cand):
                continue

            left, right = self._extend(cand, tgt, tgt_valid, j)
            total = left + right + SEED_K
            order = np.argsort(-total, kind="stable")
            seen_lens: set[int] = set()
            for idx_c in order[: max(k, 4)]:
                mlen = int(total[idx_c])
                if mlen in seen_lens:
                    continue  # one window per candidate group per probe
                seen_lens.add(mlen)
                start = int(cand[idx_c] - left[idx_c])
                m = Match(
                    seq_id=int(self.seq_of[start]),
                    a_number=f"A{int(self.seq_of[start]):06d}",
                    target_offset=j - int(left[idx_c]),
                    entry_offset=int(self.pos_in_seq[start]),
                    match_len=mlen,
                )
                key = (m.a_number, m.target_offset, m.entry_offset, m.match_len)
                prev = found.get(key)
                if prev is None or m.match_len > prev.match_len:
                    found[key] = m

        ranked = sorted(
            found.values(),
            key=lambda m: (-m.match_len, m.a_number, m.target_offset),
        )
        return ranked[:k]

    def windows_for_entry(self, target: list[int], seq_id: int) -> Match | None:
        """The best window between ``target`` and ONE entry's head — Phase 3's
        neighbourhood rescoring instrument.

        Same probing, caps and verification as :meth:`best_match`, with candidates
        filtered to the given entry. Added additively in Phase 3.
        """
        n = len(target)
        if n < SEED_K:
            return None
        tgt, tgt_valid = _to_int64(target)
        tgt_h = _hash_kgrams(tgt, tgt_valid, SEED_K)

        by_hash: dict[int, list[int]] = {}
        for j in range(n - SEED_K + 1):
            if tgt_h[j]:
                by_hash.setdefault(int(tgt_h[j]), []).append(j)
        probes: list[int] = []
        for pos in by_hash.values():
            step = len(pos) / MAX_POSITIONS_PER_DISTINCT_SEED
            probes.extend(pos[int(i * step)]
                          for i in range(min(len(pos), MAX_POSITIONS_PER_DISTINCT_SEED)))
        best: Match | None = None
        for j in sorted(probes):
            h = tgt_h[j]
            lo = np.searchsorted(self.seed_hash, h, side="left")
            hi = np.searchsorted(self.seed_hash, h, side="right")
            if hi == lo:
                continue
            if hi - lo > MAX_CANDIDATES_PER_SEED:
                hi = lo + MAX_CANDIDATES_PER_SEED
            cand = self.seed_pos[lo:hi]
            cand = cand[self.seq_of[cand] == seq_id]
            if not len(cand):
                continue
            okc = np.ones(len(cand), dtype=bool)
            for d in range(SEED_K):
                okc &= self.terms[cand + d] == tgt[j + d]
            cand = cand[okc]
            if not len(cand):
                continue
            left, right = self._extend(cand, tgt, tgt_valid, j)
            total = left + right + SEED_K
            c = int(np.argmax(total))
            mlen = int(total[c])
            if best is not None and mlen <= best.match_len:
                continue
            start = int(cand[c] - left[c])
            best = Match(
                seq_id=seq_id,
                a_number=f"A{seq_id:06d}",
                target_offset=j - int(left[c]),
                entry_offset=int(self.pos_in_seq[start]),
                match_len=mlen,
            )
        return best

    @staticmethod
    def window_two_sequences(
        a: list[int], b: list[int], b_valid: np.ndarray | None = None
    ) -> tuple[int, int, int] | None:
        """Longest exact common contiguous window of two arbitrary sequences.

        Returns ``(offset_in_a, offset_in_b, length)`` or None below SEED_K. Same
        seed-and-verify machinery as the corpus search, over a local table — Phase 3's
        entry-side derived-relation instrument (added additively). ``b_valid`` may
        supply a precomputed validity mask (the index's own view of an entry head,
        where overflow terms are breaks).
        """
        if len(a) < SEED_K or len(b) < SEED_K:
            return None
        av, a_valid = _to_int64(a)
        bv, bv_default = _to_int64(b)
        if b_valid is None:
            b_valid = bv_default
        else:
            b_valid = np.asarray(b_valid, dtype=bool)
            if len(b_valid) != len(bv):
                raise ValueError("b_valid length mismatch")
        bh = _hash_kgrams(bv, b_valid, SEED_K)
        table: dict[int, list[int]] = {}
        for i in range(len(bv) - SEED_K + 1):
            if bh[i]:
                table.setdefault(int(bh[i]), []).append(i)
        ah = _hash_kgrams(av, a_valid, SEED_K)

        _LOCAL_CAP = 64
        best: tuple[int, int, int] | None = None
        for j in range(len(av) - SEED_K + 1):
            if not ah[j]:
                continue
            cand = table.get(int(ah[j]), [])[:_LOCAL_CAP]
            if not cand:
                continue
            ci = np.asarray(cand, dtype=np.int64)
            okc = np.ones(len(ci), dtype=bool)
            for d in range(SEED_K):
                okc &= bv[np.minimum(ci + d, len(bv) - 1)] == av[j + d]
            for i in ci[okc]:
                i = int(i)
                right = SEED_K
                while (j + right < len(av) and i + right < len(bv)
                       and a_valid[j + right] and b_valid[i + right]
                       and av[j + right] == bv[i + right]):
                    right += 1
                left = 0
                while (j - left - 1 >= 0 and i - left - 1 >= 0
                       and a_valid[j - left - 1] and b_valid[i - left - 1]
                       and av[j - left - 1] == bv[i - left - 1]):
                    left += 1
                mlen = right + left
                if best is None or mlen > best[2]:
                    best = (j - left, i - left, mlen)
        return best
