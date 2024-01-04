#!/bin/bash
txt_path="/work/ftsx015/tib/txt/"
tsv_path="/work/ftsx015/tib/tsv/"

# Set the number of buckets
NUM_BUCKETS=50

# Create the bucket folders
for (( i=0; i<$NUM_BUCKETS; i++ ))
do
    mkdir -p "$tsv_path"bucket_$i
done

# Distribute the contents of the folder randomly into the bucket folders
for file in "$txt_path"*tsv
do
    if [ "$file" != "bucket_*" ] # Exclude the bucket folders from the distribution
    then
        bucket=$((RANDOM%$NUM_BUCKETS))
        cp "$file" "$tsv_path"bucket_$bucket/
    fi
done