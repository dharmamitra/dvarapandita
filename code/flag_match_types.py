#!/usr/bin/env python3
"""Boilerplate flagging: add a match_type field to every match in a corpus.

Runs as the last stage of the dvarapandita pipeline, after
merge-results-for-db has written the per-file <name>.ndjson.gz matches.

  match_type in {paratext, edition, frame, procedural, stock, pericope,
                 reuse-candidate, embedding, parallel, unknown}

Content categories (per-passage, from oracle-labeled clusters + classifier):
the first six are formulaic conventions, "reuse-candidate" is traceable
content, "unknown" = classifier below confidence threshold (treat as keep).

Structural categories (from match GEOMETRY, not content -- step 6 overlay):
  embedding: one text incorporated wholesale into another (base text inside
             a commentary, sutra inside a liturgical manual/anthology).
             Asymmetric: matches cover >=40% of the shorter text, <50% of
             the longer.
  parallel:  structural siblings -- recensions/editions of the same text,
             repetition-series siblings (Yamaka grids, PP cycles).
             Symmetric: matches cover >=50% of BOTH texts.
The overlay only ever relabels {reuse-candidate, pericope, unknown,
procedural} -- auditable head labels (paratext/edition/frame/stock) are
never touched, and both structural categories are keep-worthy, so the
overlay cannot hide anything that was visible before.

Method (cluster -> oracle-label -> propagate -> distill -> geometry):
  1. count-pass: normalized fingerprint counts over all matched strings
  2. head-pass: stats + representatives for recurring fingerprints,
     leader-clustered (Jaccard vs cluster representative, no chaining)
  3. oracle: gemini flash-lite labels the top clusters with the closed
     7-category taxonomy (needs GEMINI_API_KEY or --secrets-env)
  4. train: fastText distilled from labels propagated to member strings
  5. annotate: rewrite every ndjson.gz in place -- cluster label where the
     fingerprint is known, thresholded fastText prediction otherwise
  6. geometry overlay (during 5): per text-pair, coverage = distinct
     segments matched within the pair / the text's total matched-segment
     extent (distinct segments it matches against anyone, corpus-wide).
     Segment-based because char offsets are not text-relative in every
     corpus (zh positions are bucket-global). The denominator is the
     text's MATCHABLE extent, not its true length -- for sparsely matched
     texts this overstates coverage; min-segment guards bound the damage.

Every step caches its artifact in --state-dir and is skipped when the
artifact already exists, so a crashed run resumes where it stopped.

Usage:
  python flag_match_types.py --matches-dir DIR --lang tib --state-dir STATE \
      [--threads 32] [--min-count 25] [--n-label 20000] \
      [--model M.bin] [--secrets-env PATH] [--tau 0.7]

With --model and an existing fp2cat.pkl in --state-dir, steps 1-4 are
skipped and only annotation runs (classify-only mode for incremental data).
"""
import argparse
import gzip
import hashlib
import json
import os
import pickle
import re
import sys
import threading
import time
import unicodedata
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from multiprocessing import Pool

import numpy as np

# fasttext 0.9.x calls np.array(..., copy=False), rejected by numpy>=2
_np_array = np.array


def _np_array_compat(*a, **k):
    if k.get("copy") is False:
        k.pop("copy")
        return np.asarray(*a, **k)
    return _np_array(*a, **k)


np.array = _np_array_compat

import orjson  # noqa: E402

# --------------------------------------------------------------- lang handling

LANG_MODE = {  # zh: han-character fingerprints; lat: romanized
    "chn": "zh", "zh": "zh",
    "tib": "lat", "bo": "lat", "skt": "lat", "sa": "lat",
    "pli": "lat", "pa": "lat",
}

LANG_DESC = {
    "pa": "Pali (Theravada canon and commentaries, romanized)",
    "sa": "Sanskrit (Buddhist, epic, puranic, tantric literature, IAST)",
    "bo": "Classical Tibetan (Kangyur/Tengyur/Sungbum/Terma, Wylie)",
    "zh": "Classical Chinese (Taisho/Kanripo canon plus Confucian, Daoist, "
          "historical and medical works)",
}
LANG_CANON = {"chn": "zh", "zh": "zh", "tib": "bo", "bo": "bo",
              "skt": "sa", "sa": "sa", "pli": "pa", "pa": "pa"}

