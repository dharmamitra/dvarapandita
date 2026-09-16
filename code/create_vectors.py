from random import randint
from utils.vectorizing import *
from utils.constants import *
from utils.stemming_tib import prepare_tib
import multiprocessing
import os
import pandas as pd
import numpy as np
import pickle
from sklearn.decomposition import PCA

#embedder = Embedder()

_G_PCA_MODEL = None


def _pca_output_path(out_path):
    return os.path.join(out_path.rstrip(os.sep), "pca_model.pkl")


def apply_pca_to_vec_df(vec_df, pca):
    """Replace sumvectors with PCA-transformed rows (float32)."""
    mat = np.stack([np.asarray(v, dtype=np.float32) for v in vec_df["sumvectors"].values])
    reduced = pca.transform(mat)
    out = vec_df.copy()
    out["sumvectors"] = [row for row in reduced.astype(np.float32)]
    return out


def collect_sumvectors_sample(json_path, lang, max_samples):
    """Stack raw sumvectors from JSON inputs (no PCA) for fitting PCA."""
    rows = []
    json_files = sorted(
        f for f in os.listdir(json_path) if f.endswith(".json")
    )
    for filename in json_files:
        if len(rows) >= max_samples:
            break
        path = os.path.join(json_path, filename)
        file_df = pd.read_json(path).astype(str)
        vec_df = create_vec_df(file_df, lang)
        vecs = np.stack(vec_df["sumvectors"].values)
        need = max_samples - len(rows)
        if len(vecs) <= need:
            rows.extend(list(vecs))
        else:
            rows.extend(list(vecs[:need]))
            break
    if not rows:
        raise ValueError("No training vectors collected for PCA (empty or missing JSON inputs).")
    return np.asarray(rows, dtype=np.float64)


def fit_pca_model(X, reduction_factor):
    n_features = X.shape[1]
    n_comp = max(1, int(round(n_features / float(reduction_factor))))
    n_comp = min(n_comp, n_features, X.shape[0])
    pca = PCA(n_components=n_comp, random_state=0)
    pca.fit(X)
    return pca


def create_vec_df(file_df, lang):
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
        if lang == "tib":
            file_df['analyzed'] = file_df['analyzed'].apply(prepare_tib).str.split()
        else:
            file_df['analyzed'] = file_df['analyzed'].str.split()  # apply(lambda line: line.split())

        vec_df = file_df.explode("analyzed")
        vec_df = vec_df.dropna(subset=["analyzed"])

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
    if _G_PCA_MODEL is not None:
        vec_df = apply_pca_to_vec_df(vec_df, _G_PCA_MODEL)
    bucket_number = randint(1,buckets)
    bucket_path = out_path + "folder" + str(bucket_number)

    # if not os.path.isdir(bucket_path):
    #     os.mkdir(bucket_path)
    os.makedirs(bucket_path, exist_ok=True)
    vec_df.to_pickle(bucket_path + "/" + filename + ".p")
    

def _init_worker_pca(pca_path):
    global _G_PCA_MODEL
    if pca_path:
        with open(pca_path, "rb") as f:
            _G_PCA_MODEL = pickle.load(f)
    else:
        _G_PCA_MODEL = None


def create_vectors(
    json_path,
    out_path,
    bucket_num,
    lang,
    threads,
    pca_reduction_factor=None,
    pca_max_samples=100000,
    pca_model_path=None,
):
    """
    Build vector pickles. Optional PCA to reduce embedding size.

    - pca_reduction_factor: fit PCA on a sample of corpus vectors; output dim is
      round(embed_dim / factor). Saves pca_model.pkl under out_path.
    - pca_model_path: load a fitted PCA (e.g. from index build) so query vectors
      match the index. When set, pca_reduction_factor is ignored.
    """
    global _G_PCA_MODEL
    os.makedirs(out_path, exist_ok=True)

    pca_path_resolved = None
    if pca_model_path:
        with open(pca_model_path, "rb") as f:
            _G_PCA_MODEL = pickle.load(f)
        pca_path_resolved = os.path.abspath(pca_model_path)
        print(f"Loaded PCA from {pca_path_resolved} (n_components={_G_PCA_MODEL.n_components_})")
    elif pca_reduction_factor is not None:
        if float(pca_reduction_factor) <= 0:
            raise ValueError("pca_reduction_factor must be positive.")
        print("Collecting vectors for PCA fitting...")
        X = collect_sumvectors_sample(json_path, lang, pca_max_samples)
        print(f"Fitting PCA on {X.shape[0]} vectors, dim {X.shape[1]}...")
        _G_PCA_MODEL = fit_pca_model(X, pca_reduction_factor)
        out_pca = _pca_output_path(out_path)
        with open(out_pca, "wb") as f:
            pickle.dump(_G_PCA_MODEL, f)
        pca_path_resolved = os.path.abspath(out_pca)
        print(f"Saved PCA to {pca_path_resolved} (n_components={_G_PCA_MODEL.n_components_})")
    else:
        _G_PCA_MODEL = None

    list_of_paths = []
    for cfile in os.listdir(json_path):
        filename = os.fsdecode(cfile)
        if ".json" in filename:
            if lang == "eng":
                create_vectorfile([json_path+filename, out_path, lang, bucket_num])
            else:
                list_of_paths.append([json_path+filename, out_path, lang, bucket_num])

    if lang != "eng":
        initargs = (pca_path_resolved,) if pca_path_resolved else (None,)
        pool = multiprocessing.Pool(
            processes=threads,
            initializer=_init_worker_pca,
            initargs=initargs,
        )
        pool.map(create_vectorfile, list_of_paths)
        pool.close()
        pool.join()

    _G_PCA_MODEL = None

