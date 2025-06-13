#!/bin/bash

# Function to display usage
usage() {
    echo "Usage: $0 -l <language> -m <mode>"
    echo "  -l <language>: Specify the language (e.g., pli, chn)"
    echo "  -m <mode>: Specify the mode (create_vectorfiles, create_new_index, get_results, merge_results)"
    exit 1
}

# Parse command line arguments
while getopts "l:m:" opt; do
    case ${opt} in
        l )
            LANG=$OPTARG
            ;;
        m )
            MODE=$OPTARG
            ;;
        \? )
            usage
            ;;
    esac
done

# Check if required parameters are provided
if [ -z "$LANG" ] || [ -z "$MODE" ]; then
    usage
fi

# Buckets should always be a factor of 10. For large collections like Tibetan, Chinese, use 100; Pali and Sanskrit are fine with 10 
NUM_BUCKETS=10
[ "$LANG" = "chn" -o "$LANG" = "tib" ] && NUM_BUCKETS=100

# Define directory paths
TSV_DIR="/tier2/ucb/nehrdich/${LANG}/segments/"
WORK_DIR="/tier2/ucb/nehrdich/${LANG}/work"
OUT_DIR="/tier2/ucb/nehrdich/${LANG}/output/"
TXT_DIR="/tier2/ucb/nehrdich/${LANG}/txt/"
[ "$LANG" = "chn" ] && TXT_DIR="/tier2/ucb/nehrdich/chn/json/"

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

# Execute the specified mode
case $MODE in
    create_vectorfiles)
        echo '#!/bin/bash    
#PBS -l select=1:ncpus=160
#PBS -N '"${LANG}_create_vectorfiles"'
cd /homes/nehrdich/dvarapandita/code/
~/miniconda3/bin/invoke create-vectorfiles --tsv-path='"$TSV_DIR"' --out-path='"$WORK_DIR/"' --lang='"$LANG"' --threads=160 --bucket-num='"$NUM_BUCKETS" | qsub
        ;;
    create_new_index)
        for i in $WORK_DIR/folder*; do
            folder_array+=("$i")
            ((count++))
            if [ "$count" -eq 10 ]; then
                echo '#!/bin/bash
#PBS -l select=1:ncpus=160
#PBS -N '"${LANG}_create_new_index"'
cd /homes/nehrdich/dvarapandita/code/
parallel -j 10 --will-cite ~/miniconda3/bin/invoke create-new-index {} ::: '"${folder_array[*]}" | qsub &
                folder_array=()
                count=0
            fi
        done
        if [ "$count" -ne 0 ]; then
            echo '#!/bin/bash
#PBS -l select=1:ncpus=160
#PBS -N '"${LANG}_create_new_index_remaining"'
cd /homes/nehrdich/dvarapandita/code/
parallel -j 10 --will-cite ~/miniconda3/bin/invoke create-new-index {} ::: '"${folder_array[*]}" | qsub &
        fi
        ;;
    get_results)
        for i in $WORK_DIR/folder*; do
            folder_array+=("$i")
            ((count++))
            if [ "$count" -eq 10 ]; then
                echo '#!/bin/bash
#PBS -l select=1:ncpus=160
#PBS -N '"${LANG}_get_results"'
OMP_WAIT_POLICY=PASSIVE
cd /homes/nehrdich/dvarapandita/code/
parallel -j 10 --will-cite ~/miniconda3/bin/invoke get-results-from-index --bucket-path {}/ --lang='"$LANG"' --alignment-method=local --index-method=cpu ::: '"${folder_array[*]}" | qsub &
                folder_array=()
                count=0
            fi
        done
        if [ "$count" -ne 0 ]; then
            echo '#!/bin/bash
#PBS -l select=1:ncpus=160
#PBS -N '"${LANG}_get_results_remaining"'
OMP_WAIT_POLICY=PASSIVE
cd /homes/nehrdich/dvarapandita/code/
parallel -j 10 --will-cite ~/miniconda3/bin/invoke get-results-from-index --bucket-path {}/ --lang='"$LANG"' --alignment-method=local --index-method=cpu ::: '"${folder_array[*]}" | qsub &
        fi
        ;;
    merge_results)
        echo '#!/bin/bash    
#PBS -l select=1:ncpus=160
#PBS -N '"${LANG}_merge_results"'
cd /homes/nehrdich/dvarapandita/code/
~/miniconda3/bin/invoke merge-results-for-db --input-path '"$WORK_DIR"' --output-path '"$OUT_DIR" | qsub
        ;;
    *)
        echo "Invalid mode specified"
        usage
        ;;
esac

exit 0