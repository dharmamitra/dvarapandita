
#!/bin/bash
# Do not forget to select a proper partition if the default
# one is no fit for the job! You can do that either in the sbatch
# command line or here with the other settings.
#SBATCH --job-name=sanskrit
#SBATCH --nodes=2
#SBATCH --time=1:00:00
#SBATCH --partition=std
#SBATCH --tasks-per-node=1
# Never forget that! Strange happenings ensue otherwise.
#SBATCH --export=NONE
#SBATCH --mem=64gb
#SBATCH --output=sanskrit_slurm_%j.log
set -e # Good Idea to stop operation on first error.

source /sw/batch/init.sh
source ~/.profile
# Load environment modules for your application here.

# Actual work starting here. You might need to call
# srun or mpirun depending on your type of application

#for i in /work/ftsx015/tib/work/folder*; do srun --time=11:59:00 --partition=std  ~/anaconda3/bin/invoke create-new-index $i/ & done
#for i in /work/ftsx015/tib/tsv/*; do srun --time=00:59:00 ~/anaconda3/bin/invoke create-vectorfiles --tsv_path="$i" --out_path="/work/ftsx015/tib/work/" & done
#for i in /work/ftsx015/tib/tsv/*; do srun --time=00:59:00 ~/anaconda3/bin/invoke create-vectorfiles --tsv-path="$i/" --out-path="/work/ftsx015/tib/work/" --lang="tib" --threads=16 --bucket-num=50 & done

#for i in /work/ftsx015/tib/work/folder*; do srun --time=1:59:00 --partition=std  ~/anaconda3/bin/invoke create-new-index $i & done

for i in /work/ftsx015/tib/work/folder*; do srun --time=11:59:00 --partition=std  ~/anaconda3/bin/invoke get-results-from-index --bucket-path $i/ --lang="tib" --alignment-method="local" --index-method="cpu" & done

#~/anaconda3/bin/invoke get-results-from-index --bucket-path /work/ftsx015/tib/work/ --txt_path /work/ftsx015/tib/txt/ 

