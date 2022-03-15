import pandas as pd 
import re
import multiprocessing
import faiss
import os 


def create_index(bucket_path):
    for file in os.listdir(bucket_path):
        if ".p" in file and not "wordlist" in file:            
            file_path = bucket_path + file     
            file_df = pd.read_pickle(file_path)
            vectors_of_current_file = file_df['sumvectors'].tolist()
            
    


    
