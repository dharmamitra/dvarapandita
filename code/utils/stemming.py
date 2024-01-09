import sentencepiece as spm
import ctranslate2
from utils.intern_transliteration import unicode_to_internal_transliteration
from utils.constants import *
import re
import os
import pandas as pd
import itertools
from utils.stemming_tib import tib_create_lnum, tib_get_folio_number, tib_orig_line_preparation

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

def prepare_english(string):
    # split into sentences at punctuation
    sentences = re.split(r'(?<=[^A-Z].[.?]) +(?=[A-Z])', string)
    return sentences



def cleaned_line_preparation(string,lang):
    if lang == "skt":
        string = prepare_skt(string)
    elif lang == "tib":
        string = prepare_tib(string)
    return string
        

def chunk_line(line, maxlen, lang):
    gap = ""
    if lang == "tib":
        gap = " "
    line_chunks = []
    chunk = []
    tokens = line
    if lang == "tib":
        tokens = line.split(' ')
    last_index = len(tokens) - 1
    for index, token in enumerate(tokens):
        chunk.append(token)
        if index == last_index or len(chunk) > maxlen:
            line_chunks.append(gap.join(chunk))
            chunk = []
    if len(chunk) > 0:
        line_chunks.append(chunk)
    return line_chunks

def transres2stemlist(transres):
    stemlist = []
    for result in transres.split('#'):
        result = result.strip()
        if result == '': break
        stem = result.split(' ')[0]
        stemlist.append(stem)
    print(stemlist)
    print(" ".join(stemlist))
    return " ".join(stemlist)

def create_fname(text_path):
    filename = os.path.basename(text_path)
    filename = filename.replace(".txt","")
    filename = filename.replace(".TXT","")
    filename = filename.replace(":","-") 
    return filename 

def crop_lines(filepath, lang):
    lines = []
    with open(filepath, 'r') as file:
        for line in file:
            line = line.strip()
            chunks = chunk_line(line, MAX_SEQ_LENGTH[lang], lang)
            lines.extend(chunks)
    if lang == "chn":
        return lines
    else:
        # second iteration for tib and skt only: merge lines that are shorter than maxlen / 2 with the next line
        prefix = ""
        cleaned_lines = []
        for line in lines:
            current_length = len(prefix + line)
            if lang == "tib":
                current_length = len(str(prefix + " " + line).split(" "))
            if current_length < MAX_SEQ_LENGTH[lang] / 10:
                prefix += " " + line
            elif current_length < MAX_SEQ_LENGTH[lang] and re.search("dang[^a-zA-Z]*$", line.lower()):
                prefix += " " + line
            else:
                cleaned_lines.append(prefix + " " + line)
                prefix = ""
        return cleaned_lines


    return lines

def text2lists(filename, lines, lang):
    orig_lines = []
    cleaned_lines = []
    filenames = []
    line_numbers = []
    old_folio = ""
    count = 0

    prefix = ""
    for orig_line in lines:
        orig_line = prefix + orig_line
        if not re.search(r"[a-zA-Z]", orig_line): # [1] lines without text (e.g. only numbers) are skipped -- should be extended with diacritica!!!!!! make a separate func
            prefix += orig_line.strip() + " " # the exact form of the orig line should be saved!!!
        else:
            prefix = ""
            if lang == "tib":
                new_folio = tib_get_folio_number(orig_line, filename) # only tib
                if new_folio: # only tib
                    old_folio = new_folio
                    count = 0 # insane logic
                line_number = tib_create_lnum(old_folio, count, filename) # only tib with exception of NK and NG
                orig_line = tib_orig_line_preparation(orig_line, filename) # aprt from tibetan only strip
            else:
                line_number = str(count)
            orig_line = orig_line.strip()
            cleaned_line = cleaned_line_preparation(orig_line, lang) # only tib and skt
        ################################################################################

            if not re.search(r"[a-zA-Z]", cleaned_line): # [2] the cleaned line is check if empty
                prefix += orig_line.strip() + " " # the exact form of the orig line should be saved!!!
            else:
                # Print at least a warning when encountering very long lines
                if len(orig_line) > 1000:
                    print("Line too long: " + orig_line)
                    print("WARNING: Very long line in file: " + text_path)
                orig_lines.append(orig_line)
                cleaned_lines.append(cleaned_line)
                filenames.append(filename)
                line_numbers.append(line_number)
            count += 1

    return [filenames, line_numbers, orig_lines,cleaned_lines]




def skt_stemming(text_df):
    chunk_lists = text_df['stemmed'].apply(lambda line: chunk_line(line, 120))
    chunk_exploded = chunk_lists.explode()
    chunk_list = chunk_exploded.tolist()
    tokenizer = \
        spm.SentencePieceProcessor(model_file = SKT_STEMMER_LOCATION + "spm/skt-tag8k.model")
    tonenized_chunk_list = tokenizer.encode(chunk_list, out_type=str)
    translator = ctranslate2.Translator(SKT_STEMMER_LOCATION + "model/",
                                    intra_threads=4,
                                    device='cuda')
    transres_exploded = \
        pd.Series(translator.translate_batch(tonenized_chunk_list,
            max_batch_size=48),
            index = chunk_exploded.index)

    # pd.Series.apply: https://towardsdatascience.com/avoiding-apply-ing-yourself-in-pandas-a6ade4569b7f
    transres_exploded = transres_exploded.apply(lambda line:
        tokenizer.decode(line[0]['tokens']) )
    # leave only the stems
    transres_exploded = transres_exploded.apply(transres2stemlist)
    text_df['stemmed'] = transres_exploded#.groupby(chunk_exploded.index).apply(lambda lists:
    #itertools.chain(*lists) )
    return text_df


