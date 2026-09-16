"""
Compact wordlist storage and lookup for FAISS row positions.

Version 2 stores unique segment metadata once and two uint32 arrays (row_seg, row_tok)
so we do not duplicate original/segmentnr per token row. Legacy DataFrame wordlists
remain supported for loading old indexes.
"""

from __future__ import annotations

import json
import os
import pickle
from typing import Any, List, Sequence, Tuple

import numpy as np
import pandas as pd

from utils.constants import WINDOWSIZE

WORDLIST_VERSION_COMPACT = 2
WORDLIST_MANIFEST_VERSION = 3
WORDLIST_MANIFEST_NAME = "wordlist_manifest.json"


def append_compact_rows_from_df(
    df: pd.DataFrame,
    segments: List[dict],
    row_seg: List[int],
    row_tok: List[int],
) -> None:
    """
    Append metadata for each row of an exploded vector dataframe.
    Rows must be in the same order as sumvectors / FAISS add order.
    Uses column arrays — avoid iterrows(), which is far too slow at millions of rows.
    """
    seg_col = df["segmentnr"].to_numpy()
    orig_col = df["original"].to_numpy()
    ana_col = df["analyzed"].to_numpy()

    seg_key: Tuple[Any, Any] | None = None
    seg_id: int | None = None
    seg_local = 0

    for i in range(len(df)):
        key = (seg_col[i], orig_col[i])
        if key != seg_key:
            seg_key = key
            seg_id = len(segments)
            segments.append(
                {
                    "segmentnr": seg_col[i],
                    "original": orig_col[i],
                    "tokens": [],
                }
            )
            seg_local = 0
        assert seg_id is not None
        row_seg.append(seg_id)
        row_tok.append(seg_local)
        segments[seg_id]["tokens"].append(ana_col[i])
        seg_local += 1


def save_compact_wordlist(
    bucket_path: str,
    segments: List[dict],
    row_seg: Sequence[int],
    row_tok: Sequence[int],
) -> None:
    payload = {
        "version": WORDLIST_VERSION_COMPACT,
        "segments": segments,
        "row_seg": np.asarray(row_seg, dtype=np.uint32),
        "row_tok": np.asarray(row_tok, dtype=np.uint32),
    }
    out = os.path.join(bucket_path, "wordlist.p")
    with open(out, "wb") as f:
        pickle.dump(payload, f)


def save_compact_wordlist_shard(
    bucket_path: str,
    shard_filename: str,
    segments: List[dict],
    row_seg: Sequence[int],
    row_tok: Sequence[int],
) -> None:
    """Write one shard (e.g. wordlist_1.p) for batched index builds."""
    payload = {
        "version": WORDLIST_VERSION_COMPACT,
        "segments": segments,
        "row_seg": np.asarray(row_seg, dtype=np.uint32),
        "row_tok": np.asarray(row_tok, dtype=np.uint32),
    }
    out = os.path.join(bucket_path, shard_filename)
    with open(out, "wb") as f:
        pickle.dump(payload, f)


def write_wordlist_manifest(bucket_path: str, shards: List[dict]) -> None:
    """shards: list of {"path": "wordlist_1.p", "n_rows": int} in global order."""
    manifest = {
        "version": WORDLIST_MANIFEST_VERSION,
        "format": "sharded_compact",
        "shards": shards,
    }
    path = os.path.join(bucket_path, WORDLIST_MANIFEST_NAME)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)


class WordlistAccess:
    wordlist_len: int

    def hit_data(self, position: int, lang: str) -> Tuple[Any, Any, str]:
        """(segmentnr, original, stems_match_string) for one FAISS row."""
        return (self.segmentnr(position), self.original(position),
                self.stems_match_string(position, lang))

    def segmentnr(self, position: int) -> Any:
        raise NotImplementedError

    def original(self, position: int) -> Any:
        raise NotImplementedError

    def stems_match_string(self, position: int, lang: str) -> str:
        raise NotImplementedError


class LegacyWordlistAccess(WordlistAccess):
    """Full per-row strings (same memory profile as old list-based globals)."""

    def __init__(self, df: pd.DataFrame):
        self._segmentnr = (
            df["segmentnr"].tolist() if "segmentnr" in df.columns else [""] * len(df)
        )
        self._original = (
            df["original"].tolist() if "original" in df.columns else [""] * len(df)
        )
        if "token" in df.columns:
            col = "token"
        elif "analyzed" in df.columns:
            col = "analyzed"
        else:
            col = None
        self._stems = df[col].tolist() if col else [""] * len(df)
        self.wordlist_len = len(df)

    def segmentnr(self, position: int) -> Any:
        return self._segmentnr[position]

    def original(self, position: int) -> Any:
        return self._original[position]

    def stems_match_string(self, position: int, lang: str) -> str:
        if lang == "eng":
            return str(self._stems[position])
        end = min(position + WINDOWSIZE[lang], self.wordlist_len)
        parts = []
        for p in range(position, end):
            parts.append(str(self._stems[p]))
        return " ".join(parts)


