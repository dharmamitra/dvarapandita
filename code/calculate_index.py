import pandas as pd 
import numpy as np 
import faiss
import os 

from utils.constants import *
from utils.indexing import CalculateResults
from utils.general import test_if_should_load

FILE_EXTENSION = ".p"
WORDLIST_NAME = "wordlist"

def read_file(path):
    # if there is an error reading the file, return empty DataFrame
    try:
        return pd.read_pickle(path)
    except:
        return pd.DataFrame()
    
def load_files_from_bucket(bucket_path):
    """Load all files from the bucket path and return concatenated DataFrame."""
    files = [
        os.path.join(bucket_path, file)
        for file in os.listdir(bucket_path)
        if file.endswith(FILE_EXTENSION) and WORDLIST_NAME not in file and test_if_should_load(file)
    ]   
    dataframes = (read_file(file) for file in files)
    return pd.concat(dataframes, ignore_index=True)

def save_wordlist(df, bucket_path):
    """Drop vector related columns and save the DataFrame as wordlist."""
    cols_to_drop = ['vectors', 'sumvectors', 'weights']
    df.drop(columns=[col for col in cols_to_drop if col in df], inplace=True)
    df.to_pickle(os.path.join(bucket_path, f"{WORDLIST_NAME}{FILE_EXTENSION}"))

def build_index(total_vectors, index_method):
    """Build and return a FAISS index."""
    dim = total_vectors.shape[1]
    print("VECTOR SHAPE", total_vectors.shape)
    index = faiss.IndexFlatL2(dim)  # flat index
    if index_method == "cpu":
        index = faiss.IndexHNSWFlat(dim, 32)
        index.hnsw.efConstruction = EF_CONSTRUCTION
    elif index_method == "gpu":
        res = faiss.StandardGpuResources()
        index = faiss.index_cpu_to_gpu(res, 0, index)
        
    index.verbose = True
    faiss.normalize_L2(total_vectors)
    index.add(total_vectors)
    print("## ", type(index), " ## ")
    return index

def create_index(bucket_path, index_method="cpu"):
    all_files = load_files_from_bucket(bucket_path)
    total_vectors = np.array(all_files['sumvectors'].tolist(), dtype="float32")
    
    save_wordlist(all_files, bucket_path)
    
    index = build_index(total_vectors, index_method)
    if index_method == "cpu":
        faiss.write_index(index, os.path.join(bucket_path, "vectors.idx"))
    # else:
    return index # wird nur fuer GPU returnt

def run_calculation(bucket_path, lang, index_method, alignment_method):    
    index = create_index(bucket_path, index_method) if index_method == "gpu" else None
    calculator = CalculateResults(bucket_path, lang, index_method, cindex=index, alignment_method=alignment_method)
    calculator.run()
