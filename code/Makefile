# first step is stemming
stem-tibetan:
	invoke stem  --path "/home/basti/data/tibetan/txt-cropped/" --lang tib --threads 16

stem-chinese:
	invoke stem  --path "/home/basti/data/chinese/segmented-chinese/files/" --lang chn --threads 16


stem-sanskrit:
	invoke stem  --path "../data-kurt/" --lang skt --threads 16


# second step is vector creation 
create-vectors-tibetan:
	invoke create-vectorfiles --tsv-path="/home/basti/data/tibetan/txt-cropped/" --out-path="../tibetan-work/" --bucket-num 10 --lang "tib" --threads 16


create-vectors-chinese:
	invoke create-vectorfiles --tsv-path="/home/basti/data/chinese/segmented-chinese/tsv-extract/" --out-path="../chinese-work/" --bucket-num 1 --lang "chn" --threads 16

# third step is index creation 
create-index-chn:
	invoke create-new-index "../chinese-work/folder1/" 

# fourth step is match result calculation 
get-results-from-index-chn:
	invoke get-results-from-index --bucket-path "../chinese-work/folder1/" --lang="chn"

# TODO: fifth step: local alignment + creation of database-ready json output
