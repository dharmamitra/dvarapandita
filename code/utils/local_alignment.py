"""
Provides functionality for local sequence alignment with timeout handling and language-specific configurations.
"""

from Bio import Align
import re
import numpy as np
import random
from typing import Tuple, Dict, List, Optional
from utils.constants import PUNC, TIBETAN_STEMFILE

# Type aliases
AlignmentResult = Tuple[int, int, int, int, float]  # (start1, end1, start2, end2, score)

class AlignerConfig:
    """Configuration parameters for different language aligners."""
    CONFIGS = {
        "tib": {
            "match_score": 5,
            "mismatch_score": -4,
            "open_gap_score": -5,
            "extend_gap_score": -5
        },
        "chn": {
            "match_score": 1,
            "mismatch_score": -1,
            "open_gap_score": -0.8,
            "extend_gap_score": -0.3
        },
        "default": {
            "match_score": 1,
            "mismatch_score": -2,
            "open_gap_score": -1,
            "extend_gap_score": -0.5
        }
    }

def create_aligner(lang: str) -> Align.PairwiseAligner:
    """Create and configure a PairwiseAligner for the specified language."""
    aligner = Align.PairwiseAligner()
    aligner.mode = 'local'
    
    config = AlignerConfig.CONFIGS.get(lang, AlignerConfig.CONFIGS['default'])
    for attr, value in config.items():
        setattr(aligner, attr, value)
    
    return aligner

class TokenProcessor:
    """Handles token processing and stemming operations."""
    
    @staticmethod
    def _load_stem_dictionary(path: str) -> Dict[str, str]:
        """Load stemming dictionary from file."""
        replaces_dictionary = {}
        try:
            with open(path, "r") as f:
                for line in f:
                    parts = line.split('\t')
                    if len(parts) >= 3:
                        replaces_dictionary[parts[0]] = parts[2].strip()
        except (IOError, IndexError) as e:
            print(f"Error reading dictionary file: {e}")
        return replaces_dictionary

    # Any token containing one of these characters is dropped before alignment
    # (same set as the former per-character any() scan plus the [0-9] check).
    _DROP_TOKEN_RE = re.compile("[/@0-9" + re.escape(PUNC) + "]")
    _APOSTROPHE_RE = re.compile(r"([a-z])'.*")

    def __init__(self, stem_file: str):
        self.replaces_dictionary = self._load_stem_dictionary(stem_file)
        self._stem_cache: Dict[str, str] = {}
        # raw token -> integer code of its stem, or -1 if the token is dropped
        # before alignment. Codes are global, so equal codes <=> equal stems.
        self._token_code: Dict[str, int] = {}
        self._stem_code: Dict[str, int] = {}
        # merged text -> (int32 code array, char positions); bounded, see encode()
        self._string_cache: Dict[Tuple[str, str], Tuple[np.ndarray, List[int]]] = {}
        self._string_cache_max = 20000
        self._unique_counter = 0

    def stem_token(self, token: str) -> str:
        """Apply stemming to a single token."""
        cached = self._stem_cache.get(token)
        if cached is not None:
            return cached
        stemmed = self.replaces_dictionary.get(token, token)
        stemmed = self._APOSTROPHE_RE.sub(r"\1", stemmed)
        if "/" in stemmed:
            # deliberately unique so slash tokens never align with each other; not cached
            return stemmed + str(random.randint(1, 100))
        self._stem_cache[token] = stemmed
        return stemmed

    def _code_for(self, token: str) -> int:
        code = self._token_code.get(token)
        if code is not None:
            return code
        if self._DROP_TOKEN_RE.search(token) is not None:
            code = -1
        else:
            stemmed = self.stem_token(token)
            if "/" in stemmed:
                # slash stems are made unique on purpose; never cache them
                self._unique_counter += 1
                return 1_000_000_000 + self._unique_counter
            code = self._stem_code.get(stemmed)
            if code is None:
                code = len(self._stem_code)
                self._stem_code[stemmed] = code
        self._token_code[token] = code
        return code

    def encode(self, text: str, lang: str) -> Tuple[np.ndarray, List[int]]:
        """
        Tokenize, filter, stem and integer-code `text` in one pass:
        returns (codes as int32 array, character offset of each kept token).
        Equivalent to process_tokens followed by stem_token on each kept token,
        with stems replaced by globally consistent integer codes.
        """
        key = (text, lang)
        cached = self._string_cache.get(key)
        if cached is not None:
            return cached
        tokens = text.split() if lang == "tib" else list(text)
        step = 1 if lang == "tib" else 0
        code_for = self._code_for
        codes: List[int] = []
        positions: List[int] = []
        current_pos = 0
        for token in tokens:
            code = code_for(token)
            if code >= 0:
                codes.append(code)
                positions.append(current_pos)
            current_pos += len(token) + step
        result = (np.asarray(codes, dtype=np.int32), positions)
        if len(self._string_cache) >= self._string_cache_max:
            self._string_cache.clear()
        self._string_cache[key] = result
        return result

    def process_tokens(self, tokens: List[str], lang: str) -> Tuple[List[str], List[int]]:
        """Process tokens and track their positions."""
        processed_tokens = []
        token_positions = []
        current_pos = 0
        drop = self._DROP_TOKEN_RE.search
        step = 1 if lang == "tib" else 0

        for token in tokens:
            if drop(token) is None:
                token_positions.append(current_pos)
                processed_tokens.append(token)
            current_pos += len(token) + step

        return processed_tokens, token_positions

