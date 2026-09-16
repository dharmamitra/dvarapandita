from pathlib import Path
import glob
import os 
import numpy as np
import re
import faiss
import pandas as pd
from utils.constants import *
from utils.general import test_if_should_load
from utils.wordlist_lookup import load_wordlist_access
from merge_results import process_matches, remove_lock_files
import multiprocessing
import multiprocessing.pool
import gc

# Global variables for shared index and wordlist (loaded once in parent, shared via fork)
_G_INDEX = None
_G_WORDLIST_ACCESS = None
_G_WORDLIST_LEN = None
_G_LANG = None
_G_BUCKET_PATH = None
_G_ALIGNMENT_METHOD = None
_G_SRC_PATTERN = None

def _init_worker(bucket_path, lang, alignment_method, src_pattern):
    """Initialize worker process - prevent oversubscription of threads"""
    global _G_LANG, _G_BUCKET_PATH, _G_ALIGNMENT_METHOD, _G_SRC_PATTERN

    # Prevent oversubscription: keep faiss/blas single-threaded per worker
    os.environ["OMP_NUM_THREADS"] = "1"
    os.environ["MKL_NUM_THREADS"] = "1"
    os.environ["OPENBLAS_NUM_THREADS"] = "1"
    os.environ["NUMEXPR_NUM_THREADS"] = "1"
    try:
        faiss.omp_set_num_threads(1)
    except:
        pass

    # These should already be set from parent via fork, but ensure they're accessible
    _G_LANG = lang
    _G_BUCKET_PATH = bucket_path
    _G_ALIGNMENT_METHOD = alignment_method
    _G_SRC_PATTERN = src_pattern


def _calc_results_file_worker(query_file_path):
    """Standalone worker function that accesses global variables"""
    basename = Path(query_file_path).stem
    
    # File reading
    try:
        query_data = pd.read_pickle(query_file_path)
        if isinstance(query_data, dict):
            query_df = pd.DataFrame(query_data)
        elif isinstance(query_data, pd.DataFrame):
            query_df = query_data
        else:
            return
    except Exception:
        return
    
    # Prepare query vectors
    query_vectors = None
    if 'vector' in query_df.columns:
        query_vectors = np.array(query_df['vector'].tolist(), dtype="float32")
    elif 'sumvectors' in query_df.columns:
        query_vectors = np.array(query_df['sumvectors'].tolist(), dtype="float32")
    else:
        return
    
    if len(query_vectors) == 0:
        return
    
    faiss.normalize_L2(query_vectors)
    
    # FAISS search using shared index
    try:
        query_results = _G_INDEX.search(query_vectors, QUERY_DEPTH)
    except Exception:
        return
    
    # Extract results
    results = _extract_results_worker(query_df, query_results)
    if not results or not any(results.values()):
        return
        
    result_df = pd.DataFrame(results)
    process_matches(query_df, result_df, _G_BUCKET_PATH + basename, _G_LANG, alignment_method=_G_ALIGNMENT_METHOD)

def _extract_results_worker(query_df, query_results):
    """Extract results using global wordlist data"""
    results = {
        "query_position": [],
        "query_segmentnr": [],
        "query_stems": [],
        "query_sentence": [],
        "match_segment": [],
        "match_sentence": [],
        "match_stems": [],
        "match_position": [],
        "match_score": []
    }

    lang = _G_LANG
    threshold = THRESHOLD[lang]
    bigger_is_better = BIGGER_IS_BETTER[lang]
    epsilon = 1e-6
    window = WINDOWSIZE[lang]
    wl = _G_WORDLIST_ACCESS

    # Plain Python lists: per-hit pandas Series slicing was the dominant cost here.
    total_query_stems = query_df['analyzed'].tolist()
    total_query_segmentnrs = query_df['segmentnr'].tolist()
    total_query_sentences = query_df['original'].tolist()
    n_query = len(total_query_stems)

    all_scores = np.asarray(query_results[0])
    all_positions = np.asarray(query_results[1])
    if bigger_is_better:
        keep = all_scores > (threshold - epsilon)
    else:
        keep = all_scores < (threshold + epsilon)
    keep &= all_positions >= 0  # faiss returns -1 when not enough results are found

    for query_position in np.flatnonzero(keep.any(axis=1)).tolist():
        row_keep = keep[query_position]
        positions = all_positions[query_position][row_keep].tolist()
        scores = all_scores[query_position][row_keep].tolist()

        # Query-side window data is identical for every hit of this position.
        qpos = min(query_position, n_query)
        end_pos = min(qpos + window, n_query)
        if lang == "eng":
            qstems = total_query_stems[qpos]
            qsegmentnrs = [total_query_segmentnrs[qpos]]
        else:
            qstems = " ".join(str(item) for item in total_query_stems[qpos:end_pos])
            qsegmentnrs = list(dict.fromkeys(total_query_segmentnrs[qpos:end_pos]))
        qsentence = " ".join(dict.fromkeys(total_query_sentences[qpos:end_pos]))

        for position, score in zip(positions, scores):
            try:
                segment, sentence, stems = wl.hit_data(position, lang)
            except Exception:
                continue
            results["query_position"].append(query_position)
            results["query_segmentnr"].append(qsegmentnrs)
            results["query_stems"].append(qstems)
            results["query_sentence"].append(qsentence)
            results["match_segment"].append(segment)
            results["match_sentence"].append(sentence)
            results["match_stems"].append(stems)
            results["match_position"].append(position)
            results["match_score"].append(score)

    return results