# ------------------------------------------------------------- normalization

RE_AT = re.compile(r"@[^ ]+")
RE_LAT = re.compile(r"[^a-z'+]+")
RE_HAN = re.compile(r"[^一-鿿㐀-䶿]")


def norm_lat(s: str) -> str:
    s = RE_AT.sub(" ", s)
    s = unicodedata.normalize("NFD", s.lower())
    s = "".join(c for c in s if not unicodedata.combining(c))
    return " ".join(RE_LAT.sub(" ", s).split())


def norm_zh_chars(s: str) -> str:
    return RE_HAN.sub("", s)


def fingerprint(s: str, mode: str):
    if mode == "zh":
        n = norm_zh_chars(s)[:40]
        if len(n) < 8:
            return None
    else:
        n = norm_lat(s)[:120]
        if len(n) < 20:
            return None
    return hashlib.blake2b(n.encode(), digest_size=8).digest()


def ft_input(s: str, mode: str) -> str:
    if mode == "zh":
        return " ".join(norm_zh_chars(s))
    return norm_lat(s)


# ------------------------------------------------------------------ step 1

_MODE = None


def _count_file(path):
    cnt = Counter()
    maxpos = 0
    segs = defaultdict(set)     # segnr-derived text id -> distinct root segnrs
    try:
        with gzip.open(path, "rb") as f:
            for line in f:
                try:
                    d = orjson.loads(line)
                except Exception:
                    continue
                rs = d.get("root_string")
                if not rs:
                    continue
                fp = fingerprint(rs, _MODE)
                if fp:
                    cnt[fp] += 1
                p = d.get("inquiry_pos_end", 0)
                if p > maxpos:
                    maxpos = p
                sn = d.get("root_segnr")
                if sn:
                    segs[sn[0].split(":")[0]].update(sn)
    except Exception as e:
        sys.stderr.write(f"count ERR {path}: {e}\n")
    return (os.path.basename(path), cnt, maxpos,
            {k: len(v) for k, v in segs.items()})


def _init_mode(mode):
    global _MODE
    _MODE = mode


def step_count(files, mode, threads, out_path):
    total = Counter()
    textlens = {}
    nsegs = {}
    with Pool(threads, initializer=_init_mode, initargs=(mode,)) as pool:
        for i, (fname, cnt, maxpos, fsegs) in enumerate(
                pool.imap_unordered(_count_file, files, chunksize=4)):
            total.update(cnt)
            textlens[fname.replace(".ndjson.gz", "")] = maxpos
            for k, v in fsegs.items():
                nsegs[k] = nsegs.get(k, 0) + v
            if (i + 1) % 1000 == 0:
                print(f"  count {i + 1}/{len(files)}", flush=True)
    kept = {k: v for k, v in total.items() if v >= 3}
    with open(out_path, "wb") as f:
        pickle.dump({"counts": kept, "n_matches": sum(total.values()),
                     "textlens": textlens, "nsegs": nsegs}, f)
    print(f"  count done: {sum(total.values())} matches, "
          f"{len(kept)} recurring fingerprints, {len(nsegs)} texts")


# ------------------------------------------------------------------ step 2

_HEAD = None
_TEXTLENS = None


def _init_head(mode, head_path):
    global _MODE, _HEAD, _TEXTLENS
    _MODE = mode
    with open(head_path, "rb") as f:
        d = pickle.load(f)
    _HEAD = d["head"]
    _TEXTLENS = d["textlens"]


