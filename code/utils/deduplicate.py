def deduplicate_matches(matches):
    """
    Deduplicate matches based on root_segnr and par_segnr values.
    
    Args:
        matches: List of match dictionaries
        
    Returns:
        List of deduplicated matches, keeping the one with the highest score
        when duplicates are found
    """
    # Create a dictionary to store unique combinations
    unique_matches = {}
    
    for match in matches:
        # Convert lists to tuples so they can be hashed
        key = (
            tuple(sorted(match['root_segnr'])), 
            tuple(sorted(match['par_segnr']))
        )
        
        # Keep the match with the highest score
        if key not in unique_matches or match['score'] > unique_matches[key]['score']:
            unique_matches[key] = match
    
    return list(unique_matches.values())