class CompactWordlistAccess(WordlistAccess):
    def __init__(self, data: dict):
        self.segments = data["segments"]
        self.row_seg = np.asarray(data["row_seg"], dtype=np.uint32)
        self.row_tok = np.asarray(data["row_tok"], dtype=np.uint32)
        self.wordlist_len = int(self.row_seg.shape[0])

    def _token_at(self, position: int) -> str:
        sid = int(self.row_seg[position])
        ti = int(self.row_tok[position])
        return str(self.segments[sid]["tokens"][ti])

    def token_at(self, position: int) -> str:
        """Single analyzed token at a local row index (for sharded lookups)."""
        return self._token_at(position)

    def segmentnr(self, position: int) -> Any:
        sid = int(self.row_seg[position])
        return self.segments[sid]["segmentnr"]

    def original(self, position: int) -> Any:
        sid = int(self.row_seg[position])
        return self.segments[sid]["original"]

    def stems_match_string(self, position: int, lang: str) -> str:
        if lang == "eng":
            return self._token_at(position)
        end = min(position + WINDOWSIZE[lang], self.wordlist_len)
        return self.window_string(position, end)

    def window_string(self, start: int, end: int) -> str:
        """Space-joined analyzed tokens for local rows [start, end): two array
        slices instead of two numpy scalar reads per token."""
        segs = self.row_seg[start:end].tolist()
        toks = self.row_tok[start:end].tolist()
        segments = self.segments
        return " ".join(str(segments[s]["tokens"][t]) for s, t in zip(segs, toks))


class ShardedWordlistAccess(WordlistAccess):
    """
    Multiple compact shards (wordlist_1.p, …); global FAISS row id maps to one shard
    via prefix offsets. Windows can span shard boundaries (stems from adjacent shards).
    """

    def __init__(self, bucket_path: str, manifest: dict):
        self._shard_accesses: List[CompactWordlistAccess] = []
        n_rows_list: List[int] = []
        for entry in manifest["shards"]:
            rel = entry["path"]
            path = os.path.join(bucket_path, rel)
            with open(path, "rb") as f:
                data = pickle.load(f)
            if not isinstance(data, dict) or data.get("version") != WORDLIST_VERSION_COMPACT:
                raise ValueError(f"Bad shard format: {path}")
            acc = CompactWordlistAccess(data)
            self._shard_accesses.append(acc)
            n_rows_list.append(acc.wordlist_len)

        self._offsets = np.zeros(len(n_rows_list) + 1, dtype=np.int64)
        self._offsets[1:] = np.cumsum(n_rows_list)
        self.wordlist_len = int(self._offsets[-1])

    def _map_global(self, global_pos: int) -> Tuple[int, int]:
        if global_pos < 0 or global_pos >= self.wordlist_len:
            raise IndexError(f"wordlist position {global_pos} out of range [0, {self.wordlist_len})")
        shard_i = int(np.searchsorted(self._offsets[1:], global_pos, side="right"))
        local = int(global_pos - self._offsets[shard_i])
        return shard_i, local

    def segmentnr(self, position: int) -> Any:
        si, li = self._map_global(position)
        return self._shard_accesses[si].segmentnr(li)

    def original(self, position: int) -> Any:
        si, li = self._map_global(position)
        return self._shard_accesses[si].original(li)

    def hit_data(self, position: int, lang: str) -> Tuple[Any, Any, str]:
        si, li = self._map_global(position)
        shard = self._shard_accesses[si]
        seg = shard.segments[int(shard.row_seg[li])]
        if lang == "eng":
            return seg["segmentnr"], seg["original"], shard.token_at(li)
        end = min(position + WINDOWSIZE[lang], self.wordlist_len)
        if end <= int(self._offsets[si + 1]):
            stems = shard.window_string(li, li + (end - position))
        else:
            stems = self.stems_match_string(position, lang)
        return seg["segmentnr"], seg["original"], stems

    def stems_match_string(self, position: int, lang: str) -> str:
        if lang == "eng":
            si, li = self._map_global(position)
            return self._shard_accesses[si].token_at(li)
        end = min(position + WINDOWSIZE[lang], self.wordlist_len)
        si, li = self._map_global(position)
        shard_end = int(self._offsets[si + 1])
        if end <= shard_end:
            # common case: the whole window lies in one shard
            return self._shard_accesses[si].window_string(li, li + (end - position))
        parts = []
        for p in range(position, end):
            si, li = self._map_global(p)
            parts.append(self._shard_accesses[si].token_at(li))
        return " ".join(parts)


def load_wordlist_access(bucket_path: str) -> WordlistAccess:
    manifest_path = os.path.join(bucket_path, WORDLIST_MANIFEST_NAME)
    if os.path.isfile(manifest_path):
        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest = json.load(f)
        if manifest.get("version") == WORDLIST_MANIFEST_VERSION and manifest.get("format") == "sharded_compact":
            return ShardedWordlistAccess(bucket_path, manifest)

    path = os.path.join(bucket_path, "wordlist.p")
    with open(path, "rb") as f:
        data = pickle.load(f)

    if isinstance(data, dict) and data.get("version") == WORDLIST_VERSION_COMPACT:
        return CompactWordlistAccess(data)

    if isinstance(data, pd.DataFrame):
        return LegacyWordlistAccess(data)

    if isinstance(data, dict) and "df" in data:
        return LegacyWordlistAccess(data["df"])

    raise ValueError(f"Unsupported wordlist format in {path}")