def _collect_file(path):
    out = {}
    try:
        with gzip.open(path, "rb") as f:
            for line in f:
                try:
                    d = orjson.loads(line)
                except Exception:
                    continue
                rs = d.get("root_string")
                if not rs:
                    continue
                fp = fingerprint(rs, _MODE)
                if fp is None or fp not in _HEAD:
                    continue
                a = out.get(fp)
                if a is None:
                    # count, root_files, tgt_files, pos_root, reps
                    a = out[fp] = [0, set(), set(), [], []]
                a[0] += 1
                rf = d["root_segnr"][0].split(":")[0]
                tf = d["par_segnr"][0].split(":")[0]
                if len(a[1]) < 500:
                    a[1].add(rf)
                if len(a[2]) < 500:
                    a[2].add(tf)
                rl = _TEXTLENS.get(rf)
                if rl and len(a[3]) < 50:
                    a[3].append(min(1.0, d.get("inquiry_pos_beg", 0) / rl))
                if len(a[4]) < 3:
                    a[4].append(rs[:400])
    except Exception as e:
        sys.stderr.write(f"collect ERR {path}: {e}\n")
    return out


def step_collect(files, mode, threads, counts_path, min_count, out_path):
    with open(counts_path, "rb") as f:
        cp = pickle.load(f)
    head = {k for k, v in cp["counts"].items() if v >= min_count}
    head_path = out_path + ".head_tmp"
    with open(head_path, "wb") as f:
        pickle.dump({"head": head, "textlens": cp["textlens"]}, f)
    print(f"  {len(head)} head fingerprints (min_count={min_count})")
    agg = {}
    with Pool(threads, initializer=_init_head,
              initargs=(mode, head_path)) as pool:
        for i, part in enumerate(
                pool.imap_unordered(_collect_file, files, chunksize=4)):
            for fp, a in part.items():
                t = agg.get(fp)
                if t is None:
                    agg[fp] = a
                    continue
                t[0] += a[0]
                if len(t[1]) < 500:
                    t[1].update(a[1])
                if len(t[2]) < 500:
                    t[2].update(a[2])
                if len(t[3]) < 50:
                    t[3].extend(a[3])
                if len(t[4]) < 3:
                    t[4].extend(a[4])
            if (i + 1) % 1000 == 0:
                print(f"  collect {i + 1}/{len(files)}", flush=True)
    os.remove(head_path)
    with open(out_path, "wb") as f:
        pickle.dump(agg, f)
    print(f"  collect done: {len(agg)} head fingerprints aggregated")


# ------------------------------------------------------------------ step 3

def _shingles(s, mode):
    if mode == "zh":
        n = norm_zh_chars(s)
        return {n[i:i + 6] for i in range(0, max(1, len(n) - 5))}
    n = norm_lat(s)
    w = n.split()
    return {" ".join(w[i:i + 4]) for i in range(0, max(1, len(w) - 3))}


def leader_cluster(agg, mode):
    """agg: fp -> [count, root_files, tgt_files, pos_root, reps]"""
    fps = sorted(agg.keys(), key=lambda fp: -agg[fp][0])
    inv = defaultdict(list)
    cl_sh = []
    clusters = defaultdict(list)
    for fp in fps:
        sh = _shingles(agg[fp][4][0], mode)
        if not sh:
            clusters[len(cl_sh)].append(fp)
            cl_sh.append(set())
            continue
        sig = sorted(hashlib.blake2b(x.encode(), digest_size=8).digest()
                     for x in sh)[:12]
        cand = Counter()
        for h in sig:
            for cid in inv[h][:20]:
                cand[cid] += 1
        best = None
        for cid, _ in cand.most_common(5):
            ref = cl_sh[cid]
            if ref and len(sh & ref) / len(sh | ref) >= 0.35:
                best = cid
                break
        if best is None:
            best = len(cl_sh)
            cl_sh.append(sh)
            for h in sig:
                inv[h].append(best)
        clusters[best].append(fp)
    rows = sorted(((sum(agg[fp][0] for fp in m), m)
                   for m in clusters.values()), key=lambda r: -r[0])
    return [m for _, m in rows]


