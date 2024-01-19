from scipy import spatial
from natsort import natsorted
from utils.local_alignment import get_aligned_offsets_efficient, create_aligner
from utils.constants import *
from tqdm import tqdm
import re
from Levenshtein import distance
from utils.test_quote import test_quote
from utils.shorten_segments import shorten_segments


def normalized_levenshtein(string1,string2):
    return 1 - distance(string1,string2)/len(string2)

def get_pair_clusters(pair_list,windowsize):
    try:
        index = spatial.cKDTree(pair_list,1000)
    except:
        return []
    
    known_results = {}
    clusters = []
    c = 0
    for query_pair in pair_list:
        known_results[tuple(pair_list[0])] = 1
        if not tuple(query_pair) in known_results:
            query_pairs = [query_pair]
            current_cluster = query_pairs
            while 1:
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
    if lang == "tib":
        string = re.sub("[^a-zA-Z ]", "", string).strip()
        return len(string.split())
    else:
        return len(string)

def create_matches_with_text(matches,
                             pair_clusters,
                             inquiry_segments,
                             target_segments,
                             lang, 
                             alignment_method="local"):
    results = []
    c = 0
    efficient_threshold = 100 if lang == "chn" else 1000
    aligner = create_aligner(lang)
    for match, positions in zip(matches, pair_clusters):
        inquiry_text = []
        target_text = []
        current_inquiry_segments, current_target_segments = match
        for inquiry_segment in current_inquiry_segments:
            inquiry_text.append(inquiry_segments[inquiry_segment])
        for target_segment in current_target_segments:
            target_text.append(target_segments[target_segment])
        #if test_quote(inquiry_text, target_text, positions, lang):
        if 1==1:
            inquiry_text_merged = ""
            target_text_merged = ""

            inquiry_positions, target_positions = zip(*positions)
            inquiry_pos_beg = min(inquiry_positions)
            inquiry_pos_end = max(inquiry_positions)
            target_pos_beg = min(target_positions)
            target_pos_end = max(target_positions)

            if lang == "tib":
                inquiry_text_merged = ' '.join(inquiry_text)
                target_text_merged = ' '.join(target_text)
            else:
                inquiry_text_merged = ''.join(inquiry_text)
                target_text_merged = ''.join(target_text)
            # print("INQUIRY TEXT MERGED: ", inquiry_text_merged)
            # print("TARGET TEXT MERGED: ", target_text_merged)
            if len(inquiry_text_merged) > 5 and len(target_text_merged) > 5:
                inquiry_text_beg = 0 
                inquiry_text_end = len(inquiry_text_merged)
                target_text_beg = 0
                target_text_end = len(target_text_merged)
                score = 100
                if alignment_method == "local":
                    inquiry_text_beg, inquiry_text_end, target_text_beg, target_text_end, score = \
                        get_aligned_offsets_efficient(inquiry_text_merged,
                                                        target_text_merged,
                                                        efficient_threshold,
                                                        lang, 
                                                        aligner)


                target_offset_beg_final, \
                target_offset_end_final, \
                inquiry_offset_beg_final, \
                inquiry_offset_end_final, \
                target_text, \
                current_target_segments, \
                inquiry_text, \
                current_inquiry_segments = \
                    shorten_segments(
                        target_text_beg,
                        target_text_end,
                        inquiry_text_beg,
                        inquiry_text_end,
                        target_text,
                        current_target_segments,
                        inquiry_text,
                        current_inquiry_segments,
                        lang)
                inquiry_text_merged = inquiry_text_merged[inquiry_text_beg:inquiry_text_end]
                target_text_merged = target_text_merged[target_text_beg:target_text_end]
                inquiry_text_merged = inquiry_text_merged.strip()
                target_text_merged = target_text_merged.strip()
                inquiry_length = get_length(inquiry_text_merged, lang)
                target_length = get_length(target_text_merged, lang)
                if len(inquiry_text_merged) > 0 and len(target_text_merged) > 0:
                    if inquiry_length >= ABSOLUTE_MIN_LENGTH[lang] and target_length >= ABSOLUTE_MIN_LENGTH[lang]:
                        current_id = current_inquiry_segments[0].split(":")[0] + ":" + str(c)
                        score = normalized_levenshtein(inquiry_text_merged,target_text_merged)
                        results.append({
                            "id": current_id,
                            "score": score,
                            "par_length": target_length,
                            "root_length": inquiry_length,
                            "inquiry_pos_beg": inquiry_pos_beg,
                            "inquiry_pos_end": inquiry_pos_end,
                            "target_pos_beg": target_pos_beg,
                            "target_pos_end": target_pos_end,
                            "root_segnr": current_inquiry_segments,
                            "par_segnr": current_target_segments,
                            "root_segtext": inquiry_text,
                            "par_segtext": target_text,
                            "root_string": inquiry_text_merged,
                            "par_string": target_text_merged,
                            "root_offset_beg": inquiry_offset_beg_final,
                            "root_offset_end": inquiry_offset_end_final,
                            "par_offset_beg": target_offset_beg_final,
                            "par_offset_end": target_offset_end_final,
                            "src_lang": lang,
                            "tgt_lang": lang})
    print("Number of matches: ", len(results))
    return results
