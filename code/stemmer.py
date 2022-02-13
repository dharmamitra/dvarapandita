import os 
import pandas as pd
import re
import numpy as np
import multiprocessing
from utils.stemming import *
from utils.constants import *


def write_df(df,path):
    df['segmentnr'] = df["filename"] + ":" + df['line_number']
    # write tsv files in chunks
    for num,chunk in df.groupby(np.arange(len(df))//TEXT_CHUNKSIZE):
        chunk.to_csv(path + "-{}.tsv".format(num), sep='\t',index=False, columns=["segmentnr", "original", "stemmed"])


def stem_file(data):
    path,lang = data
    print("NOW PROCESSING",path)
    cfile = open(path,'r')
    path_short = os.path.splitext(path)[0]
    filenames, line_numbers, lines, cleaned_lines = text2lists(path,lang)    
    text_df = pd.DataFrame({"filename": filenames, "line_number": line_numbers, 'original': lines, "stemmed": cleaned_lines})
    if lang == "skt":
        text_df = skt_stemming(text_df)
    write_df(text_df, path_short)
    

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


