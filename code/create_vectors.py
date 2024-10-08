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
        sentences = file_df['analyzed'].tolist()        
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
            file_df['analyzed'] = file_df['analyzed'].apply(split_sanskrit_stem)  # apply(lambda line: line.split())
        else:
            file_df['analyzed'] = file_df['analyzed'].str.split()  # apply(lambda line: line.split())

        vec_df = file_df.explode("analyzed")

        vec_df['weights'] = vec_df['analyzed'].apply(lambda word: get_weight(word,lang))
        vec_df['vectors'] = vec_df['analyzed'].apply(lambda word:
            get_vector(word,vector_model))
        vector_list = vec_df['vectors'].tolist()
        weight_list = vec_df['weights'].tolist()
        vec_df['sumvectors'] = \
            get_sumvectors(vector_list, weight_list, windowsize)
    return vec_df



def create_vectorfile(data):    
    json_path,out_path,lang,buckets = data
    print("NOW PROCESSING",json_path)
    
    filename = os.path.basename(json_path).split('.json')[0]
    file_df = pd.read_json(json_path).astype(str)
    vec_df = create_vec_df(file_df,lang)
    bucket_number = randint(1,buckets)
    bucket_path = out_path + "folder" + str(bucket_number)

    # if not os.path.isdir(bucket_path):
    #     os.mkdir(bucket_path)
    os.makedirs(bucket_path, exist_ok=True)
    vec_df.to_pickle(bucket_path + "/" + filename + ".p")
    

def create_vectors(json_path, out_path, bucket_num, lang, threads):
    list_of_paths = []
    for cfile in os.listdir(json_path):
        filename = os.fsdecode(cfile)
        if ".json" in filename:
            if lang == "eng":
                create_vectorfile([json_path+filename, out_path, lang, bucket_num])
            else:
                list_of_paths.append([json_path+filename, out_path, lang, bucket_num])

    if lang != "eng":
        pool = multiprocessing.Pool(processes=threads)
        quote_results = pool.map(create_vectorfile, list_of_paths)
        pool.close()


