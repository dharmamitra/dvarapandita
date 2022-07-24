import json
import gzip
mainfile = json.load(gzip.open("../output/T07vakobhau-0.json.gz",'rb'))


data = {}
for segment in mainfile[0]:
    data[segment['segnr']] = []

for match in mainfile[1]:
    for src_segment in match['root_segnr']:
        if not src_segment in match['par_segnr']: # this is necessary to remove self-referential matches
            for tgt_segment in match['par_segnr']:
                data[src_segment].append(tgt_segment)

result = ""
for src_segment in data.keys():
    for tgt_segment in data[src_segment]:
        result += src_segment + "\t" + tgt_segment + "\n"

with open("../output/test.tab",'w') as testfile:
    testfile.write(result)
