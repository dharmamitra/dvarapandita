import gzip
import sys
import string
import json

filename = sys.argv[1]
print(filename)
with gzip.open(filename,'r') as f:
    segments,quotes = json.load(f)
    lang = segments[0]['lang']
    for quote in quotes:
        quote['src_lang'] = lang
        quote['tgt_lang'] = lang
    with open(filename[:-8] +"_fixed.json", 'w') as outfile:        
        json.dump([segments,quotes], outfile,indent=4,ensure_ascii=False)


                  
