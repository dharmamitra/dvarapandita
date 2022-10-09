# first step is stemming
stem-tibetan:
	invoke stem  --path "/home/basti/data/tibetan/txt-exp/" --lang tib --threads 16

stem-chinese:
	invoke stem  --path "/home/basti/data/chinese/segmented-chinese/files/" --lang chn --threads 16


stem-sanskrit:
	invoke stem  --path "../data-kurt/" --lang skt --threads 16


# second step is vector creation 
create-vectors-tibetan:
	invoke create-vectorfiles --tsv-path="/home/basti/data/tibetan/txt-exp/" --out-path="../tibetan-work/" --bucket-num 1 --lang "tib" --threads 16

create-vectors-sanskrit:
	invoke create-vectorfiles --tsv-path="../data-vedic/tsv/" --out-path="../vedic-work/" --bucket-num 1 --lang "skt" --threads 12

create-vectors-chinese:
	invoke create-vectorfiles --tsv-path="/home/basti/data/chinese/segmented-chinese/tsv-extract/" --out-path="../chinese-work/" --bucket-num 1 --lang "chn" --threads 16

# third step is index creation 
create-index-chn:
	invoke create-new-index "../chinese-work/folder1/" 

create-index-tib:
	invoke create-new-index "../tibetan-work/folder1/" 

create-index-skt:
	invoke create-new-index "../vedic-work/folder1/" 


# fourth step is match result calculation 
get-results-from-index-chn:
	invoke get-results-from-index --bucket-path "../chinese-work/folder1/" --lang="chn"

get-results-from-index-tib:
	invoke get-results-from-index --bucket-path "../tibetan-work/folder1/" --lang="tib"

get-results-from-index-skt:
	invoke get-results-from-index --bucket-path "../vedic-work/folder1/" --lang="tib"


# fifth and last step is merging the results
merge-results-tib:
	invoke merge-results --bucket-path "../tibetan-work/folder1/" --lang="tib"


# TODO: fifth step: local alignment + creation of database-ready json output
