# -*- coding: utf-8 -*-
#!/usr/bin/python
"""
Internal transliteration
"""

UNICODE_INTERN = [
        (u'ā',  'A'),
        (u'ī',  'I'),
        (u'ū',  'U'),
        (u'ṛ',  'R'),
        (u'ṝ',  'L'), # ??
        (u'ḷ',  '?'),
        (u'ḹ',  '?'),
        (u'ai', 'E'),
        (u'au', 'O'),
        # gutturals
            (u'kh', 'K'),
        (u'gh', 'G'),
        (u'ṅ',  'F'),
        # palatals
            (u'ch', 'C'),
        (u'jh', 'J'),
        (u'ñ',  'Q'),
        # retroflexes
            (u'ṭh', 'W'),
        (u'ṭ',  'w'),
        (u'ḍh', 'X'),
        (u'ḍ',  'X'),
        (u'ṇ',  'N'),
        # dentals
            (u'th', 'T'),
        (u'dh', 'D'),
        # labials 
            (u'ph', 'P'),
        (u'bh', 'B'),
        # others
            (u'ś',  'S'),
        (u'ṣ',  'z'),
        (u'ṃ',  'M'),
        (u'ḥ',  'H')
]
INTERN_UNICODE = [
        (u'ā',  'A'),
        (u'ī',  'I'),
        (u'ū',  'U'),
        (u'ṛ',  'R'),
        (u'ṝ',  'L'), # ??
        (u'ḷ',  '?'),
        (u'ḹ',  '?'),
        (u'ai', 'E'),
        (u'au', 'O'),
        # gutturals
            (u'kh', 'K'),
        (u'gh', 'G'),
        (u'ṅ',  'F'),
        # palatals
            (u'ch', 'C'),
        (u'jh', 'J'),
        (u'ñ',  'Q'),
        # retroflexes; ORDER MATTERS
            (u'ṭ',  'w'),
        (u'ṭh', 'W'),
        (u'ḍ',  'X'),
        (u'ḍh', 'X'),
        (u'ṇ',  'N'),
        # dentals
            (u'th', 'T'),
        (u'dh', 'D'),
        # labials 
            (u'ph', 'P'),
        (u'bh', 'B'),
        # others
            (u'ś',  'S'),
        (u'ṣ',  'z'),
        (u'ṃ',  'M'),
        (u'ḥ',  'H')
]

def unicode_to_internal_transliteration(s):
        for src,dst in UNICODE_INTERN:
                s = s.replace(src,dst)
        out = s
        return out

def internal_to_unicode_transliteration(s):
        for src,dst in INTERN_UNICODE:
                s = s.replace(dst,src)
        out = s
        return out




