from random import randint
from utils.vectorizing import *
from utils.constants import *
import multiprocessing
import os
import pandas as pd 
import shutil

#embedder = Embedder()

def create_vec_df(file_df,lang):
    if lang == "eng":        
        sentences = file_df['stemmed'].tolist()        
        vectors = embedder.get_vectors(sentences)
        if len(vectors) != len(sentences):
            print("ERROR: NUMBER OF SENTENCES AND VECTORS DOES NOT MATCH")
        # convert vectors to list of numpy arrays
        vectors = [np.array(vector) for vector in vectors]
        file_df['sumvectors'] = vectors
        return file_df
    else:
        windowsize = WINDOWSIZE[lang]
        vector_model = get_vector_model(lang)
        if lang == "skt":
            file_df['stemmed'] = file_df['stemmed'].apply(split_sanskrit_stem)  # apply(lambda line: line.split())
        else:
            file_df['stemmed'] = file_df['stemmed'].str.split()  # apply(lambda line: line.split())

        vec_df = file_df.explode("stemmed")

        vec_df['weights'] = vec_df['stemmed'].apply(lambda word: get_weight(word,lang))
        vec_df['vectors'] = vec_df['stemmed'].apply(lambda word:
            get_vector(word,vector_model))
        vector_list = vec_df['vectors'].tolist()
        weight_list = vec_df['weights'].tolist()
        vec_df['sumvectors'] = \
            get_sumvectors(vector_list, weight_list, windowsize)
    return vec_df



def create_vectorfile(data):    
    tsv_path,out_path,lang,buckets = data
    print("NOW PROCESSING",tsv_path)
    
    filename = os.path.basename(tsv_path).split('.tsv')[0]
    file_df = pd.read_csv(tsv_path, sep='\t', names=['segmentnr', 'original', 'stemmed'], on_bad_lines="skip").astype(str)
    vec_df = create_vec_df(file_df,lang)
    bucket_number = randint(1,buckets)
    bucket_path = out_path + "folder" + str(bucket_number)

    # if not os.path.isdir(bucket_path):
    #     os.mkdir(bucket_path)
    os.makedirs(bucket_path, exist_ok=True)
    vec_df.to_pickle(bucket_path + "/" + filename + ".p")
    

def create_vectors(tsv_path, out_path, bucket_num, lang, threads):
    list_of_paths = []
    # make sure the buckets are clean
    #shutil.rmtree(out_path)
    #os.mkdir(out_path)
    for cfile in os.listdir(tsv_path):
        filename = os.fsdecode(cfile)
        #print("FILENAME", filename)
        # make sure we only read tsv-files
        if ".tsv" in filename:
            if lang == "eng":
                create_vectorfile([tsv_path+filename, out_path, lang, bucket_num])
            else:
                list_of_paths.append([tsv_path+filename, out_path, lang, bucket_num])

    if lang != "eng":
        pool = multiprocessing.Pool(processes=threads)
        quote_results = pool.map(create_vectorfile, list_of_paths)
        pool.close()


