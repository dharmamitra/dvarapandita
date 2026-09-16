import os
import re

import faiss
import numpy as np
import pandas as pd
from tqdm import tqdm
from tqdm.contrib.concurrent import process_map

from utils.constants import *
from utils.indexing import CalculateResults
from utils.general import test_if_should_load
from utils.wordlist_lookup import (
    WORDLIST_MANIFEST_NAME,
    append_compact_rows_from_df,
    save_compact_wordlist_shard,
    write_wordlist_manifest,
)

FILE_EXTENSION = ".p"
WORDLIST_NAME = "wordlist"


def read_file(path):
    """Load a single vector pickle; return empty DataFrame on error."""
    try:
        return pd.read_pickle(path)
    except:
        return pd.DataFrame()


def list_bucket_vector_files(bucket_path, tgt_pattern=None):
    """Sorted .p paths (excluding wordlist shards), same order as former concat.

    If tgt_pattern is given, only files whose basename contains it are kept.
    """
    files = [
        os.path.join(bucket_path, file)
        for file in os.listdir(bucket_path)
        if file.endswith(FILE_EXTENSION)
        and WORDLIST_NAME not in file
        and test_if_should_load(file)
        and (tgt_pattern is None or tgt_pattern in file)
    ]
    return sorted(files)


def _clear_wordlist_artifacts(bucket_path):
    """Remove previous wordlist outputs before rebuilding."""
    mpath = os.path.join(bucket_path, WORDLIST_MANIFEST_NAME)
    if os.path.isfile(mpath):
        os.remove(mpath)
    legacy = os.path.join(bucket_path, "wordlist.p")
    if os.path.isfile(legacy):
        os.remove(legacy)
    for fn in os.listdir(bucket_path):
        if re.match(r"^wordlist_\d+\.p$", fn):
            os.remove(os.path.join(bucket_path, fn))


def _effective_load_workers(load_workers, num_paths):
    if num_paths <= 1:
        return 1
    if load_workers is not None:
        return max(1, min(int(load_workers), num_paths))
    return min(8, os.cpu_count() or 4, num_paths)


def _effective_file_batch_size(file_batch_size, n_paths):
    if n_paths <= 0:
        return 0
    if file_batch_size is None or file_batch_size <= 0:
        return n_paths
    return min(int(file_batch_size), n_paths)


def _load_vector_pickle_for_index(path):
    """
    Load one vector pickle in a worker process. Returns (path, block, slim_df);
    block and slim_df are None when the file is skipped.
    Must be top-level for multiprocessing pickling.
    """
    df = read_file(path)
    if df.empty or "sumvectors" not in df.columns:
        return path, None, None
    if (
        "segmentnr" not in df.columns
        or "original" not in df.columns
        or "analyzed" not in df.columns
    ):
        raise ValueError(
            f"{path} missing segmentnr/original/analyzed columns required for compact wordlist"
        )
    block = np.array(df["sumvectors"].tolist(), dtype="float32")
    if block.size == 0:
        return path, None, None
    slim = df[["segmentnr", "original", "analyzed"]]
    return path, block, slim


def _load_paths_batch(paths, load_workers, tqdm_desc):
    """Load one batch of paths; returns metadata lists and vector chunk list."""
    segments = []
    row_seg = []
    row_tok = []
    vector_chunks = []
    n_workers = _effective_load_workers(load_workers, len(paths))
    if n_workers <= 1:
        for path in tqdm(paths, desc=tqdm_desc, unit="file"):
            _path, block, slim = _load_vector_pickle_for_index(path)
            if block is None or slim is None:
                continue
            append_compact_rows_from_df(slim, segments, row_seg, row_tok)
            vector_chunks.append(block)
    else:
        results = process_map(
            _load_vector_pickle_for_index,
            paths,
            max_workers=n_workers,
            desc=tqdm_desc,
            unit="file",
            chunksize=1,
        )
        for _path, block, slim in tqdm(
            results,
            desc=tqdm_desc + " (merge metadata)",
            unit="file",
            total=len(results),
        ):
            if block is None or slim is None:
                continue
            append_compact_rows_from_df(slim, segments, row_seg, row_tok)
            vector_chunks.append(block)
    return segments, row_seg, row_tok, vector_chunks


