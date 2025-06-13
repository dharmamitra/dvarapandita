#!/bin/bash

# Function to display usage
usage() {
    echo "Usage: $0 -l <language> -t <task>"
    echo "  -l <language>: Specify the language (e.g., pli, chn)"
    echo "  -t <task>: Specify the task (create_vectorfiles, create_index, get_results, merge_results)"
    exit 1
}

# Parse command line arguments
while getopts "l:t:" opt; do
    case ${opt} in
        l )
            LANG=$OPTARG
            ;;
        t )
            TASK=$OPTARG
            ;;
        \? )
            usage
            ;;
    esac
done

# Check if required parameters are provided
if [ -z "$LANG" ] || [ -z "$TASK" ]; then
    usage
fi

# Buckets should always be a factor of 10. For large collections like Tibetan, Chinese, use 100; Pali and Sanskrit are fine with 10 
NUM_BUCKETS=10

# Define directory paths
TSV_DIR="/tier2/ucb/nehrdich/${LANG}/segments/"
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

# Execute the specified task
case $TASK in
    create_vectorfiles)
        sbatch <<EOF
#!/bin/bash
#SBATCH --partition=xeon
#SBATCH --cpus-per-task=160
#SBATCH --qos=normal
cd /homes/nehrdich/dvarapandita/code/
~/miniconda3/bin/invoke create-vectorfiles --tsv-path=$TSV_DIR --out-path=$WORK_DIR/ --lang=$LANG --threads=160 --bucket-num=$NUM_BUCKETS
EOF
        ;;
    create_index)
        for folder in $WORK_DIR/folder*; do
            sbatch <<EOF
#!/bin/bash
#SBATCH --qos=normal
cd /homes/nehrdich/dvarapandita/code/
~/miniconda3/bin/invoke create-new-index $folder
EOF
        done
        ;;
    get_results)
        for folder in $WORK_DIR/folder*; do
            sbatch <<EOF
#!/bin/bash
#SBATCH --qos=normal
export OMP_WAIT_POLICY=PASSIVE
cd /homes/nehrdich/dvarapandita/code/
~/miniconda3/bin/invoke get-results-from-index --bucket-path $folder/ --lang=$LANG --alignment-method=local --index-method=cpu
EOF
        done
        ;;
    merge_results)
        sbatch <<EOF
#!/bin/bash
#SBATCH --partition=xeon
#SBATCH --cpus-per-task=160
#SBATCH --qos=normal
cd /homes/nehrdich/dvarapandita/code/
~/miniconda3/bin/invoke merge-results-for-db --input-path $WORK_DIR --output-path $OUT_DIR
EOF
        ;;
    *)
        echo "Invalid task specified"
        usage
        ;;
esac

exit 0