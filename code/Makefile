TEST_DIR		:= /home/wo/bn/dvarapandita/test-data/tib
TEST_ORIG_RAW	:= ${TEST_DIR}/original-raw/
TEST_ORIG_STEM	:= ${TEST_DIR}/original-stemmed/
# TEST_ORIG_VEC	:= ${TEST_DIR}/original-vecs/ # do not have to be saved if tested with hash

TEST_NEW_STEM	:= ${TEST_DIR}/testing-stemmed/
TEST_NEW_VEC	:= ${TEST_DIR}/original-stemmed/ # should be changed to /testing-vecs, ${TEST_DIR}/orig_vectors.chk has to be hashed

RED		:= '\033[0;31m'
GREEN	:= '\033[0;32m'
NC		:= '\033[0m' # No Color

test-all: test-stem-test test-vectors-tibetan

test-stem-test:
	@rm -rf ${TEST_NEW_STEM}
	@DP_TESTMODE=1 \
	DP_TEST_STEMMED=${TEST_STEMMED} \
	invoke stem  --path ${TEST_ORIG_RAW} --lang tib --threads 16 > /dev/null
	@if diff ${TEST_ORIG_STEM} ${TEST_NEW_STEM} ; then \
		echo ${GREEN}"✅ STEMMING TEST PASSED" ${NC}; \
	else \
		echo -e ${RED}"🔥 STEMMING TEST FAILED" ${NC}; \
	fi
	@rm -rf ${TEST_NEW_STEM}

test-vectors-tibetan:
	@# invoke create-vectorfiles --tsv-path="${TEST_ORIG_STEM}" --out-path="${TEST_NEW_VEC}" --bucket-num 1  --lang "tib" --threads 16
	@if cd ${TEST_NEW_VEC} && md5sum --check ${TEST_DIR}/orig_vectors.chk > /dev/null ; then \
		echo ${GREEN}"✅ VECTORIZATION TEST PASSED" ${NC}; \
	else \
		echo -e ${RED}"🔥 VECTORIZATION TEST FAILED" ${NC}; \
	fi
	@rm -rf ${TEST_NEW_STEM}

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
	invoke create-vectorfiles --tsv-path="../data/bo/segments/" --out-path="../work/bo/" --bucket-num 1  --lang "tib" --threads 24

create-vectors-sanskrit:
	invoke create-vectorfiles --tsv-path="../data/sa/segments/" --out-path="../work/sa/" --bucket-num 1 --lang "skt" --threads 12

create-vectors-chinese:
	invoke create-vectorfiles --tsv-path="../data/zh/segments/" --out-path="../work/sa/" --bucket-num 1 --lang "chn" --threads 16

create-vectors-pali:
	invoke create-vectorfiles --tsv-path="../data/pa/segments/" --out-path="../work/pa/" --bucket-num 1 --lang "pli" --threads 16


create-vectors-english:
	invoke create-vectorfiles --tsv-path="../data/tib-eng/" --out-path="../work/tib-eng/" --bucket-num 1 --lang "eng" --threads 1


# third step is index creation; this we only do for HNSW on CPU; on GPU, we construct and use the index directly 
create-index-chn:
	invoke create-new-index "../chinese-work/folder1/" 

create-index-tib:
	invoke create-new-index "../work/bo/folder1/" 

create-index-skt:
	invoke create-new-index "../work/sa/folder1/" 

create-index-pli:
	invoke create-new-index "../work/pa/folder1/" 


create-index-eng:
	invoke create-new-index "../work/tib-eng/folder1/"

# fourth step is match result calculation
get-results-from-index-chn:
	invoke get-results-from-index --bucket-path "../chinese-work/folder1/" --lang="chn" --alignment-method="local" --index-method="cpu"

get-results-from-index-tib:
	invoke get-results-from-index --bucket-path "../work/bo/folder1/" --lang="tib" --alignment-method="local" --index-method="cpu"

get-results-from-index-skt:
	invoke get-results-from-index --bucket-path "../work/sa/folder1/" --lang="pli" --alignment-method="local" --index-method="cpu"

get-results-from-index-pli:
	invoke get-results-from-index --bucket-path "../work/pa/folder1/" --lang="pli" --alignment-method="local" --index-method="cpu"

get-results-from-index-eng:
	invoke get-results-from-index --bucket-path "../work/tib-eng/folder1/" --lang="eng" --index-method="gpu" --alignment-method="sentence"


