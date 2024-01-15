from vectorizer import Vectorizer
from file_mngr import FileMngr
import multiprocessing
import os
fm = FileMngr(
    n_buckets=3,
)
lang = "pli"
def vectorize_text(file_path):
    Vectorizer(fm, lang).process_text(file_path)

list_of_paths = fm.get_stemmed_files(lang)
print(os.listdir("../test-data"))
pool = multiprocessing.Pool(processes=2)
pool.map(vectorize_text, list_of_paths)
pool.close()