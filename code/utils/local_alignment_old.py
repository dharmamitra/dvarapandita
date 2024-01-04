from Bio import pairwise2
from Bio import Align

import re
from utils.constants import PUNC, TIBETAN_STEMFILE

def create_replaces_dictionary(path):
    replaces_dictionary = {}
    r = open(path, "r")
    for line in r:
        headword = line.split('\t')[0]
        entry = line.split('\t')[2]
        replaces_dictionary[headword] = entry.strip()
    return replaces_dictionary

replaces_dictionary = create_replaces_dictionary(TIBETAN_STEMFILE)

def multireplace(string):
    if string in replaces_dictionary:
        string = replaces_dictionary[string]
    return string


def crude_stemmer(tokens):
    tokens = [multireplace(x) for x in tokens]
    result_tokens = []
    for token in tokens:
        token = re.sub(r"([a-z])\'.*", r"\1", token)
        if "/" in tokens:
            token = token + str(random.randint(1, 100))
        result_tokens.append(token)
    return result_tokens


def get_aligned_offsets_efficient(inquiry_text, target_text, threshold, lang):
    # efficient version of get_aligned_offsets where we only look at the first 100 tokens in both directions, avoiding the algorithm to get stuck on very long matches
    if len(inquiry_text) < threshold or len(target_text) < threshold:
        return get_aligned_offsets(inquiry_text, target_text, lang)
    else:
        inquiry_text_beg, w, target_text_beg, v, score_beg = get_aligned_offsets(inquiry_text[:threshold],
                                                                         target_text[:threshold], lang)
        x, inquiry_text_end, y, target_text_end, score_end = get_aligned_offsets(inquiry_text[-threshold:],
                                                                         target_text[-threshold:], lang)
        score = (score_beg + score_end) / 2
        inquiry_text_end = inquiry_text_end + len(inquiry_text) - threshold
        target_text_end = target_text_end + len(target_text) - threshold
        return inquiry_text_beg, inquiry_text_end, target_text_beg, target_text_end, score
def get_aligned_offsets(stringa, stringb, lang="tib"):
    stringa = stringa.lower()
    stringb = stringb.lower()
    alignments = []
    if lang == "tib":
        stringa_tokens_before = stringa.split()
        stringb_tokens_before = stringb.split()
        c = 0
        stringa_lengths = []
        stringa_tokens_after = []
        for token in stringa_tokens_before:
            if not "/" in token and not "@" in token and token not in PUNC and not re.search('[0-9]', token):
                stringa_lengths.append(c)
                stringa_tokens_after.append(token)
            if lang == "tib":
                c += len(token) + 1
            else:
                c += len(token)
        c = 0
        stringb_lengths = []
        stringb_tokens_after = []
        for token in stringb_tokens_before:
            if not "/" in token and not "@" in token and token not in PUNC and not re.search('[0-9]', token):
                stringb_lengths.append(c)
                stringb_tokens_after.append(token)
            if lang == "tib":
                c += len(token) + 1
            else:
                c += len(token)
        stringa_tokens = stringa_tokens_after
        stringb_tokens = stringb_tokens_after

        stringa_tokens = crude_stemmer(stringa_tokens_after)
        stringb_tokens = crude_stemmer(stringb_tokens_after)


        alignments = pairwise2.align.localms(stringa_tokens, stringb_tokens, 5, -4, -5, -5, gap_char=["-"],
                                             one_alignment_only=1)


        if len(alignments) > 0:
            if len(alignments[0]) == 5:
                resulta, resultb, score, beg, end = alignments[0]
                score = (score / abs(beg - end))
                a_beg = resulta[:beg]
                a_len = len([x for x in a_beg if x is not '-'])
                a_offset_beg = stringa_lengths[a_len]
                b_beg = resultb[:beg]
                b_len = len([x for x in b_beg if x is not '-'])
                b_offset_beg = stringb_lengths[b_len]
                a_end = resulta[:end]
                a_len = len([x for x in a_end if x is not '-'])
                if a_len < len(stringa_lengths):
                    a_offset_end = stringa_lengths[a_len]
                else:
                    a_offset_end = len(stringa)
                b_end = resultb[:end]
                b_len = len([x for x in b_end if x is not '-'])
                if b_len < len(stringb_lengths):
                    b_offset_end = stringb_lengths[b_len]
                else:
                    b_offset_end = len(stringb)
                stringa_last_token = stringa[:a_offset_end].strip().split(' ')[-1]
                if "/" in stringa_last_token or "@" in stringa_last_token:
                    a_offset_end -= len(stringa_last_token) + 1
                stringb_last_token = stringb[:b_offset_end].strip().split(' ')[-1]
                if "/" in stringb_last_token or "@" in stringb_last_token:
                    b_offset_end -= len(stringb_last_token) + 1
                return a_offset_beg, a_offset_end, b_offset_beg, b_offset_end, score
            else:
                return 0, 0, 0, 0, 0
        else:
            return 0, 0, 0, 0, 0
    if lang == "chn" or lang == "pli" or lang == "skt":
        stringa = stringa.lower()
        stringb = stringb.lower()
        stringa_before = stringa
        stringb_before = stringb
        c = 0
        stringa_lengths = []
        stringa_after = []
        for token in stringa_before:
            if not token in PUNC:
                stringa_lengths.append(c)
                stringa_after.append(token)
            c += 1
        c = 0
        stringb_lengths = []
        stringb_after = []
        for token in stringb_before:
            if not token in PUNC and not re.search("[0-9]", token):
                stringb_lengths.append(c)
                stringb_after.append(token)
            c += 1
        if lang == "chn":
            alignments = pairwise2.align.localms(stringa_after, stringb_after, 1, -1, -0.8, -0.3, gap_char=["-"],
                                                 one_alignment_only=1)
        if lang == "pli" or lang == "skt":
            # alignments = pairwise2.align.localms(stringa_after,stringb_after,2,-1,-1.5,-0.3, gap_char=["-"],one_alignment_only=1)
            alignments = pairwise2.align.localms(stringa_after, stringb_after, 1, -2, -1.0, -0.5, gap_char=["-"],
                                                 one_alignment_only=1)
        if len(alignments) > 0:
            if len(alignments[0]) == 5:
                resulta, resultb, score, beg, end = alignments[0]
                score = (score / abs(beg - end))
                a_beg = resulta[:beg]
                a_len = len([x for x in a_beg if x not in PUNC])
                a_offset_beg = stringa_lengths[a_len]
                b_beg = resultb[:beg]
                b_len = len([x for x in b_beg if x not in PUNC])
                b_offset_beg = stringb_lengths[b_len]
                a_end = resulta[:end]
                a_len = len([x for x in a_end if x not in PUNC])
                if a_len < len(stringa_lengths):
                    a_offset_end = stringa_lengths[a_len]
                else:
                    a_offset_end = len(stringa)
                b_end = resultb[:end]
                b_len = len([x for x in b_end if x not in PUNC])
                if b_len < len(stringb_lengths):
                    b_offset_end = stringb_lengths[b_len]
                else:
                    b_offset_end = len(stringb)
                while stringa[a_offset_end - 1] in PUNC and a_offset_end > 2:
                    a_offset_end -= 1
                while stringb[b_offset_end - 1] in PUNC and b_offset_end > 2:
                    b_offset_end -= 1
                return a_offset_beg, a_offset_end, b_offset_beg, b_offset_end, score
            else:
                return 0, 0, 0, 0, 0
        else:
            return 0, 0, 0, 0, 0
