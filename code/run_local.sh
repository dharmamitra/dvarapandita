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

# Define directory paths (modified for local use)
TSV_DIR="/tier2/ucb/nehrdich/${LANG}/segments/"
WORK_DIR="/tier2/ucb/nehrdich/${LANG}/work"
OUT_DIR="/tier2/ucb/nehrdich/${LANG}/output/"
TXT_DIR="/tier2/ucb/nehrdich/${LANG}/txt/"
[ "$LANG" = "chn" ] && TXT_DIR="./data/chn/json/"

# ... existing directory creation code ...

# Execute the specified mode
case $MODE in
    create_vectorfiles)
        invoke create-vectorfiles --tsv-path="$TSV_DIR" --out-path="$WORK_DIR/" --lang="$LANG" --threads=8 --bucket-num="$NUM_BUCKETS"
        ;;
    create_new_index)
        folders=($WORK_DIR/folder*)
        
        for folder in "${folders[@]}"; do
            mpiexec -n 1 invoke create-new-index "$folder" &
        done
        wait
        ;;
    get_results)
        folders=($WORK_DIR/folder*)
        export OMP_WAIT_POLICY=PASSIVE

        for folder in "${folders[@]}"; do
            mpiexec -n 1 python -m mpi4py ~/miniconda3/bin/invoke get-results-from-index \
                --bucket-path="$folder/" \
                --lang="$LANG" \
                --alignment-method=local \
                --index-method=cpu &
        done
        wait
        ;;
    merge_results)
        invoke merge-results-for-db --input-path="$WORK_DIR" --output-path="$OUT_DIR"
        ;;
esac

exit 0