TAXONOMY = """Categories (choose exactly one per cluster):

- paratext: packaging of the text object — titles, homage/salutation before the text, translation or authorship colophons, chapter/section end markers, uddana/summary verses, "here ends X".
- edition: editorial or printing boilerplate of a particular edition/database — e.g. Siku Quanshu compiler credits, Muktabodha e-text headers, modern printing dedications, page furniture.
- frame: narrative opening/closing conventions of scripture — "thus have I heard, at one time...", setting-the-scene passages, concluding "...rejoiced and praised" formulas, jataka/apadana framing verses, "wishing to restate the meaning he spoke this verse".
- procedural: legal/ritual procedure formulas — vinaya karmavacana, "the sangha is silent, thus it is held", "I allow, monks...", instructions to repeat ("second and third time likewise"), ritual/liturgical action sequences, dharani/mantra chains.
- stock: stock phrases and genre conventions inside running prose — epithet chains, "if a good son or good daughter...", fourfold assembly lists, Chan dialogue openers, narrative transitions ("then the Blessed One said..."), ubiquitous technical terms, dosage/recipe patterns, polite address formulas.
- pericope: repeated doctrinal exposition blocks shared across texts of a genre — skandha/dhatu/faculty lists, abhidhamma matrices, Prajnaparamita repetition cycles, "...pe..." elision blocks, catechism chains. Doctrinally meaningful but repeated as a template.
- reuse-candidate: a specific traceable passage — a particular verse or doctrinal statement whose recurrence looks like genuine quotation/transmission rather than convention. A scholar wants to see ALL occurrences of THIS passage.

Decision rule when torn: ask "would every text of this genre contain this wording anyway, regardless of any specific textual relationship?" If yes -> one of the six formulaic categories. If the wording identifies one specific source passage -> reuse-candidate. Short ubiquitous terms or epithets are stock, never reuse-candidate."""

ORACLE_PROMPT = """You are a philologist labeling recurring match clusters from an all-against-all alignment of a large {langdesc} corpus.

Stats per cluster: n = number of pairwise matches, root_files/tgt_files = distinct texts containing it, pos = mean relative position in text (0=start, 1=end).

{taxonomy}

For each cluster output: {{"id": <id>, "category": "<one of: paratext|edition|frame|procedural|stock|pericope|reuse-candidate>"}}
Output ONLY a JSON array, no other text.

Clusters:
{items}"""

VALID_CATS = {"paratext", "edition", "frame", "procedural", "stock",
              "pericope", "reuse-candidate"}


def get_api_key(secrets_env=None):
    key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if key:
        return key
    if secrets_env and os.path.exists(secrets_env):
        for line in open(secrets_env):
            line = line.strip()
            if line.startswith(("GEMINI_API_KEY=", "GOOGLE_API_KEY=")):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    raise RuntimeError("no GEMINI_API_KEY; pass --secrets-env or --model "
                       "for classify-only mode")


def call_gemini(prompt, key, model="gemini-3.1-flash-lite", retries=5):
    import requests
    url = ("https://generativelanguage.googleapis.com/v1beta/models/"
           f"{model}:generateContent?key={key}")
    payload = {"contents": [{"parts": [{"text": prompt}]}],
               "generationConfig": {"temperature": 0.0,
                                    "maxOutputTokens": 4096,
                                    "thinkingConfig": {"thinkingBudget": 0}}}
    last = None
    for attempt in range(retries):
        try:
            resp = requests.post(url, json=payload, timeout=300)
            resp.raise_for_status()
            parts = resp.json()["candidates"][0]["content"]["parts"]
            return "".join(p.get("text", "") for p in parts
                           if not p.get("thought")).strip()
        except Exception as e:
            last = e
            time.sleep(2.0 * (2 ** attempt))
    raise RuntimeError(f"gemini failed: {last}")


