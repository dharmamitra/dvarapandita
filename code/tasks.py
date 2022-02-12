from invoke import task

from stemmer import run_stemmer 



@task
def stem_skt(path):
    run_stemmer(path, "skt",num_of_threads=1)
    
@task
def stem_tib(path):
    run_stemmer(path, "tib",num_of_threads=1)

@task
def stem_chn(path):
    run_stemmer(path, "chn",num_of_threads=1)

@task
def stem_pli(path):
    run_stemmer(path, "pli",num_of_threads=1)
