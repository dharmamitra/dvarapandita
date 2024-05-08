from invoke import task

from stemmer import run_stemmer 
from create_vectors import create_vectors
from calculate_index import create_index, run_calculation
from merge_stats import collect_stats_from_folder


@task
def stem(c, path, lang, threads=1):
    run_stemmer(path, lang,num_of_threads=threads)    

@task
def create_vectorfiles(c, tsv_path, out_path, lang, bucket_num=1, threads=1 ):
    create_vectors(tsv_path, out_path, bucket_num, lang, threads)
    
@task
def get_results_from_index(c, bucket_path, lang, index_method, alignment_method):
    run_calculation(bucket_path, lang, index_method, alignment_method)

@task
def create_new_index(c, bucket_path):
    create_index(bucket_path)

@task
def merge_results_for_db(c, input_path, output_path):
    collect_stats_from_folder(input_path, output_path)

    
    
