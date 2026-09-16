def add_co_occ_value(matches):    
    """
    For each match, determine how many other matches it is "contained" by.
    A match 'B' is contained by 'A' if:
    1. All root segments of B are contained within A's root segments.
       - If they differ in the sets of segments (B is a strict subset), B is considered contained if overlapping.
       - If they have the exact same set of root segments, then B is contained if A's root string length 
         is equal to or greater than B's root string length.

    Args:x
        matches (list of dict): Each dict should have keys:
            - 'root_segnr': A list of segment identifiers (e.g. [1, 2, 3])
            - 'root_string': The matched string
            - 'root_offset_beg': Start offset of the match
            - 'root_offset_end': End offset of the match

    Returns:
        The modified matches list with a new key 'co_occ' for each match.
    """

    # Precompute additional attributes for each match for efficiency
    for m in matches:
        m['segment_set'] = set(m['root_segnr'])
        m['text_len'] = len(m['root_string'])  

    # Sort matches:
    # First by descending number of segments, then by descending text length
    # This ensures that larger matches come first, so they can contain the smaller ones.
    matches.sort(key=lambda x: (-len(x['root_segnr']), -x['text_len']))

    # Build a segment index to quickly find candidate containing matches
    segment_index = {}
    for i, match in enumerate(matches):
        for seg in match['root_segnr']:
            if seg not in segment_index:
                segment_index[seg] = []
            segment_index[seg].append(i)

    def contains_match(match1, match2):
        """
        Check if match1 contains match2 according to the rules:
        - match2's segments must be a subset of match1's segments
        - If segments sets are equal, match1's text length must be >= match2's text length.
        """
        segs1 = match1['segment_set']
        segs2 = match2['segment_set']

        # Check subset condition
        if not segs2.issubset(segs1):
            return False

        # If sets are equal, compare length
        if segs1 == segs2:
            return match1['text_len'] >= match2['text_len']
        
        # If it's a strict subset, then match1 contains match2
        return True

    # Compute co_occ for each match
    # Since matches are sorted, we only look at indices < i
    for i, match in enumerate(matches):
        candidate_indices = set()
        for seg in match['root_segnr']:
            # Only consider matches that appear before this one in the sorted list
            candidate_indices.update(idx for idx in segment_index[seg] if idx < i)

        co_occ = 0
        for j in candidate_indices:
            if contains_match(matches[j], match):
                co_occ += 1
                if co_occ > 50:
                    break
        match['co_occ'] = co_occ

    # Clean up temporary fields if necessary
    for m in matches:
        del m['segment_set']
        del m['text_len']

    return matches
