import numpy as cp
import time
from Bio import pairwise2
import pyopa
import os
import itertools
import cupy as np
DELETION, INSERTION, MATCH = range(3)

def smith_waterman(seq1, seq2, insertion_penalty = -1, deletion_penalty = -1,
                   mismatch_penalty = -1, match_score = 2):
    """
    Find the optimum local sequence alignment for the sequences `seq1`
    and `seq2` using the Smith-Waterman algorithm. Optional keyword
    arguments give the gap-scoring scheme:

    `insertion_penalty` penalty for an insertion (default: -1)
    `deletion_penalty`  penalty for a deletion (default: -1)
    `mismatch_penalty`  penalty for a mismatch (default: -1)
    `match_score`       score for a match (default: 2)

    See <http://en.wikipedia.org/wiki/Smith-Waterman_algorithm>.

    >>> for s in smith_waterman('AGCAGACT', 'ACACACTA'): print s
    ... 
    AGCAGACT-
    A-CACACTA
    """
    m, n = len(seq1), len(seq2)

    # Construct the similarity matrix in p[i][j], and remember how
    # we constructed it -- insertion, deletion or (mis)match -- in
    # q[i][j].
    p = cp.zeros((m + 1, n + 1))
    q = cp.zeros((m + 1, n + 1))
    time_before = time.time()
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            deletion = (p[i - 1][j] + deletion_penalty, DELETION)
            insertion = (p[i][j - 1] + insertion_penalty, INSERTION)
            if seq1[i - 1] == seq2[j - 1]:
                match = (p[i - 1][j - 1] + match_score, MATCH)
            else:
                match = (p[i - 1][j - 1] + mismatch_penalty, MATCH)
            p[i][j], q[i][j] = max((0, 0), deletion, insertion, match)
    # print(p)
    # print(q)

    # Yield the aligned sequences one character at a time in reverse
    # order.
    def backtrack():
        i, j = m, n
        while i > 0 or j > 0:
            assert i >= 0 and j >= 0
            if q[i][j] == MATCH:
                i -= 1
                j -= 1
                yield seq1[i], seq2[j]
            elif q[i][j] == INSERTION:
                j -= 1
                yield '-', seq2[j]
            elif q[i][j] == DELETION:
                i -= 1
                yield seq1[i], '-'
            else:
                assert(False)
    time_after = time.time()
    print("TIME NP",time_after - time_before)
    return [''.join(reversed(s)) for s in zip(*backtrack())]

chn_stringa = "。若如是者則能無倒顯示空相"
chn_stringb = "二性是有。。。實知以實知故即能無倒顯示空相"

stringa = "aabbccddd"
stringb = "aabccdddd"
time_before1 = time.time()
print(smith_waterman(stringa, stringb, insertion_penalty = -1, deletion_penalty = -1,
                     mismatch_penalty = -1, match_score = 2))
time_after1 = time.time()
print("TIME NP OUTER",time_after1-time_before1)

time_before = time.time()
print(pairwise2.align.localms(stringa,stringb,2,-1,-1,-1, gap_char="-",one_alignment_only=1))
time_after = time.time()
print("TIME SKBIO",time_after-time_before)

log_pam1_env = pyopa.read_env_json(os.path.join(pyopa.matrix_dir(), 'logPAM1.json'))
time_before = time.time()
s1 = pyopa.Sequence(stringb.upper())
s2 = pyopa.Sequence(stringa.upper())

# super fast check whether the alignment reaches a given min-score
min_score = 100
pam250_env = pyopa.generate_env(log_pam1_env, 250, min_score)
print(pyopa.align_short(s1, s2, pam250_env))

time_after = time.time()
print("TIME PYOPA",time_after-time_before)



def matrix(a, b, match_score=3, gap_cost=2):
    H = np.zeros((len(a) + 1, len(b) + 1), np.int)

    for i, j in itertools.product(range(1, H.shape[0]), range(1, H.shape[1])):
        match = H[i - 1, j - 1] + (match_score if a[i - 1] == b[j - 1] else - match_score)
        delete = H[i - 1, j] - gap_cost
        insert = H[i, j - 1] - gap_cost
        H[i, j] = max(match, delete, insert, 0)
    return H

def traceback(H, b, b_='', old_i=0):
    # flip H to get index of **last** occurrence of H.max() with np.argmax()
    H_flip = np.flip(np.flip(H, 0), 1)
    i_, j_ = np.unravel_index(H_flip.argmax(), H_flip.shape)
    i, j = np.subtract(H.shape, (i_ + 1, j_ + 1))  # (i, j) are **last** indexes of H.max()
    if H[i, j] == 0:
        return b_, j
    b_ = b[j - 1] + '-' + b_ if old_i - i > 1 else b[j - 1] + b_
    return traceback(H[0:i, 0:j], b, b_, i)

def smith_waterman2(a, b, match_score=3, gap_cost=2):
    a, b = a.upper(), b.upper()
    H = matrix(a, b, match_score, gap_cost)
    b_, pos = traceback(H, b)
    return pos, pos + len(b_)


time_before1 = time.time()
print(smith_waterman2(stringa, stringb, match_score = 2,gap_cost=1))
time_after1 = time.time()
print("TIME NP ALT",time_after1-time_before1)
