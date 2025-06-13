#!/bin/bash
#SBATCH --partition=xeon
#SBATCH --time=24:00:00
#SBATCH --mem=450G
#SBATCH --job-name=create_index
#SBATCH --output=index_%A_%a.log
#SBATCH --array=0-9

module load mpi  # Adjust based on your cluster setup

folders=(/tier2/ucb/nehrdich/skt/work/folder*)
folder=${folders[$SLURM_ARRAY_TASK_ID]}

mpiexec -n 1 invoke create-new-index "$folder"
