from scipy import spatial
from natsort import natsorted
from utils.local_alignment import get_aligned_offsets_efficient, create_aligner
from utils.constants import *
from tqdm import tqdm
import re
from Levenshtein import distance
from utils.test_quote import test_quote
from utils.shorten_segments import shorten_segments
import numpy as np
from collections import defaultdict


def normalized_levenshtein(string1, string2):
    if not string1 or not string2:
        return 0
    max_len = max(len(string1), len(string2))
    return 1 - distance(string1, string2) / max_len

def get_pair_clusters(pair_list, windowsize):
    """
    Find continuous chains of pairs where consecutive pairs are at most windowsize apart.
    Optimized for large datasets with thousands of items.
    
    Args:
        pair_list: List of tuples containing (x,y) coordinates
        windowsize: Maximum allowed distance between consecutive pairs
    """
    if pair_list is None:
        return []
    if not isinstance(pair_list, (list, tuple)):
        return []
    
    # Convert to numpy array for faster operations
    pairs = np.array(pair_list)
    
    # Create a spatial hash grid for quick neighbor lookups
    # Round positions to grid cells of size windowsize
    grid_size = windowsize
    grid = defaultdict(list)
    
    # Map pairs to grid cells
    for i, (x, y) in enumerate(pairs):
        cell_x = x // grid_size
        cell_y = y // grid_size
        grid[(cell_x, cell_y)].append(i)
    
    # Find clusters using grid
    visited = set()
    clusters = []
    
    def get_neighbors(idx):
        x, y = pairs[idx]
        cell_x, cell_y = x // grid_size, y // grid_size
        
        # Check neighboring cells
        neighbor_indices = []
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                cell = (cell_x + dx, cell_y + dy)
                if cell in grid:
                    for neighbor_idx in grid[cell]:
                        if neighbor_idx != idx and neighbor_idx not in visited:
                            nx, ny = pairs[neighbor_idx]
                            if (abs(nx - x) <= windowsize and 
                                abs(ny - y) <= windowsize):
                                neighbor_indices.append(neighbor_idx)
        return neighbor_indices
    
    # Use iterative approach instead of recursive for better performance
    for start_idx in range(len(pairs)):
        if start_idx in visited:
            continue
            
        current_cluster = []
        to_visit = [start_idx]
        
        while to_visit:
            idx = to_visit.pop()
            if idx not in visited:
                visited.add(idx)
                current_cluster.append(tuple(pairs[idx]))
                to_visit.extend(get_neighbors(idx))
        
        if current_cluster:
            # Sort cluster by position for consistency
            current_cluster.sort()
            clusters.append(current_cluster)
    
    return clusters


def construct_matches_from_pair_clusters(pair_clusters,
                                         inquiry_segment_position,
                                         match_segment_position):
    results = []
    if len(list(inquiry_segment_position.keys())) > 2:    
        first_segmentnr = list(inquiry_segment_position.keys())[2]
        first_segmentnr = inquiry_segment_position[first_segmentnr][0]
        inquiry_filename = first_segmentnr.split(":")[0]
        inquiry_filename = re.sub("\$[0-9]+", "", inquiry_filename)
        inquiry_filename = inquiry_filename.replace(".txt", "")

        for cluster in pair_clusters:
            inquiry_segments = []
            match_segments = []
            cluster = list(set(cluster))
            inquiry_positions, match_positions = zip(*cluster)
            if match_segment_position[match_positions[0]][0:len(inquiry_filename)] != inquiry_filename:
                inquiry_positions = list(inquiry_positions)
                match_positions = list(match_positions)
                inquiry_positions.sort()
                match_positions.sort()
                for inquiry_position in inquiry_positions:
                    inquiry_segment = inquiry_segment_position[inquiry_position]
                    if isinstance(inquiry_segment[0], str):
                        inquiry_segments.extend(inquiry_segment)

                for match_position in match_positions:
                    match_segment = match_segment_position[match_position]
                    if isinstance(match_segment, str):
                        match_segments.append(match_segment)
            inquiry_segments = list(dict.fromkeys(inquiry_segments))
            match_segments = list(dict.fromkeys(match_segments))
            results.append([inquiry_segments, match_segments])
    return results


