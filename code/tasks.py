from invoke import task

from stemmer import run_stemmer 
from create_vectors import create_vectors
from calculate_index import create_index, run_calculation
from merge_matches_exp import collect_matches_from_folder_exp


@task
def stem(c, path, lang, threads=1):
    run_stemmer(path, lang,num_of_threads=threads)    

@task
def create_vectorfiles(
    c,
    tsv_path,
    out_path,
    lang,
    bucket_num=1,
    threads=1,
    pca_reduction_factor=None,
    pca_max_samples=100000,
    pca_model_path=None,
):
    create_vectors(
        tsv_path,
        out_path,
        bucket_num,
        lang,
        threads,
        pca_reduction_factor=pca_reduction_factor,
        pca_max_samples=pca_max_samples,
        pca_model_path=pca_model_path,
    )
    
@task
def get_results_from_index(c, bucket_path, lang, index_method, alignment_method, src_pattern=None, tgt_pattern=None, threads=16, load_workers=None, file_batch_size=10000):
    """
    src_pattern: only query .p files whose basename contains this substring.
    tgt_pattern: only index .p files whose basename contains this substring
                 (applies when index_method='gpu' builds the index in-process).
    """
    run_calculation(bucket_path, lang, index_method, alignment_method, src_pattern=src_pattern, tgt_pattern=tgt_pattern, num_processes=threads, load_workers=load_workers, file_batch_size=file_batch_size)

@task
def create_new_index(c, bucket_path, load_workers=None, file_batch_size=10000, tgt_pattern=None):
    """tgt_pattern: only index .p files whose basename contains this substring."""
    create_index(bucket_path, load_workers=load_workers, file_batch_size=file_batch_size, tgt_pattern=tgt_pattern)

@task
def merge_results_for_db(c, input_path, output_path, threads=0):
    """Merge work/matches into per-text <name>.ndjson.gz files plus
    stats/global_stats.json.gz under output_path (DharmaNexus package).

    threads<=0: use all CPUs; else multiprocessing pool size.
    """
    print(input_path)
    print(output_path)
    nproc = None if threads is None or threads <= 0 else int(threads)
    collect_matches_from_folder_exp(input_path, output_path, num_processes=nproc)

@task
def merge_results_for_db_exp(c, input_path, output_path, threads=0):
    """Alias of merge-results-for-db, kept for existing run scripts."""
    merge_results_for_db(c, input_path, output_path, threads=threads)

@task
def flag_match_types(c, matches_path, lang, state_path, threads=32,
                     min_count=25, n_label=20000, model=None,
                     secrets_env=None, tau=0.7):
    """Add match_type (boilerplate category) to every match ndjson.gz.

    Run after merge-results-for-db. Needs GEMINI_API_KEY (or --secrets-env)
    the first time; later runs reuse the cached labels/model in state_path.
    """
    cmd = (f"python3 flag_match_types.py --matches-dir {matches_path} "
           f"--lang {lang} --state-dir {state_path} --threads {threads} "
           f"--min-count {min_count} --n-label {n_label} --tau {tau}")
    if model:
        cmd += f" --model {model}"
    if secrets_env:
        cmd += f" --secrets-env {secrets_env}"
    c.run(cmd)

