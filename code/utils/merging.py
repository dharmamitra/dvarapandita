import scipy
from natsort import natsorted
from utils.local_alignment import get_aligned_offsets
from utils.constants import *
def get_pair_clusters(pair_list,windowsize):
    index = scipy.spatial.cKDTree(pair_list,1000)
    known_results = {}
    clusters = []
    c = 0
    for query_pair in pair_list:
        known_results[tuple(pair_list[0])] = 1
        if not tuple(query_pair) in known_results:
            query_pairs = [query_pair]
            current_cluster = query_pairs
            while 1==1:
                new_results = []
                query_results = index.query_ball_point(query_pairs, windowsize * 3)
                for query_result in query_results:
                    for result in query_result:
                        result_pair = pair_list[result]
                        if tuple(result_pair) not in known_results:
                            new_results.append(result_pair)
                            known_results[tuple(result_pair)] = 1
                            current_cluster.append(result_pair)
                if len(new_results) == 0:
                    break
                else:
                    query_pairs = new_results
            if(len(current_cluster) != 0):
                clusters.append(current_cluster)
        c +=1
    return clusters

def construct_matches_from_pair_clusters(pair_clusters,
                                         inquiry_segment_position,
                                         match_segment_position):
    results = []
    for cluster in pair_clusters:
        inquiry_segments = []
        match_segments = []
        for pair in cluster:
            inquiry_position, match_position = pair
            inquiry_segment = inquiry_segment_position[inquiry_position]
            match_segment = match_segment_position[match_position]
            inquiry_segments.extend(inquiry_segment)
            match_segments.append(match_segment)
        inquiry_segments = list(dict.fromkeys(inquiry_segments))
        match_segments = list(dict.fromkeys(match_segments))
        inquiry_segments = natsorted(inquiry_segments)
        match_segments = natsorted(match_segments)
        results.append([inquiry_segments, match_segments])
    return results

def create_matches_with_text(matches,
                     inquiry_segments,
                     target_segments,
                     lang):
    results = []
    for match in matches:
        inquiry_text = []
        target_text = []
        current_inquiry_segments, current_target_segments = match
        for inquiry_segment in current_inquiry_segments:
            inquiry_text.append(inquiry_segments[inquiry_segment])
        for target_segment in current_target_segments:
            target_text.append(target_segments[target_segment])


        inquiry_text_merged = ""
        target_text_merged = ""
        if lang == "tib":
            inquiry_text_merged = ' '.join(inquiry_text)
            target_text_merged = ' '.join(target_text)
        else:
            inquiry_text_merged = ''.join(inquiry_text)
            target_text_merged = ''.join(target_text)
        inquiry_text_beg, inquiry_text_end, target_text_beg, target_text_end, score = get_aligned_offsets(inquiry_text_merged, target_text_merged, lang)
        inquiry_text_merged = inquiry_text_merged[inquiry_text_beg:inquiry_text_end]
        target_text_merged = target_text_merged[target_text_beg:target_text_end]
        if len(inquiry_text_merged) > MIN_LENGTH['lang'] and len(target_text_merged) > MIN_LENGTH['lang']:
            results.append({
                "score": score,
                "root_segnr": current_inquiry_segments,
                "par_segnr": current_target_segments,
                "root_segtext": inquiry_text,
                "par_segtext": target_text,
                "root_string": inquiry_text_merged,
                "par_string": target_text_merged })
    return results