def step_oracle(agg, cluster_rows, lang, n_label, key, out_path):
    langdesc = LANG_DESC[LANG_CANON[lang]]
    rows = cluster_rows[:n_label]
    B = 16
    batches = []
    for i in range(0, len(rows), B):
        batch = []
        for j, members in enumerate(rows[i:i + B]):
            big = max(members, key=lambda fp: agg[fp][0])
            count = sum(agg[fp][0] for fp in members)
            rfiles = len(set().union(*(agg[fp][1] for fp in members)))
            tfiles = len(set().union(*(agg[fp][2] for fp in members)))
            pos = [p for fp in members for p in agg[fp][3]]
            mp = round(sum(pos) / len(pos), 2) if pos else "?"
            batch.append((i + j,
                          f"id={i + j} n={count} root_files={rfiles} "
                          f"tgt_files={tfiles} pos={mp}\n"
                          f"text: {agg[big][4][0][:300]}\n"))
        batches.append(batch)
    results = {}
    lock = threading.Lock()

    def work(b):
        prompt = ORACLE_PROMPT.format(
            langdesc=langdesc, taxonomy=TAXONOMY,
            items="\n".join(x[1] for x in b))
        try:
            txt = call_gemini(prompt, key)
            if txt.startswith("```"):
                txt = txt.split("```")[1]
                if txt.startswith("json"):
                    txt = txt[4:]
            for o in json.loads(txt):
                if o.get("category") in VALID_CATS:
                    with lock:
                        results[o["id"]] = o["category"]
        except Exception as e:
            sys.stderr.write(f"oracle batch fail: {e}\n")

    with ThreadPoolExecutor(12) as ex:
        futs = [ex.submit(work, b) for b in batches]
        for i, f in enumerate(as_completed(futs)):
            f.result()
            if (i + 1) % 100 == 0:
                print(f"  oracle {i + 1}/{len(batches)} batches", flush=True)
    with open(out_path, "w") as f:
        json.dump({str(k): v for k, v in results.items()}, f)
    print(f"  oracle done: {len(results)}/{len(rows)} clusters labeled")
    return results


# ------------------------------------------------------------------ step 4

def step_train(agg, cluster_rows, labels, mode, state_dir, model_path):
    import fasttext
    train_file = os.path.join(state_dir, "ft_train.txt")
    n_ex = 0
    with open(train_file, "w") as f:
        for idx, members in enumerate(cluster_rows):
            cat = labels.get(idx)
            if cat is None:
                continue
            exs = []
            for fp in members:
                for r in agg[fp][4]:
                    n = ft_input(r, mode)
                    if len(n) >= 15:
                        exs.append(n)
            for e in exs[:200]:
                f.write(f"__label__{cat} {e}\n")
                n_ex += 1
    print(f"  training fastText on {n_ex} examples")
    if mode == "zh":
        model = fasttext.train_supervised(
            train_file, lr=0.5, epoch=25, dim=100, wordNgrams=3,
            minn=0, maxn=0, minCount=1, verbose=0)
    else:
        model = fasttext.train_supervised(
            train_file, lr=0.5, epoch=25, dim=100, wordNgrams=2,
            minn=2, maxn=5, minCount=1, verbose=0)
    model.quantize(input=train_file, retrain=False, qnorm=True)
    model.save_model(model_path)
    print(f"  model saved: {model_path} "
          f"({os.path.getsize(model_path) // 2**20} MB)")


# ------------------------------------------------------- steps 5+6 (annotate)

_FP2CAT = None
_MODEL = None
_TAU = 0.7
_ANN_NSEGS = None
_OVERLAY = True

# geometry overlay thresholds -- see module docstring for rationale
PARALLEL_COV = 0.5      # both texts covered >= this -> parallel
EMBED_COV = 0.4         # shorter text covered >= this (longer < 0.5) -> embedding
MIN_SEGS = 30           # ignore texts with fewer matched segments than this
MIN_PAIR_SEGS = 20      # ignore pairs matching fewer distinct segments
OVERRIDABLE = {"reuse-candidate", "pericope", "unknown", "procedural"}


def _init_annotate(mode, fp2cat_path, model_path, tau, nsegs, overlay):
    global _MODE, _FP2CAT, _MODEL, _TAU, _ANN_NSEGS, _OVERLAY
    import fasttext
    _MODE = mode
    with open(fp2cat_path, "rb") as f:
        _FP2CAT = pickle.load(f)
    _MODEL = fasttext.load_model(model_path)
    _TAU = tau
    _ANN_NSEGS = nsegs
    _OVERLAY = overlay


def _classify(rs):
    fp = fingerprint(rs, _MODE)
    if fp is not None:
        cat = _FP2CAT.get(fp)
        if cat is not None:
            return cat
    n = ft_input(rs, _MODE)
    if len(n) < 10:
        return "unknown"
    labels, probs = _MODEL.predict(n)
    if probs[0] >= _TAU:
        return labels[0].replace("__label__", "")
    return "unknown"


