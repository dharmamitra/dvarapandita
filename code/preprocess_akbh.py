import re
mainfile = open("../data-akbh/T07vakobhau.tsv",'r')

current_verse = "VAkK_1.1"
c = 0
result = ""
for line in mainfile:
    entries = line.split('\t')
    if "VAkK" in entries[1]:
        current_verse = re.search("(VAkK[^ ]+)",entries[1])[1]
        c = 0
    segment_name = current_verse + ":" + str(c)
    c+=1
    result += segment_name + '\t' + '\t'.join(entries[1:])

with open("../data-akbh/T07vakobhau.tsv",'w') as outfile:
    outfile.write(result)

    
