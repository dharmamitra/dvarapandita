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

# Define directory paths
TSV_DIR="/tier2/ucb/nehrdich/${LANG}/segments/"
WORK_DIR="/tier2/ucb/nehrdich/${LANG}/work/"
OUT_DIR="/tier2/ucb/nehrdich/${LANG}/output/"
TXT_DIR="/tier2/ucb/nehrdich/${LANG}/txt/"
[ "$LANG" = "chn" ] && TXT_DIR="./data/chn/json/"

# SLURM configuration
SLURM_PARTITION="xeon"  # Adjust according to your cluster
SLURM_TIME="24:00:00"     # Adjust time limit as needed
SLURM_MEM="450G"          # Adjust memory as needed

# Execute the specified mode
case $MODE in
    create_vectorfiles)
        echo '#!/bin/bash    
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=160
#SBATCH --job-name='"${LANG}_create_vectorfiles"'
cd /homes/nehrdich/dvarapandita/code/
mpiexec ~/miniconda3/bin/invoke create-vectorfiles --tsv-path='"$TSV_DIR"' --out-path='"$WORK_DIR/"' --lang='"$LANG"' --threads=160 --bucket-num='"$NUM_BUCKETS"'' | sbatch
        ;;
    create_new_index)
        folders=(${WORK_DIR}/folder*)
        total_folders=${#folders[@]}
        folders_per_task=10
        
        for ((i=0; i<total_folders; i+=folders_per_task)); do
            folder_list=""
            # Build list of folders for this task
            for ((j=i; j<i+folders_per_task && j<total_folders; j++)); do
                folder_list+="\"${folders[j]}\" "
            done
            
            echo '#!/bin/bash
#SBATCH --partition='"${SLURM_PARTITION}"'
#SBATCH --time='"${SLURM_TIME}"'
#SBATCH --mem='"${SLURM_MEM}"'
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=160
#SBATCH --job-name='"${LANG}_create_new_index_${i}"'
cd /homes/nehrdich/dvarapandita/code/

export OMP_NUM_THREADS=16  # Reduced since we have fewer folders per task

for folder in '"$folder_list"'; do
    ~/miniconda3/bin/invoke create-new-index "$folder" &
done
wait' | sbatch
        done
        ;;
    get_results)
        folders=(${WORK_DIR}/folder*)
        total_folders=${#folders[@]}
        folders_per_task=10
        
        for ((i=0; i<total_folders; i+=folders_per_task)); do
            folder_list=""
            # Build list of folders for this task
            for ((j=i; j<i+folders_per_task && j<total_folders; j++)); do
                folder_list+="\"${folders[j]}\" "
            done
            
            echo '#!/bin/bash
#SBATCH --partition='"${SLURM_PARTITION}"'
#SBATCH --time='"${SLURM_TIME}"'
#SBATCH --mem='"${SLURM_MEM}"'
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=160
#SBATCH --job-name='"${LANG}_get_results_${i}"'
cd /homes/nehrdich/dvarapandita/code/

export OMP_WAIT_POLICY=PASSIVE
export OMP_NUM_THREADS=16

for folder in '"$folder_list"'; do
    ~/miniconda3/bin/invoke get-results-from-index \
        --bucket-path="$folder/" \
        --lang="'"$LANG"'" \
        --alignment-method=local \
        --index-method=cpu &
done
wait' | sbatch
        done
        ;;
    merge_results)
        sbatch <<EOT
#!/bin/bash
#SBATCH --partition=${SLURM_PARTITION}
#SBATCH --time=${SLURM_TIME}
#SBATCH --mem=${SLURM_MEM}
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --job-name=merge_results
#SBATCH --output=merge_%j.log

invoke merge-results-for-db-exp --input-path="$WORK_DIR" --output-path="$OUT_DIR"
EOT
        ;;
esac

exit 0