def _pair_verdicts(pairs):
    """pairs: (rf, tf) -> [root segnr set, target segnr set]"""
    verdicts = {}
    for (rf, tf), (rs_, ts_) in pairs.items():
        nr = _ANN_NSEGS.get(rf)
        nt = _ANN_NSEGS.get(tf)
        if not nr or not nt or min(nr, nt) < MIN_SEGS:
            continue
        if max(len(rs_), len(ts_)) < MIN_PAIR_SEGS:
            continue
        cov_r = min(1.0, len(rs_) / nr)
        cov_t = min(1.0, len(ts_) / nt)
        if cov_r >= PARALLEL_COV and cov_t >= PARALLEL_COV:
            verdicts[(rf, tf)] = "parallel"
        else:
            cov_short, cov_long = ((cov_r, cov_t) if nr <= nt
                                   else (cov_t, cov_r))
            if cov_short >= EMBED_COV and cov_long < PARALLEL_COV:
                verdicts[(rf, tf)] = "embedding"
    return verdicts


def _annotate_file(path):
    tmp = path + ".mt_tmp"
    stats = Counter()
    try:
        # pass A: classify every line, collect per-pair matched segment sets
        labels = []
        pairs = defaultdict(lambda: (set(), set()))
        pair_of = []
        with gzip.open(path, "rb") as fin:
            for line in fin:
                if not line.strip():
                    continue
                try:
                    d = orjson.loads(line)
                    rs = d.get("root_string", "")
                    labels.append(_classify(rs) if rs else "unknown")
                    rf = d["root_segnr"][0].split(":")[0]
                    tf = d["par_segnr"][0].split(":")[0]
                    if _OVERLAY and rf != tf:
                        ri, ti = pairs[(rf, tf)]
                        ri.update(d["root_segnr"])
                        ti.update(d["par_segnr"])
                        pair_of.append((rf, tf))
                    else:
                        pair_of.append(None)
                except Exception:
                    labels.append(None)         # passthrough
                    pair_of.append(None)
        verdicts = _pair_verdicts(pairs) if _OVERLAY else {}

        # pass B: re-read, apply labels (+ structural override), write
        i = 0
        n_out = 0
        with gzip.open(path, "rb") as fin, \
                gzip.open(tmp, "wb", compresslevel=6) as fout:
            for line in fin:
                if not line.strip():
                    continue
                lab = labels[i]
                if lab is None:
                    fout.write(line.rstrip(b"\n") + b"\n")
                    stats["passthrough"] += 1
                else:
                    d = orjson.loads(line)
                    pv = verdicts.get(pair_of[i]) if pair_of[i] else None
                    if pv and lab in OVERRIDABLE:
                        lab = pv
                    d["match_type"] = lab
                    stats[lab] += 1
                    fout.write(orjson.dumps(d) + b"\n")
                i += 1
                n_out += 1
        if n_out != len(labels):
            os.remove(tmp)
            return path, None, f"count mismatch {len(labels)}!={n_out}"
        os.replace(tmp, path)
        return path, stats, None
    except Exception as e:
        if os.path.exists(tmp):
            os.remove(tmp)
        return path, None, str(e)


def step_annotate(files, mode, threads, fp2cat_path, model_path, tau,
                  nsegs, overlay=True):
    total = Counter()
    errors = []
    with Pool(threads, initializer=_init_annotate,
              initargs=(mode, fp2cat_path, model_path, tau, nsegs,
                        overlay)) as pool:
        for i, (path, stats, err) in enumerate(
                pool.imap_unordered(_annotate_file, files, chunksize=2)):
            if err:
                errors.append((path, err))
            else:
                total.update(stats)
            if (i + 1) % 500 == 0:
                print(f"  annotate {i + 1}/{len(files)}", flush=True)
    n = sum(total.values())
    print(f"  annotate done: {n} matches, {len(errors)} file errors")
    for p, e in errors[:20]:
        print("  ERR", p, e)
    for cat, c in total.most_common():
        print(f"    {cat:12s} {c:12d} {c / max(1, n):6.1%}")
    return not errors


