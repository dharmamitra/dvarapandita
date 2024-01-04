import re
from utils.constants import WINDOWSIZE

def test_pattern(string):
    if "//" in string or re.search(r"g.{0,2}/",string):
        return True
    else:
        return False

def test_quote(inquiry_segments,target_segments, position_pairs, lang):
    new_inquiry_segments = []
    for segment in inquiry_segments:
        new_inquiry_segments.extend(segment.split("/"))
    new_target_segments = []
    for segment in target_segments:
        new_target_segments.extend(segment.split("/"))
    inquiry_segments = new_inquiry_segments
    target_segments = new_target_segments
    if lang != "tib":
        return True
    half_flag = False
    flag = False
    for segtext in inquiry_segments:
        segtext_cleaned = segtext.replace("/","").strip()
        clen = len(segtext_cleaned.split())
        if clen == 7 or clen == 9 or clen == 11:
                half_flag = True
    if half_flag:
        for segtext in target_segments:
            segtext_cleaned = segtext.replace("/","").strip()
            clen = len(segtext_cleaned.split())
            if clen == 7 or clen == 9 or clen == 11:
                flag = True
    if not flag:
        inquiry_positions, target_positions = zip(*position_pairs)
        lowest_inquiry_position = min(inquiry_positions)
        highest_inquiry_position = max(inquiry_positions)
        if highest_inquiry_position - lowest_inquiry_position > 0:
            flag = True
    return flag