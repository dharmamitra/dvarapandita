import json
import sys
import gzip
import os
import re
from utils.constants import *

def test_match_tib(match):
    if match['par_length'] >= MIN_LENGTH['tib']:
        return True
    else:
        if match['par_length'] >= 7 and match['root_length'] >= 7:
            fragments = match['root_string'].split("/")
            longest_fragment = max(fragments, key=len)
            if len(re.sub("@.+", "", longest_fragment).split()) >= 7:
                inquiry_string = "/ " + " ".join(match['root_segtext'])
                target_string = "/ " + " ".join(match['par_segtext'])
                inquiry_string = re.sub("@.+", "", inquiry_string)
                target_string = re.sub("@.+", "", target_string)
                inquiry_string = re.sub(r" [^a-zA-Z/]+ ", " ", inquiry_string)
                target_string = re.sub(r" [^a-zA-Z/]+ ", " ", target_string)
                if re.search("/ [a-zA-Z+]+ [a-zA-Z+]+ [a-zA-Z+]+ [a-zA-Z+]+ [a-zA-Z+]+ [a-zA-Z+]+ [a-zA-Z+]+ //", inquiry_string):
                    return True
                if re.search("/ [a-zA-Z+]+ [a-zA-Z+]+ [a-zA-Z+]+ [a-zA-Z+]+ [a-zA-Z+]+ [a-zA-Z+]+ [a-zA-Z+]+ [a-zA-Z+]+ [a-zA-Z+]+ //", inquiry_string):
                    return True
                if re.search("/ [a-zA-Z+]+ [a-zA-Z+]+ [a-zA-Z+]+ [a-zA-Z+]+ [a-zA-Z+]+ [a-zA-Z+]+ [a-zA-Z+]+ [a-zA-Z+]+ [a-zA-Z+]+ [a-zA-Z+]+ [a-zA-Z+]+ //", inquiry_string):
                    return True
                if re.search("/ [a-zA-Z+]+ [a-zA-Z+]+ [a-zA-Z+]+ [a-zA-Z+]+ [a-zA-Z+]+ [a-zA-Z+]+ [a-zA-Z+]+ //", target_string):
                    return True
                if re.search("/ [a-zA-Z+]+ [a-zA-Z+]+ [a-zA-Z+]+ [a-zA-Z+]+ [a-zA-Z+]+ [a-zA-Z+]+ [a-zA-Z+]+ [a-zA-Z+]+ [a-zA-Z+]+ //", target_string):
                    return True
                if re.search("/ [a-zA-Z+]+ [a-zA-Z+]+ [a-zA-Z+]+ [a-zA-Z+]+ [a-zA-Z+]+ [a-zA-Z+]+ [a-zA-Z+]+ [a-zA-Z+]+ [a-zA-Z+]+ [a-zA-Z+]+ [a-zA-Z+]+ //", target_string):
                    return True


def filter_matches(matches):
    filtered_matches = []
    for match in matches:
        if match['root_segnr'][0].split(':')[0] != match['par_segnr'][0].split(":")[0]:        
            if match['src_lang'] == "tib":
                if test_match_tib(match):
                    filtered_matches.append(match)
            else:
                filtered_matches.append(match)
    return filtered_matches


def merge_matches(path):
    if "$0" in path:
        total_segment_numbers = []
        total_matches = []
        for c in range(0, 1000):
            if os.path.isfile(path.replace("$0", "$" + str(c))):
                print("MERGING", path.replace("$0", "$" + str(c)))
                with gzip.open(path.replace("$0", "$" + str(c)), "rb") as f:
                    data = json.load(f)
                    total_segment_numbers.extend(data[0])
                    for match in data[1]:
                        if match['src_lang'] == "tib":
                            if test_match_tib(match):
                                total_matches.append(match)
                        else:
                            total_matches.append(match)
        for i in range(len(total_segment_numbers)):
            total_segment_numbers[i]['position'] = i

        id_stem = total_matches[0]['id'].split(":")[0]
        for i in range(len(total_matches)):
            total_matches[i]['id'] = id_stem + ":" + str(i)
        result = [total_segment_numbers, total_matches]
        json_str = json.dumps(result,indent=4,ensure_ascii=False) + "\n"               # 2. string (i.e. JSON)
        json_bytes = json_str.encode('utf-8')
        with gzip.GzipFile(path.replace("$0", "_filtered"), 'w') as f:
            f.write(json_bytes)



#merge_matches(sys.argv[1])
#merge_matches("../tibetan-work/folder1/T06D4021$0.json.gz")