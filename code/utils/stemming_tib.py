import re

TIBETAN_STEMFILE="ref/verbinator_tabfile.txt"



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
    if string in tib_stems:
        string = tib_stems[string]
    return string


def tib_create_lnum(folio,count,filename):
    # include folio numbers for KG/TG, not for other files
    if "NK" in filename or "NG" in filename or len(folio) == 0: # genial!
        return str(count)
    else:
        return folio.lower() + '-' + str(count)


def tib_get_folio_number(line, text_path):
    # For Tibetan, we extract the folio numbers from the lines
    # if lang == "tib":
    if not "NK" in text_path and not "NG" in text_path:
        match =  re.search("@([0-9]+[abAB])",line)
        if match:
            return match.group(1)
        # this is for NyGB
        else:
            match =  re.search("([0-9])+[^a-zA-Z@]+@",line)
            if match:
                return match.group(1)

def tib_orig_line_preparation(line, text_path):    
    line = line.lower()
    if "T" in text_path:
        line = line.replace("ts","tsh")
        line = line.replace("tz","ts")
    line = line.replace(',','/')
    line = line.replace('|','/')
    # This substitution is necessary due to a special problem in the rinchen gter mdzod texts
    line = re.sub(r"\[.*?\]", "", line)
    if "unicode" in line:
        print(line)
    return line

def prepare_tib(string):    
    result = ''
    #string = string.replace("+"," ")
    string = re.sub(r"\([0-9]+\)", "", string)
    for word in string.split():
        if not "/" in word and not "@" in word and re.search("[a-zA-Z]",word):
            # todo: Orna fragen wegen den genauen Apostroph-handling hier?
            word_stripped = word.replace("'i", "")
            word_stripped = word_stripped.replace("'o", "")
            word_stripped = word_stripped.replace("'ang", "")
            word_stripped = word_stripped.replace("'am", "")            
            result += multireplace(word_stripped,tib_stems).replace("'","") + " "
    return result

def tib_clean_line(filename, orig_line, current_folio, count):
    new_folio = tib_get_folio_number(orig_line, filename) # only tib
    if new_folio: # only tib
        current_folio = new_folio
        count = 0 # insane logic
    line_number = tib_create_lnum(current_folio, count, filename) # only tib with exception of NK and NG
    orig_line = tib_orig_line_preparation(orig_line, filename) # aprt from tibetan only strip
    return orig_line, current_folio, line_number, count
