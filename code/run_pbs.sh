#!/bin/bash

# Set the language variable
LANG=tib

# Toggle variables for each step
RUN_CREATE_VECTORFILES=false
RUN_CREATE_NEW_INDEX=false
RUN_GET_RESULTS=false
RUN_MERGE_RESULTS=false
RUN_CALCULATE_STATS=true
NUM_BUCKETS=10

# Define directory paths
TXT_DIR="/tier2/ucb/nehrdich/${LANG}/txt/"
TSV_DIR="/tier2/ucb/nehrdich/${LANG}/tsv/"
WORK_DIR="/tier2/ucb/nehrdich/${LANG}/work"
OUT_DIR="/tier2/ucb/nehrdich/${LANG}/output/"


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
    cd /homes/nehrdich/dvarapandita-code/code/
    ~/miniconda3/bin/invoke create-vectorfiles --tsv-path='"$TSV_DIR"' --out-path='"$WORK_DIR/"' --lang='"$LANG"' --threads=160 --bucket-num='"$NUM_BUCKETS" | qsub
fi

if [ "$RUN_CREATE_NEW_INDEX" = true ]; then
    for i in $WORK_DIR/folder*; do
        echo '#!/bin/bash    
        #PBS -l select=1:ncpus=160        
        cd /homes/nehrdich/dvarapandita-code/code/
        ~/miniconda3/bin/invoke create-new-index '"$i" | qsub &
    done
fi

# Queue jobs for processing each folder in WORK_DIR if toggled
# Warning: multithreading is not yet well implemented here and highly inefficient; needs more attention
if [ "$RUN_GET_RESULTS" = true ]; then
    for i in $WORK_DIR/folder2; do
        echo '#!/bin/bash    
        #PBS -l select=1:ncpus=160
        OMP_WAIT_POLICY=PASSIVE 
        OMP_NUM_THREADS=1
        cd /homes/nehrdich/dvarapandita-code/code/
        ~/miniconda3/bin/invoke get-results-from-index --bucket-path '"$i/"' --lang='"$LANG"' --alignment-method=local --index-method=cpu' | qsub &
    done
fi

# Queue jobs for merging results if toggled
if [ "$RUN_MERGE_RESULTS" = true ]; then
    echo '#!/bin/bash    
    #PBS -l select=1:ncpus=160
    cd /homes/nehrdich/dvarapandita-code/code/
    ~/miniconda3/bin/invoke merge-results-for-db --input-path '"$WORK_DIR"' --output-path '"$OUT_DIR" | qsub
fi

# Queue jobs for calculating stats if toggled
if [ "$RUN_CALCULATE_STATS" = true ]; then
    echo '#!/bin/bash    
    #PBS -l select=1:ncpus=160
    cd /homes/nehrdich/dvarapandita-code/code/
    ~/miniconda3/bin/invoke calculate-stats --output-path '"$OUT_DIR" | qsub
fi

exit 0
