"""Merge two folders of ndjson.gz match files into the first folder.

For each file in folder B:
  - If it does not exist in folder A, copy it over.
  - If it exists in both, read both, concatenate matches, deduplicate, and
    write the merged result back to folder A.

Duplicates are identified by the 'id' field; on collision the match with the
higher 'score' is kept. Matches without an 'id' fall back to a composite key
of sorted (root_segnr, par_segnr).
"""

import argparse
import gzip
import os
import shutil
import sys
from concurrent.futures import ProcessPoolExecutor, as_completed

from tqdm import tqdm

try:
    import orjson

    def _loads(data):
        return orjson.loads(data)

    def _dumps(obj):
        return orjson.dumps(obj)
except ImportError:
    import json

    def _loads(data):
        return json.loads(data)

    def _dumps(obj):
        return json.dumps(obj, ensure_ascii=False).encode("utf-8")


def read_ndjson_gz(path):
    matches = []
    with gzip.open(path, "rb") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            matches.append(_loads(line))
    return matches


def write_ndjson_gz_atomic(matches, path):
    tmp_path = path + ".tmp"
    try:
        with gzip.open(tmp_path, "wb", compresslevel=6) as f:
            for m in matches:
                f.write(_dumps(m))
                f.write(b"\n")
        os.replace(tmp_path, path)
    except Exception:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        raise


def dedup_key(match):
    mid = match.get("id")
    if mid is not None:
        return ("id", mid)
    return (
        "seg",
        tuple(sorted(match.get("root_segnr", []))),
        tuple(sorted(match.get("par_segnr", []))),
    )


def deduplicate(matches):
    best = {}
    for m in matches:
        key = dedup_key(m)
        cur = best.get(key)
        if cur is None or m.get("score", 0) > cur.get("score", 0):
            best[key] = m
    return list(best.values())


def process_file(filename, folder_a, folder_b):
    path_a = os.path.join(folder_a, filename)
    path_b = os.path.join(folder_b, filename)

    if not os.path.exists(path_a):
        shutil.copy2(path_b, path_a)
        return filename, "copied", 0

    matches_a = read_ndjson_gz(path_a)
    matches_b = read_ndjson_gz(path_b)
    total_before = len(matches_a) + len(matches_b)
    merged = deduplicate(matches_a + matches_b)
    removed = total_before - len(merged)
    write_ndjson_gz_atomic(merged, path_a)
    return filename, "merged", removed


def list_match_files(folder):
    return {
        f
        for f in os.listdir(folder)
        if f.endswith(".ndjson.gz") and os.path.isfile(os.path.join(folder, f))
    }


def main():
    parser = argparse.ArgumentParser(
        description="Merge matches from folder B into folder A (in place)."
    )
    parser.add_argument("folder_a", help="Target folder (modified in place).")
    parser.add_argument("folder_b", help="Source folder to merge from.")
    parser.add_argument(
        "--workers",
        "--threads",
        dest="workers",
        type=int,
        default=os.cpu_count() or 8,
        help="Number of worker processes (default: number of CPU cores).",
    )
    args = parser.parse_args()

    folder_a = os.path.abspath(args.folder_a)
    folder_b = os.path.abspath(args.folder_b)

    if not os.path.isdir(folder_a):
        sys.exit(f"folder_a does not exist: {folder_a}")
    if not os.path.isdir(folder_b):
        sys.exit(f"folder_b does not exist: {folder_b}")

    files_b = sorted(list_match_files(folder_b))
    if not files_b:
        print(f"No .ndjson.gz files in {folder_b}")
        return

    print(
        f"Merging {len(files_b)} files from {folder_b} into {folder_a} "
        f"using {args.workers} processes."
    )

    copied = 0
    merged = 0
    removed_total = 0
    errors = []

    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        futures = {
            pool.submit(process_file, fn, folder_a, folder_b): fn for fn in files_b
        }
        for fut in tqdm(as_completed(futures), total=len(futures)):
            fn = futures[fut]
            try:
                _, action, removed = fut.result()
                if action == "copied":
                    copied += 1
                else:
                    merged += 1
                    removed_total += removed
            except Exception as e:
                errors.append((fn, str(e)))

    print(
        f"Done. copied={copied} merged={merged} duplicates_removed={removed_total} "
        f"errors={len(errors)}"
    )
    for fn, err in errors[:20]:
        print(f"  ERROR {fn}: {err}")


if __name__ == "__main__":
    main()