# ----------------------------------------------------------------------- main

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--matches-dir", required=True)
    ap.add_argument("--lang", required=True, choices=sorted(LANG_MODE))
    ap.add_argument("--state-dir", required=True)
    ap.add_argument("--threads", type=int, default=32)
    ap.add_argument("--min-count", type=int, default=25,
                    help="min corpus count for a fingerprint to be clustered")
    ap.add_argument("--n-label", type=int, default=20000,
                    help="number of top clusters the oracle labels")
    ap.add_argument("--model", default=None,
                    help="existing fastText model; with cached fp2cat.pkl "
                         "this skips straight to annotation")
    ap.add_argument("--secrets-env", default=None)
    ap.add_argument("--tau", type=float, default=0.7)
    ap.add_argument("--no-overlay", action="store_true",
                    help="skip the geometry overlay (embedding/parallel)")
    args = ap.parse_args()

    mode = LANG_MODE[args.lang]
    os.makedirs(args.state_dir, exist_ok=True)
    files = sorted(
        os.path.join(args.matches_dir, f)
        for f in os.listdir(args.matches_dir) if f.endswith(".ndjson.gz"))
    if not files:
        sys.exit(f"no ndjson.gz files in {args.matches_dir}")
    print(f"{len(files)} files, lang={args.lang} (mode={mode})")

    fp2cat_path = os.path.join(args.state_dir, "fp2cat.pkl")
    model_path = args.model or os.path.join(args.state_dir, "model.ftz")

    need_build = not (os.path.exists(fp2cat_path)
                      and os.path.exists(model_path))
    if need_build:
        counts_path = os.path.join(args.state_dir, "counts.pkl")
        agg_path = os.path.join(args.state_dir, "agg.pkl")
        if not os.path.exists(counts_path):
            print("step 1/5: fingerprint counting")
            step_count(files, mode, args.threads, counts_path)
        if not os.path.exists(agg_path):
            print("step 2/5: head collection")
            step_collect(files, mode, args.threads, counts_path,
                         args.min_count, agg_path)
        with open(agg_path, "rb") as f:
            agg = pickle.load(f)
        cluster_rows = leader_cluster(agg, mode)
        print(f"  {len(cluster_rows)} clusters")
        labels_path = os.path.join(args.state_dir, "oracle_labels.json")
        if os.path.exists(labels_path):
            labels = {int(k): v for k, v in json.load(open(labels_path)).items()}
        else:
            print("step 3/5: oracle labeling")
            key = get_api_key(args.secrets_env)
            labels = step_oracle(agg, cluster_rows, args.lang, args.n_label,
                                 key, labels_path)
        if not os.path.exists(fp2cat_path):
            fp2cat = {}
            for idx, members in enumerate(cluster_rows):
                cat = labels.get(idx)
                if cat:
                    for fp in members:
                        fp2cat[fp] = cat
            with open(fp2cat_path, "wb") as f:
                pickle.dump(fp2cat, f)
            print(f"  {len(fp2cat)} fingerprints mapped")
        if not os.path.exists(model_path):
            print("step 4/5: fastText training")
            step_train(agg, cluster_rows, labels, mode, args.state_dir,
                       model_path)

    counts_path = os.path.join(args.state_dir, "counts.pkl")
    nsegs = {}
    overlay = not args.no_overlay
    if overlay:
        if os.path.exists(counts_path):
            with open(counts_path, "rb") as f:
                nsegs = pickle.load(f).get("nsegs", {})
        if not nsegs:
            print("  no per-text segment extents cached -> running count "
                  "pass to build them")
            step_count(files, mode, args.threads, counts_path)
            with open(counts_path, "rb") as f:
                nsegs = pickle.load(f)["nsegs"]

    print("step 5+6: annotation (in-place rewrite"
          + (", geometry overlay on)" if overlay else ", overlay OFF)"))
    ok = step_annotate(files, mode, args.threads, fp2cat_path, model_path,
                       args.tau, nsegs, overlay)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
