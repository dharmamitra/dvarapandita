import re
import sentencepiece as spm
import ctranslate2
import pandas as pd
from utils.constants import *
from utils.intern_transliteration import unicode_to_internal_transliteration

# import itertools

def transres2stemlist(transres):
    stemlist = []
    for result in transres.split("#"):
        result = result.strip()
        if result == "":
            break
        stem = result.split(" ")[0]
        stemlist.append(stem)
    print(stemlist)
    print(" ".join(stemlist))
    return " ".join(stemlist)

def prepare_skt(string):
    string = string.lower()
    string = re.sub(r"// ?([^ ]+_[^ ]+) ?//", "", string)
    string = re.sub(r"\|\| ?([^ ]+_[^ ]+) ?\|\|", "", string)
    string = re.sub(r"[^\s]+[0-9][^\s]+", "", string)
    string = string.replace("ñ ", "ṃ ")
    string = re.sub(r"[^a-zA-ZāĀīĪūŪṛṚṝḷḶḹṅṄñÑṭṬḍḌṇṆśŚṣṢṃḥēōḻṟṉḵṯ \n]", "", string)
    string = string.strip()
    string = unicode_to_internal_transliteration(string)
    return string


def skt_stemming(text_df):
    chunk_lists = text_df["stemmed"].apply(lambda line: chunk_line(line, 120))
    chunk_exploded = chunk_lists.explode()
    chunk_list = chunk_exploded.tolist()
    tokenizer = spm.SentencePieceProcessor(
        model_file=SKT_STEMMER_LOCATION + "spm/skt-tag8k.model"
    )
    tonenized_chunk_list = tokenizer.encode(chunk_list, out_type=str)
    translator = ctranslate2.Translator(
        SKT_STEMMER_LOCATION + "model/", intra_threads=4, device="cuda"
    )
    transres_exploded = pd.Series(
        translator.translate_batch(tonenized_chunk_list, max_batch_size=48),
        index=chunk_exploded.index,
    )

    # pd.Series.apply: https://towardsdatascience.com/avoiding-apply-ing-yourself-in-pandas-a6ade4569b7f
    transres_exploded = transres_exploded.apply(
        lambda line: tokenizer.decode(line[0]["tokens"])
    )
    # leave only the stems
    transres_exploded = transres_exploded.apply(transres2stemlist)
    text_df[
        "stemmed"
    ] = transres_exploded  # .groupby(chunk_exploded.index).apply(lambda lists:
    # itertools.chain(*lists) )
    return text_df
