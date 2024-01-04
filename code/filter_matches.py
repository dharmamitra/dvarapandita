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