# Initialize global token processor
token_processor = TokenProcessor(TIBETAN_STEMFILE)

def _aligned_bounds(coordinates) -> Optional[Tuple[int, int, int, int]]:
    """
    (start_a, end_a, start_b, end_b) of the aligned (non-gap) part of a pairwise
    alignment path, i.e. the same values as result.aligned[0][0][0],
    result.aligned[0][-1][1], result.aligned[1][0][0], result.aligned[1][-1][1],
    computed once from the path coordinates instead of via the .aligned property.
    Paths are short, so plain Python beats numpy here.
    """
    row_a, row_b = coordinates.tolist()
    n = len(row_a) - 1
    first = -1
    for i in range(n):
        if row_a[i + 1] != row_a[i] and row_b[i + 1] != row_b[i]:
            first = i
            break
    if first < 0:
        return None
    last = n
    while row_a[last] == row_a[last - 1] or row_b[last] == row_b[last - 1]:
        last -= 1
    return row_a[first], row_a[last], row_b[first], row_b[last]


def get_aligned_offsets(stringa: str, stringb: str, lang: str, 
                       aligner: Align.PairwiseAligner, 
                       timeout: int = 30) -> AlignmentResult:
    """
    Get aligned offsets between two strings with timeout handling.
    Returns (start1, end1, start2, end2, score) or (0,0,0,0,0) if alignment fails.
    """
    if len(stringa) <= 3 or len(stringb) <= 3:
        return 0, 0, 0, 0, 0

    # Tokenize, filter, stem and integer-code both sides (cached per string).
    # Handing PairwiseAligner int32 arrays skips its pure-Python alphabet
    # construction; equality of codes is exactly equality of stemmed tokens.
    seq_a, stringa_positions = token_processor.encode(stringa, lang)
    seq_b, stringb_positions = token_processor.encode(stringb, lang)

    if len(seq_a) < 6 or len(seq_b) < 6:
        return 0, 0, 0, 0, 0

    try:
        # Perform alignment directly
        alignments = aligner.align(seq_a, seq_b)
        if not alignments:
            return 0, 0, 0, 0, 0

        result = alignments[0]
        bounds = _aligned_bounds(result.coordinates)
        if bounds is None:
            return 0, 0, 0, 0, 0
        a_beg, a_end, b_beg, b_end = bounds

        # Calculate final positions
        start1 = stringa_positions[a_beg]
        end1 = stringa_positions[a_end] if a_end < len(stringa_positions) else len(stringa)
        start2 = stringb_positions[b_beg]
        end2 = stringb_positions[b_end] if b_end < len(stringb_positions) else len(stringb)

        return start1, end1, start2, end2, result.score
        
    except Exception as e:
        print("Error during alignment:", str(e))
        return 0, 0, 0, 0, 0

def get_aligned_offsets_efficient(inquiry_text: str, target_text: str, 
                                threshold: int, lang: str, 
                                aligner: Align.PairwiseAligner) -> AlignmentResult:
    """
    Efficient version of get_aligned_offsets for long texts.
    Only processes the first and last 'threshold' characters.
    """
    if len(inquiry_text) < threshold or len(target_text) < threshold:
        return get_aligned_offsets(inquiry_text, target_text, lang, aligner)
    
    # Get alignments for beginning and end portions
    start_alignment = get_aligned_offsets(inquiry_text[:threshold],
                                        target_text[:threshold], 
                                        lang, aligner)
    
    end_alignment = get_aligned_offsets(inquiry_text[-threshold:],
                                      target_text[-threshold:], 
                                      lang, aligner)
    
    # Adjust end positions
    inquiry_end = end_alignment[1] + len(inquiry_text) - threshold
    target_end = end_alignment[3] + len(target_text) - threshold
    avg_score = (start_alignment[4] + end_alignment[4]) / 2
    
    return start_alignment[0], inquiry_end, start_alignment[2], target_end, avg_score
