#!/bin/bash

# Set the language variable
LANG=chn

# Toggle variables for each step
RUN_CREATE_VECTORFILES=true
RUN_CREATE_NEW_INDEX=false
RUN_GET_RESULTS=false
RUN_MERGE_RESULTS=false
# Buckets should always be a factor of 10. For the large collections such as Tibetan, Chinese, this should be 100; Pali and Sanskrit are fine with 10 
NUM_BUCKETS=100

# Define directory paths
TSV_DIR="/tier2/ucb/nehrdich/${LANG}/tsv/"
WORK_DIR="/tier2/ucb/nehrdich/${LANG}/work"
OUT_DIR="/tier2/ucb/nehrdich/${LANG}/output/"

if [ "$LANG" = "chn" ]; then
  TXT_DIR="/tier2/ucb/nehrdich/chn/json/"
else
  TXT_DIR="/tier2/ucb/nehrdich/${LANG}/txt/"
fi

# Function to create directory if it does not exist
create_directory() {
    if [ ! -d "$1" ]; then
        mkdir -p "$1"
    fi
}

# Create necessary directories
create_directory "$TSV_DIR"
create_directory "$WORK_DIR"
create_directory "$OUT_DIR"

# Queue a job for creating vector files if toggled
if [ "$RUN_CREATE_VECTORFILES" = true ]; then
    echo '#!/bin/bash    
    #PBS -l select=1:ncpus=160
    cd /homes/nehrdich/dvarapandita/code/
    ~/miniconda3/bin/invoke create-vectorfiles --tsv-path='"$TSV_DIR"' --out-path='"$WORK_DIR/"' --lang='"$LANG"' --threads=160 --bucket-num='"$NUM_BUCKETS" | qsub
fi

if [ "$RUN_CREATE_NEW_INDEX" = true ]; then
    folder_array=()
    count=0
    for i in $WORK_DIR/folder*; do
        folder_array+=("$i")
        ((count++))
        if [ "$count" -eq 10 ]; then
            echo ${folder_array[*]}
            # Generate the PBS script with GNU Parallel command inside
            echo '#!/bin/bash
#PBS -l select=1:ncpus=160
cd /homes/nehrdich/dvarapandita/code/

# Use GNU Parallel to process the folders
parallel -j 10 --will-cite ~/miniconda3/bin/invoke create-new-index {} ::: '"${folder_array[*]}" | qsub &
            # Reset array and count for next batch
            echo sent ${folder_array[*]}
            folder_array=()
            count=0
        fi
    done

    # Submit remaining folders if any
    if [ "$count" -ne 0 ]; then
        echo '#!/bin/bash
#PBS -l select=1:ncpus=160
cd /homes/nehrdich/dvarapandita/code/

# Use GNU Parallel to process the folders
parallel -j 10 --will-cite ~/miniconda3/bin/invoke create-new-index {} ::: '"${folder_array[*]}" | qsub &
    fi
fi


# Queue jobs for processing each folder in WORK_DIR if toggled
# Warning: multithreading is not yet well implemented here and highly inefficient; needs more attention
if [ "$RUN_GET_RESULTS" = true ]; then
    folder_array=()
    count=0
    for i in $WORK_DIR/folder*; do
        folder_array+=("$i")
        ((count++))
        if [ "$count" -eq 10 ]; then
            # Generate the PBS script with GNU Parallel command inside
            echo '#!/bin/bash
#PBS -l select=1:ncpus=160
OMP_WAIT_POLICY=PASSIVE
cd /homes/nehrdich/dvarapandita/code/

# Use GNU Parallel to process the folders
parallel -j 10 --will-cite ~/miniconda3/bin/invoke get-results-from-index --bucket-path {}/ --lang='"$LANG"' --alignment-method=local --index-method=cpu ::: '"${folder_array[*]}" | qsub &

            # Reset array and count for next batch
            folder_array=()
            count=0
        fi
    done

    # Submit remaining folders if any
    if [ "$count" -ne 0 ]; then
        echo '#!/bin/bash
#PBS -l select=1:ncpus=160
OMP_WAIT_POLICY=PASSIVE
cd /homes/nehrdich/dvarapandita/code/

# Use GNU Parallel to process the folders
parallel -j 10 --will-cite ~/miniconda3/bin/invoke get-results-from-index --bucket-path {}/ --lang='"$LANG"' --alignment-method=local --index-method=cpu ::: '"${folder_array[*]}" | qsub &
    fi
fi


# Queue jobs for merging results if toggled
if [ "$RUN_MERGE_RESULTS" = true ]; then
    echo '#!/bin/bash    
    #PBS -l select=1:ncpus=160
    cd /homes/nehrdich/dvarapandita/code/
    ~/miniconda3/bin/invoke merge-results-for-db --input-path '"$WORK_DIR"' --output-path '"$OUT_DIR" | qsub    
fi


exit 0