def _init_faiss_index(dim, index_method):
    index = faiss.IndexFlatL2(dim)
    if index_method == "cpu":
        index = faiss.IndexHNSWFlat(dim, 32)
        index.hnsw.efConstruction = EF_CONSTRUCTION
    elif index_method == "gpu":
        res = faiss.StandardGpuResources()
        index = faiss.index_cpu_to_gpu(res, 0, index)
    index.verbose = True
    return index


def create_index(
    bucket_path,
    index_method="cpu",
    load_workers=None,
    file_batch_size=10000,
    tgt_pattern=None,
):
    """
    Build FAISS index and sharded compact wordlists (wordlist_1.p, wordlist_2.p, … +
    wordlist_manifest.json). Processes vector pickles in file batches (default 10k
    files) to cap peak RAM, then concatenates each batch’s vectors once, normalizes,
    and index.add. file_batch_size None or <=0 means one batch of all files.

    tgt_pattern: if set, only .p files whose basename contains this substring are
    added to the index.
    """
    print(f"started with {bucket_path}")
    if tgt_pattern:
        print(f"tgt_pattern active: only indexing files containing '{tgt_pattern}'")
    paths = list_bucket_vector_files(bucket_path, tgt_pattern=tgt_pattern)
    if not paths:
        print("No vector files found in bucket")
        return None

    _clear_wordlist_artifacts(bucket_path)

    fsz = _effective_file_batch_size(file_batch_size, len(paths))
    n_batches = (len(paths) + fsz - 1) // fsz
    print(
        f"File batch size: {fsz} ({n_batches} batch(es)); "
        f"sharded wordlists → wordlist_1.p … + {WORDLIST_MANIFEST_NAME}"
    )

    manifest_shards = []
    index = None
    dim = None
    shard_counter = 0

    for b in range(n_batches):
        batch_paths = paths[b * fsz : (b + 1) * fsz]
        tqdm_desc = f"Batch {b + 1}/{n_batches} ({len(batch_paths)} files)"
        segments, row_seg, row_tok, vector_chunks = _load_paths_batch(
            batch_paths, load_workers, tqdm_desc
        )
        if not vector_chunks:
            print(f"  Batch {b + 1}: no vector rows, skipping")
            continue

        shard_counter += 1
        shard_name = f"wordlist_{shard_counter}.p"
        save_compact_wordlist_shard(bucket_path, shard_name, segments, row_seg, row_tok)
        n_rows = len(row_seg)
        manifest_shards.append({"path": shard_name, "n_rows": n_rows})

        print("  Concatenating vector matrix blocks…")
        total_vectors = np.concatenate(vector_chunks, axis=0)
        del vector_chunks
        if dim is None:
            dim = total_vectors.shape[1]
            index = _init_faiss_index(dim, index_method)
        if total_vectors.shape[0] != n_rows:
            raise RuntimeError(
                f"Batch vector rows {total_vectors.shape[0]} != metadata rows {n_rows}"
            )
        print(
            f"  Vector batch: shape {total_vectors.shape}, "
            f"{total_vectors.nbytes / (1024 ** 3):.3f} GiB (float32)"
        )
        faiss.normalize_L2(total_vectors)
        index.add(total_vectors)
        del total_vectors
        print(f"  Index ntotal after batch: {index.ntotal}")

    if index is None or not manifest_shards:
        print("No usable vector rows found")
        return None

    write_wordlist_manifest(bucket_path, manifest_shards)
    total_rows = sum(s["n_rows"] for s in manifest_shards)
    print(f"Wrote {len(manifest_shards)} wordlist shard(s), {total_rows} total rows")

    if index.ntotal != total_rows:
        raise RuntimeError(
            f"FAISS ntotal {index.ntotal} != manifest row sum {total_rows}"
        )

    print("Writing index to disk")
    if index_method == "cpu":
        faiss.write_index(index, os.path.join(bucket_path, "vectors.idx"))
    else:
        return index


def run_calculation(
    bucket_path,
    lang,
    index_method,
    alignment_method,
    src_pattern=None,
    tgt_pattern=None,
    num_processes=16,
    load_workers=None,
    file_batch_size=10000,
):
    index = (
        create_index(
            bucket_path,
            index_method,
            load_workers=load_workers,
            file_batch_size=file_batch_size,
            tgt_pattern=tgt_pattern,
        )
        if index_method == "gpu"
        else None
    )
    calculator = CalculateResults(
        bucket_path,
        lang,
        index_method,
        cindex=index,
        alignment_method=alignment_method,
        src_pattern=src_pattern,
        num_processes=num_processes,
    )
    calculator.run()
