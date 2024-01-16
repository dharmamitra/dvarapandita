import pandas as pd 
import numpy as np 
import faiss
import os 

from utils.constants import *
from utils.indexing import CalculateResults
from utils.general import test_if_should_load

from calculate_index import create_index

bucket_path1 = "/home/wo/bn/dvarapandita/test-data/pli/vectors/bucket_/"
bucket_path2 = "/home/wo/bn/dvarapandita/test-data/pli/vectors/"
lang = "pli"
index_method = "cpu"
alignment_method="local"

index = create_index(bucket_path1, index_method)
calculator = CalculateResults(bucket_path2, lang, index_method, cindex=index, alignment_method=alignment_method)

calculator.run()