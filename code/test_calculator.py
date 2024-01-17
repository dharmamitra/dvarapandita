import pandas as pd 
import numpy as np 
import faiss
import os 
from pathlib import Path

from utils.constants import *
from utils.indexing import CalculateResults
from utils.general import test_if_should_load

from calculate_index import create_index

bucket_path = "test-data/pli/vectors/folder0000/"
root_dir = os.path.dirname(os.path.realpath(__file__)) # find the file's dir
path = Path(root_dir).parent / bucket_path

lang = "pli"
index_method = "cpu"
alignment_method="local"

index = create_index(bucket_path, index_method)
calculator = CalculateResults(bucket_path, lang, index_method, cindex=index, alignment_method=alignment_method)

calculator.run()