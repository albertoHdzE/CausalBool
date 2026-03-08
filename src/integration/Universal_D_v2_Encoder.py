import numpy as np
import math
from typing import Dict, Any, List, Tuple

class UniversalDv2Encoder:
    def __init__(self, adjacency_matrix: np.ndarray, block_sizes: List[int] | None = None, stride: int = 1):
        self.cm = np.array(adjacency_matrix).astype(int)
        self.n = self.cm.shape[0]
        self.stride = max(1, int(stride))
        self.block_sizes = block_sizes if block_sizes is not None else [4, 5, 6]

    def _extract_blocks(self, b: int) -> List[np.ndarray]:
        m = self.cm
        n = self.n
        blocks = []
        pad = (b - (n % b)) % b
        if pad > 0:
            m = np.pad(m, ((0, pad), (0, pad)), mode="constant", constant_values=0)
            n = m.shape[0]
        for i in range(0, n - b + 1, self.stride):
            for j in range(0, n - b + 1, self.stride):
                blocks.append(m[i:i + b, j:j + b])
        return blocks

    def _block_key(self, block: np.ndarray) -> Tuple[int, int]:
        ones = int(block.sum())
        size = block.size
        return (size, ones)

    def _block_complexity(self, block: np.ndarray) -> float:
        size = block.size
        ones = int(block.sum())
        p = ones / max(1, size)
        if p == 0.0 or p == 1.0:
            h = 0.0
        else:
            h = -(p * math.log2(p) + (1 - p) * math.log2(1 - p))
        return h * size

    def compute(self) -> Dict[str, Any]:
        dv2 = 0.0
        detail = {}
        for b in self.block_sizes:
            blocks = self._extract_blocks(b)
            counts: Dict[Tuple[int, int], int] = {}
            base: Dict[Tuple[int, int], float] = {}
            for blk in blocks:
                k = self._block_key(blk)
                counts[k] = counts.get(k, 0) + 1
            for k in counts.keys():
                size, ones = k
                blk = np.ones((int(math.sqrt(size)), int(math.sqrt(size))), dtype=int)
                if ones == 0:
                    blk[:] = 0
                base[k] = self._block_complexity(blk)
            total = 0.0
            for k, c in counts.items():
                total += base[k] + math.log2(c)
            dv2 += total
            detail[f"b{b}"] = {"unique_blocks": len(counts), "total_blocks": len(blocks), "cost": total}
        return {"dv2": dv2, "detail": detail, "n": self.n, "blocks": self.block_sizes}