class CalculateResults:
    def __init__(
        self,
        bucket_path,
        lang,
        index_method="cpu",
        cindex=None,
        alignment_method="local",
        src_pattern=None,
        num_processes=16,
    ):
        global _G_INDEX, _G_WORDLIST_ACCESS, _G_WORDLIST_LEN
        global _G_LANG, _G_BUCKET_PATH, _G_ALIGNMENT_METHOD, _G_SRC_PATTERN

        self.main_path = re.sub("folder.*", "", bucket_path)
        self.lang = lang
        self.bucket_path = bucket_path
        self.alignment_method = alignment_method
        self.index_method = index_method
        self.src_pattern = src_pattern
        self.num_processes = num_processes

        if index_method == "cpu":
            _G_INDEX = faiss.read_index(bucket_path + "vectors.idx")
        else:
            _G_INDEX = cindex

        _G_WORDLIST_ACCESS = load_wordlist_access(bucket_path)
        _G_WORDLIST_LEN = _G_WORDLIST_ACCESS.wordlist_len
        self.wordlist_access = _G_WORDLIST_ACCESS
        self.wordlist_len = _G_WORDLIST_LEN

        _G_LANG = lang
        _G_BUCKET_PATH = bucket_path
        _G_ALIGNMENT_METHOD = alignment_method
        _G_SRC_PATTERN = src_pattern

        self.blacklist = self._load_blacklist(lang)
        if self.blacklist:
            print(f"Loaded blacklist for lang={lang}: {len(self.blacklist)} entries skipped")

    @staticmethod
    def _load_blacklist(lang):
        path = os.path.join("ref", f"blacklist_{lang}.txt")
        if not os.path.isfile(path):
            return set()
        entries = set()
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.split("#", 1)[0].strip()
                if not line:
                    continue
                entries.add(line)
                # also store stem so callers can match either way
                if line.endswith(".p"):
                    entries.add(line[:-2])
        return entries

    def create_querypaths(self, query_path):
        filelist =  glob.glob(query_path + '/**/*.p', recursive=True)
        filepaths = []
        skipped_blacklist = 0
        for current_file in filelist:
            filepath = current_file
            if test_if_should_load(filepath):
                if not "wordlist" in filepath:
                    # Filter by pattern if specified
                    if self.src_pattern is None or self.src_pattern in filepath:
                        basename = os.path.basename(filepath)
                        if basename in self.blacklist or Path(basename).stem in self.blacklist:
                            skipped_blacklist += 1
                            continue
                        filepaths.append(filepath)
        if skipped_blacklist:
            print(f"  blacklist skipped {skipped_blacklist} file(s) under {query_path}")
        return filepaths

    def _run_query_file_list(self, query_files):
        """Sort largest-first (LPT), then GPU sequential or CPU pool work queue."""
        if not query_files:
            return

        def _size_or_zero(p):
            try:
                return os.path.getsize(p)
            except OSError:
                return 0

        query_files = sorted(query_files, key=_size_or_zero, reverse=True)

        if self.index_method == "gpu":
            # in-process index (built on the GPU); same per-file worker as the CPU pool
            for query_file in query_files:
                _calc_results_file_worker(query_file)
            remove_lock_files(os.path.join(self.main_path, "matches"))
            return

        # The index and wordlist are shared with the workers through fork. Freezing
        # the parent's heap keeps the workers' garbage collector from traversing
        # (and thereby copy-on-write duplicating) those millions of long-lived
        # wordlist objects on every full collection.
        gc.collect()
        gc.freeze()
        ctx = multiprocessing.get_context("fork")
        with ctx.Pool(
            processes=self.num_processes,
            initializer=_init_worker,
            initargs=(self.bucket_path, self.lang, self.alignment_method, self.src_pattern),
        ) as pool:
            # chunksize=1 + imap_unordered: global queue; workers pick next task when idle.
            for _ in pool.imap_unordered(
                _calc_results_file_worker, query_files, chunksize=1
            ):
                pass
        remove_lock_files(os.path.join(self.main_path, "matches"))

    def run(self):
        all_query_files = []
        for directory in os.listdir(self.main_path):
            dir_path = os.path.join(self.main_path, directory)
            if os.path.isdir(dir_path):
                all_query_files.extend(self.create_querypaths(dir_path))
        self._run_query_file_list(all_query_files)
                                                    