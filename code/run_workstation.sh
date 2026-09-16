#!/usr/bin/env bash
#
# Local workstation driver: create vector files → build FAISS index per work folder →
# query index per folder → merge matches (DharmaNexus-style package, same as run_slurm.sh
# merge_results using merge-results-for-db-exp). Paths and language are configured below;
# optionally limit which steps run via command-line task names.
#
# Usage:
#   ./run_workstation.sh                              # all four steps
#   ./run_workstation.sh get_results                  # only get-results-from-index
#   ./run_workstation.sh create_new_index get_results
#   ./run_workstation.sh merge_results                  # only merge (after matches exist)
#
# From repo root you can:  code/run_workstation.sh
# Recommended: cd to this directory (code/) so invoke finds tasks.py.
#
set -u

# --- hard-coded pipeline parameters (edit these) ---
LANG="tib"
NUM_BUCKETS=10

# Root that contains work/folder0 .. work/folder$((NUM_BUCKETS-1))
# Override at runtime: WORK_DIR=/path/to/zh/work ./run_workstation.sh
WORK_DIR="${WORK_DIR:-../data/${LANG}/work}"
# TSV shards for create-vectorfiles (hardcoded per language)
case "$LANG" in
    tib) TSV_DIR_DEFAULT="${HOME}/data/dharmanexus-tibetan/segments/" ;;
    *)   TSV_DIR_DEFAULT="../data/${LANG}/segments" ;;
esac
TSV_DIR="${TSV_DIR:-$TSV_DIR_DEFAULT}"
# Output for merge-results-for-db-exp (DharmaNexus-ready NDJSON package)
OUT_DIR="${OUT_DIR:-../data/${LANG}/output}"

# Work folders are auto-discovered: any directory under $WORK_DIR whose name
# starts with "folder" is treated as a bucket.
FOLDER_PREFIX="folder"

VECTOR_THREADS="${VECTOR_THREADS:-64}"
GET_RESULTS_THREADS="${GET_RESULTS_THREADS:-64}"
# Merge step pool size; 0 = use all CPUs (same convention as invoke threads=0)
MERGE_THREADS="${MERGE_THREADS:-64}"
INDEX_METHOD="${INDEX_METHOD:-cpu}"
ALIGNMENT_METHOD="${ALIGNMENT_METHOD:-local}"
# Optional extras passed to invoke (empty ok)
CREATE_INDEX_EXTRA=()   # e.g. ( --load-workers 8 )
GET_RESULTS_EXTRA=()    # e.g. ( --load-workers 8 --file-batch-size 5000 )
MERGE_EXTRA=()          # extra flags for merge invoke
# merge-results-for-db and merge-results-for-db-exp are the same task (alias).
MERGE_INVOKE_TASK="${MERGE_INVOKE_TASK:-merge-results-for-db-exp}"

# --- invoke binary ---
INVOKE="${INVOKE:-invoke}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR" || exit 1

usage() {
    echo "Usage: $0 [TASK ...]"
    echo "Tasks (invoke names, space-separated if multiple):"
    echo "  create_vectorfiles   invoke create-vectorfiles (once, uses NUM_BUCKETS)"
    echo "  create_new_index     invoke create-new-index for each work folder"
    echo "  get_results          invoke get-results-from-index for each work folder"
    echo "  merge_results        invoke ${MERGE_INVOKE_TASK:-merge-results-for-db-exp} (WORK_DIR → OUT_DIR)"
    echo "Default TASK list: all four in order."
    echo "Env overrides: WORK_DIR, TSV_DIR, OUT_DIR, LANG, NUM_BUCKETS,"
    echo "  MERGE_INVOKE_TASK (default merge-results-for-db-exp), MERGE_THREADS (0=all CPUs), INVOKE, ..."
    exit 0
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
    usage
fi

if [[ $# -gt 0 ]]; then
    TASKS=("$@")
else
    TASKS=(create_vectorfiles create_new_index get_results merge_results)
fi

run_create_vectorfiles() {
    echo "==> create_vectorfiles  lang=${LANG}  buckets=${NUM_BUCKETS}  tsv=${TSV_DIR}  out=${WORK_DIR}/"
    "$INVOKE" create-vectorfiles \
        --tsv-path="$TSV_DIR" \
        --out-path="${WORK_DIR}/" \
        --lang="$LANG" \
        --threads="$VECTOR_THREADS" \
        --bucket-num="$NUM_BUCKETS"
}

discover_folders() {
    local f
    for f in "${WORK_DIR}/${FOLDER_PREFIX}"*/; do
        [[ -d "$f" ]] || continue
        printf '%s\n' "${f%/}"
    done | sort -V
}

run_create_new_index() {
    local folder found=0
    echo "==> create_new_index  (folders matching ${FOLDER_PREFIX}* under ${WORK_DIR})"
    while IFS= read -r folder; do
        [[ -n "$folder" ]] || continue
        found=1
        echo "    --- $folder"
        "$INVOKE" create-new-index "${folder}/" "${CREATE_INDEX_EXTRA[@]}"
    done < <(discover_folders)
    if [[ $found -eq 0 ]]; then
        echo "    (no ${FOLDER_PREFIX}* directories found in ${WORK_DIR})"
    fi
}

run_get_results() {
    local folder found=0
    echo "==> get_results_from_index  (folders matching ${FOLDER_PREFIX}* under ${WORK_DIR})"
    export OMP_WAIT_POLICY="${OMP_WAIT_POLICY:-PASSIVE}"
    while IFS= read -r folder; do
        [[ -n "$folder" ]] || continue
        found=1
        echo "    --- $folder"
        "$INVOKE" get-results-from-index \
            --bucket-path="${folder}/" \
            --lang="$LANG" \
            --index-method="$INDEX_METHOD" \
            --alignment-method="$ALIGNMENT_METHOD" \
            --src-pattern="BO" \
            --threads="$GET_RESULTS_THREADS" \
            "${GET_RESULTS_EXTRA[@]}"
    done < <(discover_folders)
    if [[ $found -eq 0 ]]; then
        echo "    (no ${FOLDER_PREFIX}* directories found in ${WORK_DIR})"
    fi
}

run_merge_results() {
    echo "==> merge_results  ${MERGE_INVOKE_TASK}  input=${WORK_DIR}  output=${OUT_DIR}  threads=${MERGE_THREADS}"
    mkdir -p "$OUT_DIR"
    "$INVOKE" "$MERGE_INVOKE_TASK" \
        --input-path="$WORK_DIR" \
        --output-path="$OUT_DIR" \
        --threads="$MERGE_THREADS" \
        "${MERGE_EXTRA[@]}"
}

for task in "${TASKS[@]}"; do
    case "$task" in
        create_vectorfiles)
            run_create_vectorfiles
            ;;
        create_new_index)
            run_create_new_index
            ;;
        get_results)
            run_get_results
            ;;
        merge_results)
            run_merge_results
            ;;
        -h|--help)
            usage
            ;;
        *)
            echo "Unknown task: $task" >&2
            echo "Expected one of: create_vectorfiles create_new_index get_results merge_results" >&2
            exit 1
            ;;
    esac
done

echo "Done. Tasks: ${TASKS[*]}"
