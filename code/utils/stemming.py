import sentencepiece as spm
import ctranslate2
from utils.intern_transliteration import unicode_to_internal_transliteration
from utils.constants import *
import re
import os


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
            # todo: Orna fragen wegen den genauen Apostroph-handling hier?
            word_stripped = word.replace("'i", "")
            word_stripped = word_stripped.replace("'o", "")
            word_stripped = word_stripped.replace("'ang", "")
            word_stripped = word_stripped.replace("'am", "")            
            result += multireplace(word_stripped,tib_stems).replace("'","") + " "
    return result




def cleaned_line_preparation(string,lang):
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

def create_lnum(folio,count,filename):
    # include folio numbers for KG/TG, not for other files
    if "NK" in filename or "NG" in filename or len(folio) == 0:
        return str(count)
    else:
        return folio.lower() + '-' + str(count)


def get_folio_number(line, lang, text_path):
    # For Tibetan, we extract the folio numbers from the lines
    if lang == "tib" and not "NK" in text_path and not "NG" in text_path:
        match =  re.search("@([0-9]+[abAB])",line)
        if match:
            return match.group(1)
        # this is for NyGB
        else:
            match =  re.search("([0-9])+[^a-zA-Z@]+@",line)
            if match:
                return match.group(1)

def orig_line_preparation(line, lang, text_path):    
    if lang == "tib":
        line = line.lower()
        if "T" in text_path:
            line = line.replace("ts","tsh")
            line = line.replace("tz","ts")
        line = line.replace(',','/')
        line = line.replace('|','/')
    return line.strip()

def create_fname(text_path):
    filename = os.path.basename(text_path)
    filename = filename.replace(":","-") 
    return filename 
            
def text2lists(text_path,lang):
    orig_lines = []
    cleaned_lines = []
    filenames = []
    line_numbers = []
    folio = ""
    count = 0
    filename = create_fname(text_path)
    with open(text_path,"r") as text:
        prefix = ""
        for orig_line in text:
            orig_line = prefix + orig_line
            if not re.search(r"[a-zA-Z]", orig_line):
                prefix += orig_line.strip() + " "
            else:                
                new_folio = get_folio_number(orig_line, lang, text_path)
                if new_folio:
                    folio = new_folio
                    count = 0
                prefix = ""
                orig_line = orig_line_preparation(orig_line, lang, text_path)
                line_number = create_lnum(folio, count, filename)                
                cleaned_line = cleaned_line_preparation(orig_line, lang)
                if not re.search(r"[a-zA-Z]", cleaned_line):
                    prefix += orig_line.strip() + " "
                else:
                    orig_lines.append(orig_line)
                    cleaned_lines.append(cleaned_line)
                    filenames.append(filename)
                    line_numbers.append(line_number)                
                count += 1
                
    return [filenames, line_numbers, orig_lines,cleaned_lines]




def skt_stemming(text_df):
    chunk_lists = text_df['stemmed'].apply(lambda line: chunk_line(line), 120)
    chunk_exploded = chunk_lists.explode()
    chunk_list = chunk_exploded.tolist()
    tokenizer = \
        spm.SentencePieceProcessor(model_file = location + "spm/skt-tag8k.model")
    tonenized_chunk_list = tokenizer.encode(chunk_list, out_type=str)
    translator = ctranslate2.Translator(location + "model/",
                                    intra_threads=4,
                                    device='cpu')
    transres_exploded = \
        pd.Series(translator.translate_batch(tonenized_chunk_list,
            max_batch_size=548),
            index = chunk_exploded.index)

    # pd.Series.apply: https://towardsdatascience.com/avoiding-apply-ing-yourself-in-pandas-a6ade4569b7f
    transres_exploded = transres_exploded.apply(lambda line:
        tokenizer.decode(line[0]['tokens']) )
    # leave only the stems
    transres_exploded = transres_exploded.apply(transres2stemlist)
    text_df['stemmed'] = \
        transres_exploded.groupby(chunk_exploded.index).apply(lambda lists:
    list(itertools.chain(*lists)) )    
    return text_df


