import os 
import pandas as pd
import sentencepiece as spm
import ctranslate2
import re
import multiprocessing
from utils.stemming import *

def stem_file(data):
    path,lang = data
    print("NOW PROCESSING",path)
    cfile = open(path,'r')
    path_short = os.path.splitext(path)[0]
    segmentnrs, lines, cleaned_lines = text2list(path,lang)
    text_df = pd.DataFrame({'segmentnrs': segmentnrs, 'original': lines, "stemmed": cleaned_lines})
    if lang == "skt":
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
    text_df.to_csv(path_short + ".tsv", sep='\t')

def run_stemmer(path,lang,num_of_threads):
    list_of_paths = []
    for cfile in os.listdir(path):
        filename = os.fsdecode(cfile)
        # make sure we only read txt-files
        if ".txt" in filename:
            list_of_paths.append([path+filename,lang])
    pool = multiprocessing.Pool(processes=num_of_threads)
    quote_results = pool.map(stem_file, list_of_paths)
    pool.close()
# remove this once tasks/Makefile is working
run_stemmer("../test/","tib",1)    
