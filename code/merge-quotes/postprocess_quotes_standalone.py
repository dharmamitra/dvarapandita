from quotes_constants import *
from postprocess_quotes import postprocess_quotes_tib,postprocess_quotes_skt
import sys
import gzip
import json
import os


def process_file(filename):
    filename_json = filename.replace(".json.gz","_cleaned.json.gz")
    if os.path.isfile(filename_json):
        return
    with gzip.open(filename,'rt') as f:
        segments,quotes = json.load(f)
        if len(quotes) > 0:
            lang = quotes[0]['src_lang']
            if lang == "tib":
                quotes = postprocess_quotes_tib(quotes)
            if lang == "skt":
                quotes = postprocess_quotes_skt(quotes)
        json_str = json.dumps([segments,quotes],indent=4,ensure_ascii=False) + "\n"              
        json_bytes = json_str.encode('utf-8')
        with gzip.GzipFile(filename_json, 'w') as fout:   # 4. gzip
            fout.write(json_bytes)  

process_file(sys.argv[1])

#process_file("/mnt/output/tib/tab/folder4/T01TD1127E.json.gz")
#process_file("/mnt/output/tib/tab/folder1/T06TD4032E-9.json.gz")
#process_file("/mnt/output/tib/json/T06TD4032E.json.gz")
#process_file("/mnt/output/tib/json_gap7_final/T06D4032.json.gz")
