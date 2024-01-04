import json
import pandas
import glob
import multiprocessing
import os
import gzip
import sys 

input_path = sys.argv[1]
output_path = sys.argv[2]


def read_json_gz(filepath):
    """Read a .json.gz file and return its content."""
    print(f'Reading {filepath}')
    with gzip.open(filepath, 'rt') as f:
        return json.load(f)

def collect_json_gz_files(directory):
    """Recursively find all .json.gz files under the directory."""
    for root, _, files in os.walk(directory):
        for filename in files:
            if filename.endswith('.json.gz'):
                yield os.path.join(root, filename)

def process_chunk(data):
    file_chunk, chunk_id = data 
    """Process a chunk of files (read and merge their content)."""
    merged_content = []    
    for filepath in file_chunk:        
        content = read_json_gz(filepath)
        merged_content.extend(content)
    write_chunk(merged_content, chunk_id)

def write_chunk(chunk, chunk_id):
    """Write a chunk to a file in output_path as json.gz."""
    filename = os.path.join(output_path, f'chunk_{chunk_id}.json.gz')
    with gzip.open(filename, 'wt') as f:
        json.dump(chunk, f)
    


def merge_json_gz_files(directory):
    """Find all .json.gz files, chunk them and process each chunk using multiprocessing."""
    all_files = list(collect_json_gz_files(directory))
    
    # Chunk files into chunks of 1000 files each
    chunks = [all_files[i:i + 1000] for i in range(0, len(all_files), 1000)]
    # create list of format [chunk, chunk_id]
    chunks = [(chunk, chunk_id) for chunk_id, chunk in enumerate(chunks)]

    # Use multiprocessing to process each chunk
    with multiprocessing.Pool() as pool:
        pool.map(process_chunk, chunks)

merge_json_gz_files(input_path)