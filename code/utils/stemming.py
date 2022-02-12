from xliterator import unicode_to_internal_transliteration
import re

TIBETAN_STEMFILE="data/verbinator_tabfile.txt"



def initialize_tibetan_stemmer(tibetan_stemfile):
    global r
    r = open(tibetan_stemfile,'r')
    stems = {}
    
    for line in r:
        headword = line.split('\t')[0]
        entry = line.split('\t')[2].strip()
        stems[headword] = entry
    return stems 

tib_stems = initialize_tibetan_stemmer(TIBETAN_STEMFILE)

def multireplace(string,tib_stems):
    string1 = string
    if string in tib_stems:
        string = tib_stems[string]
    return string



def prepare_skt(string):
    string = string.lower()
    string = re.sub(r"// ?([^ ]+_[^ ]+) ?//","",string)
    string = re.sub(r"\|\| ?([^ ]+_[^ ]+) ?\|\|","",string)
    string = re.sub(r'[^\s]+[0-9][^\s]+',"",string)
    string = string.replace('ñ ','ṃ ')
    string = re.sub(r"[^a-zA-ZāĀīĪūŪṛṚṝḷḶḹṅṄñÑṭṬḍḌṇṆśŚṣṢṃḥēōḻṟṉḵṯ \n]","",string)
    string = string.strip()
    string = unicode_to_internal_transliteration(string)
    return string

def prepare_tib(string):    
    result = ''
    string = string.replace("+"," ")
    for word in string.split():
        if not "/" in word and not "@" in word and re.search("[a-zA-Z]",word):
            word_stripped = word.split("'")[0]
            result += multireplace(word_stripped,tib_stems) + " "
    return result

def prepare(string,lang):
    if lang == "skt":
        string = prepare_skt(string)
    elif lang == "tib":
        string = prepare_tib(string)
    return string
        

def chunk_line(line, maxlen):
    line_chunks = []

    chunk = ""
    tokens = line.split(' ')
    last_index = len(tokens) - 1
    for index, token in enumerate(tokens):
        chunk += token + " "
        if index == last_index or len(chunk) > maxlen:
            line_chunks.append(chunk)
            chunk = ""
    if chunk:
        line_chunks.append(chunk)
    return line_chunks

def transres2stemlist(transres):
    stemlist = []
    for result in transres.split('#'):
        result = result.strip()
        if result == '': break
        stem = result.split(' ')[0]
        stemlist.append(stem)
    return stemlist

def create_segnr(folio,count,filepath):
    # include folio numbers for KG/TG, not for other files
    filename = re.sub(".*/","",filepath)
    filename = re.sub("\..*","",filename)
    filename = filename.replace(":","-") 
    if "NK" in filename or "NG" in filename or len(folio) == 0:
        return filename + ":" + str(count)
    else:
        return filename + ":" + folio.lower() + '-' + str(count)


def get_folio_number(line):
    folio_number = ""
    m =  re.search("@([0-9]+[abAB])",line)
    if m:
        folio_number = m.group(1)
        return folio_number
    # this is for NyGB
    else:
        m =  re.search("([0-9])+[^a-zA-Z@]+@",line)
        if m:
            folio_number = m.group(1)
            return folio_number.lower()

def text2list(text_path,lang):
    lines = []
    cleaned_lines = []
    segmentnrs = []
    folio = ""
    count = 0 
    with open(text_path,"r") as text:
        prefix = ""
        for line in text:
            # For Tibetan, we extract the folio numbers from the lines
            if lang == "tib":
                new_folio = get_folio_number(line)
                if new_folio and not"NK" in text_path and not "NG" in text_path:
                    folio = new_folio
                    count = 0
                    
            line = prefix + line  #.strip()
            if not re.search(r"[a-zA-Z]", line):
                prefix += line.strip() + " "
            else:
                prefix = ""
                line = line.strip()
                # a bit of tibetan-specific preprocessing
                if lang == "tib":
                    line = line.lower()
                    if "T" in text_path:
                        line = line.replace("ts","tsh")
                        line = line.replace("tz","ts")
                    line = line.replace(',','/')
                    line = line.replace('|','/')
                segmentnr = create_segnr(folio,count,text_path)
                cleaned_line = prepare(line,lang)
                lines.append(line)
                cleaned_lines.append(cleaned_line)
                segmentnrs.append(segmentnr)
                count += 1
    return [segmentnrs,lines,cleaned_lines]
        