def get_length(string, lang):
    if not isinstance(string, str):
        return 0
    if lang == "tib":
        try:
            string = re.sub("[^a-zA-Z ]", "", string).strip()
            return len(string.split())
        except Exception as e:
            print(f"Error processing Tibetan string: {e}")
            return 0
    return len(string)

def create_matches_with_text(matches, pair_clusters, inquiry_segments, target_segments, lang, alignment_method="local"):
    if matches is None or pair_clusters is None:
        print("Warning: matches or pair_clusters is None")
        return []
    
    EFFICIENT_THRESHOLDS = {
        "chn": 100,
        "tib": 1000,
        "eng": 1000,
    }
    efficient_threshold = EFFICIENT_THRESHOLDS.get(lang, 1000)
    aligner = create_aligner(lang)
    results = []
    
    for match_idx, (match, positions) in enumerate(zip(matches, pair_clusters)):
        result = process_single_match(
            match, positions, inquiry_segments, target_segments,
            lang, match_idx, efficient_threshold, aligner, alignment_method
        )
        if result:
            results.extend(result)
            
    print("Number of matches: ", len(results))
    return results

def process_single_match(match, positions, inquiry_segments, target_segments, 
                        lang, match_idx, efficient_threshold, aligner, alignment_method):
    """Process a single match and return the result dictionary if valid."""
    # Extract texts
    inquiry_text, target_text = extract_segment_texts(match, inquiry_segments, target_segments)
    
    # Get position boundaries
    pos_bounds = get_position_boundaries(positions)
    
    # Merge texts
    inquiry_merged, target_merged = merge_texts(inquiry_text, target_text, lang)
    
    if len(inquiry_merged) <= 5 or len(target_merged) <= 5:
        return None
        
    # Get aligned offsets
    aligned_texts = get_aligned_text_offsets(
        inquiry_merged, target_merged, 
        efficient_threshold, lang, aligner, alignment_method
    )
    if not aligned_texts:
        return None
        
    # Create and return the result dictionary
    return create_result_dict(
        aligned_texts, pos_bounds, match, inquiry_text, target_text,
        lang, match_idx
    )

def extract_segment_texts(match, inquiry_segments, target_segments):
    """Extract inquiry and target texts from segments."""
    current_inquiry_segments, current_target_segments = match
    inquiry_text = [inquiry_segments[seg] for seg in current_inquiry_segments]
    target_text = [target_segments[seg] for seg in current_target_segments]
    return inquiry_text, target_text

def get_position_boundaries(positions):
    """Get the beginning and end positions for inquiry and target."""
    inquiry_positions, target_positions = zip(*positions)
    return {
        "inquiry_pos_beg": min(inquiry_positions),
        "inquiry_pos_end": max(inquiry_positions),
        "target_pos_beg": min(target_positions),
        "target_pos_end": max(target_positions)
    }

def merge_texts(inquiry_text, target_text, lang):
    """Merge texts based on language."""
    separator = ' ' if lang == "tib" else ''
    inquiry_merged = separator.join(inquiry_text)
    target_merged = separator.join(target_text)
    return inquiry_merged, target_merged

def get_aligned_text_offsets(inquiry_merged, target_merged, threshold, lang, aligner, alignment_method):
    """Get aligned text offsets and process them."""
    if alignment_method != "local":
        return {
            "inquiry_text_beg": 0,
            "inquiry_text_end": len(inquiry_merged),
            "target_text_beg": 0,
            "target_text_end": len(target_merged),
            "score": 100
        }
    
    result = get_aligned_offsets_efficient(
        inquiry_merged, target_merged, threshold, lang, aligner
    )
    return dict(zip(
        ["inquiry_text_beg", "inquiry_text_end", "target_text_beg", "target_text_end", "score"],
        result
    ))

