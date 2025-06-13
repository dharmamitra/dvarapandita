"""
Provides functionality for local sequence alignment with timeout handling and language-specific configurations.
"""

from Bio import Align
import re
from multiprocessing import Process, Queue
import time
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
    
    def __init__(self, stem_file: str):
        self.replaces_dictionary = self._load_stem_dictionary(stem_file)

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

    def stem_token(self, token: str) -> str:
        """Apply stemming to a single token."""
        if token in self.replaces_dictionary:
            token = self.replaces_dictionary[token]
        token = re.sub(r"([a-z])\'.*", r"\1", token)
        if "/" in token:
            token += str(random.randint(1, 100))
        return token

    def process_tokens(self, tokens: List[str], lang: str) -> Tuple[List[str], List[int]]:
        """Process tokens and track their positions."""
        processed_tokens = []
        token_positions = []
        current_pos = 0
        
        for token in tokens:
            if not any(char in token for char in ['/', '@', *PUNC]) and not re.search('[0-9]', token):
                token_positions.append(current_pos)
                processed_tokens.append(token)
            current_pos += len(token) + (1 if lang == "tib" else 0)
            
        return processed_tokens, token_positions

# Initialize global token processor
token_processor = TokenProcessor(TIBETAN_STEMFILE)

def get_aligned_offsets(stringa: str, stringb: str, lang: str, 
                       aligner: Align.PairwiseAligner, 
                       timeout: int = 30) -> AlignmentResult:
    """
    Get aligned offsets between two strings with timeout handling.
    Returns (start1, end1, start2, end2, score) or (0,0,0,0,0) if alignment fails.
    """
    if len(stringa) <= 3 or len(stringb) <= 3:
        return 0, 0, 0, 0, 0

    # Process tokens
    stringa_tokens = stringa.split() if lang == "tib" else list(stringa)
    stringb_tokens = stringb.split() if lang == "tib" else list(stringb)
    
    stringa_processed, stringa_positions = token_processor.process_tokens(stringa_tokens, lang)
    stringb_processed, stringb_positions = token_processor.process_tokens(stringb_tokens, lang)
    
    # Apply stemming
    stringa_stemmed = [token_processor.stem_token(token) for token in stringa_processed]
    stringb_stemmed = [token_processor.stem_token(token) for token in stringb_processed]
    
    # Configure aligner alphabet
    aligner.alphabet = list(set(stringa_stemmed + stringb_stemmed))

    if len(stringa_stemmed) < 6 or len(stringb_stemmed) < 6:        
        return 0, 0, 0, 0, 0
    
    try:
        # Perform alignment directly
        alignments = aligner.align(stringa_stemmed, stringb_stemmed)
        if not alignments:
            return 0, 0, 0, 0, 0
            
        result = alignments[0]
        
        # Calculate final positions
        start1 = stringa_positions[result.aligned[0][0][0]]
        end1 = stringa_positions[result.aligned[0][-1][1]] if result.aligned[0][-1][1] < len(stringa_positions) else len(stringa)
        start2 = stringb_positions[result.aligned[1][0][0]]
        end2 = stringb_positions[result.aligned[1][-1][1]] if result.aligned[1][-1][1] < len(stringb_positions) else len(stringb)
        
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
