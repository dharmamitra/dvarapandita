# first step is stemming
stem-tibetan:
	invoke stem  --path "/mnt/code/dvarapandita/data/tib/" --lang tib --threads 16

stem-chinese:
	invoke stem  --path "/home/basti/data/chinese/segmented-chinese/files/" --lang chn --threads 16


stem-sanskrit:
	invoke stem  --path "../data-vedic/txt/" --lang skt --threads 4

prepare-english:
	invoke stem  --path "../data/tib-eng/" --lang eng --threads 16

# second step is vector creation 
create-vectors-tibetan:
	invoke create-vectorfiles --tsv-path="../data/tib/" --out-path="../work/tibetan/" --bucket-num 1  --lang "tib" --threads 16

create-vectors-sanskrit:
	invoke create-vectorfiles --tsv-path="../data-vedic/tsv/" --out-path="../vedic-work/" --bucket-num 1 --lang "skt" --threads 12

create-vectors-chinese:
	invoke create-vectorfiles --tsv-path="/home/basti/data/chinese/segmented-chinese/tsv-extract/" --out-path="../chinese-work/" --bucket-num 1 --lang "chn" --threads 16

create-vectors-english:
	invoke create-vectorfiles --tsv-path="../data/tib-eng/" --out-path="../work/tib-eng/" --bucket-num 1 --lang "eng" --threads 1


# third step is index creation; this we only do for HNSW on CPU; on GPU, we construct and use the index directly 
create-index-chn:
	invoke create-new-index "../chinese-work/folder1/" 

create-index-tib:
	invoke create-new-index "../work/tibetan/folder1/" 

create-index-skt:
	invoke create-new-index "../vedic-work/folder1/" 

create-index-eng:
	invoke create-new-index "../work/tib-eng/folder1/"

# fourth step is match result calculation
get-results-from-index-chn:
	invoke get-results-from-index --bucket-path "../chinese-work/folder1/" --lang="chn" --alignment-method="local" --index-method="cpu"

get-results-from-index-tib:
	invoke get-results-from-index --bucket-path "../work/tibetan/folder1/" --lang="tib" --alignment-method="local" --index-method="cpu"

get-results-from-index-skt:
	invoke get-results-from-index --bucket-path "../vedic-work/folder1/" --lang="skt" --alignment-method="local" --index-method="cpu"

get-results-from-index-eng:
	invoke get-results-from-index --bucket-path "../work/tib-eng/folder1/" --lang="eng" --index-method="gpu" --alignment-method="sentence"