def create_result_dict(aligned_texts, pos_bounds, match, inquiry_text, target_text, lang, match_idx):
    """Create the final result dictionary with both original and inverted matches."""
    current_inquiry_segments, current_target_segments = match
    
    # Process text with aligned offsets
    shortened = shorten_segments(
        aligned_texts["target_text_beg"], aligned_texts["target_text_end"],
        aligned_texts["inquiry_text_beg"], aligned_texts["inquiry_text_end"],
        target_text, current_target_segments,
        inquiry_text, current_inquiry_segments, lang
    )
    
    target_offset_beg, target_offset_end, inquiry_offset_beg, inquiry_offset_end, \
    target_text, current_target_segments, inquiry_text, current_inquiry_segments = shortened
    
    # Create final merged texts - join lists before slicing
    separator = ' ' if lang == "tib" else ''
    inquiry_merged = separator.join(inquiry_text)[aligned_texts["inquiry_text_beg"]:aligned_texts["inquiry_text_end"]].strip()
    target_merged = separator.join(target_text)[aligned_texts["target_text_beg"]:aligned_texts["target_text_end"]].strip()
    
    # Get lengths and check minimums
    inquiry_length = get_length(inquiry_merged, lang)
    target_length = get_length(target_merged, lang)
    
    if not (len(inquiry_merged) and len(target_merged) and 
            inquiry_length >= ABSOLUTE_MIN_LENGTH[lang] and 
            target_length >= ABSOLUTE_MIN_LENGTH[lang]):
        return None
    
    current_id = f"{current_inquiry_segments[0].split(':')[0]}:{match_idx}"
    target_id = f"{current_target_segments[0].split(':')[0]}:{match_idx}"
    score = normalized_levenshtein(inquiry_merged, target_merged)
    
    # Create original match
    original_match = {
        "id": current_id,
        "score": score,
        "par_length": target_length,
        "root_length": inquiry_length,
        "inquiry_pos_beg": pos_bounds["inquiry_pos_beg"],
        "inquiry_pos_end": pos_bounds["inquiry_pos_end"],
        "target_pos_beg": pos_bounds["target_pos_beg"],
        "target_pos_end": pos_bounds["target_pos_end"],
        "root_segnr": current_inquiry_segments,
        "par_segnr": current_target_segments,
        "root_segtext": inquiry_text,
        "par_segtext": target_text,
        "root_string": inquiry_merged,
        "par_string": target_merged,
        "root_offset_beg": inquiry_offset_beg,
        "root_offset_end": inquiry_offset_end,
        "par_offset_beg": target_offset_beg,
        "par_offset_end": target_offset_end,
        "src_lang": lang,
        "tgt_lang": lang
    }
    
    # Create inverted match
    inverted_match = {
        "id": target_id,
        "score": score,
        "par_length": inquiry_length,
        "root_length": target_length,
        "inquiry_pos_beg": pos_bounds["target_pos_beg"],
        "inquiry_pos_end": pos_bounds["target_pos_end"],
        "target_pos_beg": pos_bounds["inquiry_pos_beg"],
        "target_pos_end": pos_bounds["inquiry_pos_end"],
        "root_segnr": current_target_segments,
        "par_segnr": current_inquiry_segments,
        "root_segtext": target_text,
        "par_segtext": inquiry_text,
        "root_string": target_merged,
        "par_string": inquiry_merged,
        "root_offset_beg": target_offset_beg,
        "root_offset_end": target_offset_end,
        "par_offset_beg": inquiry_offset_beg,
        "par_offset_end": inquiry_offset_end,
        "src_lang": lang,
        "tgt_lang": lang
    }
    
    return [original_match, inverted_match]
