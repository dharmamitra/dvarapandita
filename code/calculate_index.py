import pandas as pd 
import numpy as np 
import re
import multiprocessing
import faiss
import os 

efConstruction = 40 # higher = more accuracy; 40 is a good default

def create_index(bucket_path):
    global total_vectors
    all_files = pd.DataFrame()
    for file in os.listdir(bucket_path):
        if ".p" in file and not "wordlist" in file:            
            file_path = bucket_path + file     
            file_df = pd.read_pickle(file_path)
            all_files = pd.concat([all_files,file_df])
    total_vectors = np.array(all_files['sumvectors'].tolist(),dtype="float32")

    # wordlist is used in conjunction with the index 
    wordlist = all_files.drop(["vectors","sumvectors",'weights'],axis=1)
    wordlist.to_pickle(bucket_path + "wordlist.p")

    # build the index
    dim = total_vectors.shape[1]
    index = faiss.IndexHNSWFlat(dim, 32)
    index.hnsw.efConstruction = efConstruction # 40 is default, higher = more accuracy 
    index.verbose = True
    faiss.normalize_L2(total_vectors)
    index.add(total_vectors)
    faiss.write_index(index, bucket_path + "vectors.idx")

def calculate_results(bucket_path):
    main_path = re.sub("folder.*","",path)
    index = faiss.read_index(path + "vectors.idx")

    for directory in os.listdir(main_path):
        process_folder(main_path+directory,bucket_path)
        
    


    
create_index("../tibetan-work/folder1/")
    


    
