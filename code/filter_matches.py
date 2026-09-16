import json
import gzip
import re
import regex
#from utils.constants import *
from utils.general import test_if_should_load

tib_stop = set(line.strip() for line in open("ref/tib_stop.txt"))

chn_stop = set(line.strip() for line in open("ref/chn_stop.txt"))

def test_if_stopword_tib(word):
    if word in tib_stop:
        return True
    else:
        return False

def test_if_stopword_chn(word):
    if word in chn_stop:
        return True
    else:
        return False

def get_tib_stopword_ratio(string):
    words = string.split()
    stopword_count = sum(test_if_stopword_tib(word) for word in words)
    return stopword_count / len(words)

def get_chn_stopword_ratio(string):
    words = string.split()
    stopword_count = sum(test_if_stopword_chn(word) for word in words)
    return stopword_count / len(words)

def test_match_tib(match):
    if get_tib_stopword_ratio(match['root_string']) > 0.7 and get_tib_stopword_ratio(match['par_string']) > 0.7:
        return False    
    if match['par_length'] >= 14:
        return True
    else:
        if match['par_length'] >= 7 and match['root_length'] >= 7:
            fragments = match['root_string'].split("/")
            longest_fragment = max(fragments, key=len)
            if len(re.sub("@.+", "", longest_fragment).split()) >= 7:                
                    root_offset_beg = match['root_offset_beg'] -3
                    root_offset_end = match['root_offset_end'] +3
                    par_offset_beg = match['par_offset_beg'] -3
                    par_offset_end = match['par_offset_end'] +3
                    if root_offset_beg < 0:
                        root_offset_beg = 0
                    if par_offset_beg < 0:
                        par_offset_beg = 0               
                    inquiry_string = "/ " + " ".join(match['root_segtext'])
                    target_string = "/ " + " ".join(match['par_segtext'])
                    inquiry_string = inquiry_string[root_offset_beg:root_offset_end]
                    target_string = target_string[par_offset_beg:par_offset_end]

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

def test_match_pli_skt(match):
    if match['par_length'] >= 30:
        return True

def test_match_chn(match):
    #if "論" in match['root_string'] or "論" in match['par_string']:
    #    return 
    #if "經" in match['root_string'] or "經" in match['par_string']:
    #    return
    #if "卷" in match['root_string'] or "卷" in match['par_string']:
    #    return
    if get_chn_stopword_ratio(match['root_string']) > 0.7 and get_chn_stopword_ratio(match['par_string']) > 0.7:
        return False
    elif match['par_length'] >= 9 and match['root_length'] >= 9:
        return True
    else:
        inquiry_string = "".join(match['root_segtext'])
        target_string = "".join(match['par_segtext'])
        inquiry_string = inquiry_string[match['root_offset_beg']-3:match['root_offset_end']+3]
        target_string = target_string[match['par_offset_beg']-3:match['par_offset_end']+3]
        # test if inquiry_string contains 5 chinese characters preceeded by punctuation and followed by punctuation
        if regex.search(r"(^[。，！？　]|[\p{Han}]{5}|[。，！？　]$)", inquiry_string):
            return True
        if regex.search(r"(^[。，！？　]|[\p{Han}]{5}|[。，！？　]$)", target_string):
            return True
        if regex.search(r"(^[。，！？　]|[\p{Han}]{6}|[。，！？　]$)", inquiry_string):
            return True
        if regex.search(r"(^[。，！？　]|[\p{Han}]{6}|[。，！？　]$)", target_string):
            return True

def filter_matches(matches):
    print("LENGTH OF MATCHES", len(matches))
    filtered_matches = []
    for match in matches:
        if not "root_segnr" in match:
            continue
        if not test_if_should_load(match['root_segnr'][0]):
            continue
        if not test_if_should_load(match['par_segnr'][0]):
            continue
            
        if match['root_segnr'][0].split(':')[0] != match['par_segnr'][0].split(":")[0]:        
            match['id'] = match['root_segnr'][0] + "_" + match['par_segnr'][0]
            if match['src_lang'] == "tib":                      
                if test_match_tib(match):                    
                    filtered_matches.append(match)
            elif match['src_lang'] == "chn":
                if test_match_chn(match):
                    filtered_matches.append(match)
            elif match['src_lang'] == "skt" or match['src_lang'] == "pli":
                if test_match_pli_skt(match):
                    filtered_matches.append(match)
            else:
                filtered_matches.append(match)    
    return filtered_matches

def process_path(path):
    # load matches from gzip at path
    matches = json.load(gzip.open(path, 'rt'))
    # filter matches
    filtered_matches = filter_matches(matches)
    # write filtered matches to gzip at path
    with gzip.open(path, 'wt') as f:
        json.dump(filtered_matches, f)
