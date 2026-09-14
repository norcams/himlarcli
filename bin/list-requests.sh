#!/bin/bash
#
# list-requests.sh
#
# Quick overview of IaaS project request submissions from Nettskjema
# form 289417, the "new project" form available at https://request.nrec.no.
#
# Note: This script ONLY queries submissions to the new-project form.
# It does not access other Nettskjema forms or ticket systems, and
# it does NOT distinguish between resolved and unresolved requests.
# Resolution state is managed elsewhere (e.g. in Request Tracker).
#
# Displays key submission details in a compact tabular format.
#
# Usage:
#   list-requests.sh [OPTIONS]
#
# Options:
#   -l, --limit N       Show last N submissions (default: 50; set to -1
#                       for all submissions)
#   -f, --from-id ID    Only show submissions with ID >= ID
#   --oldest-first      Sort oldest first (default: newest first)
#   -h, --help          Show this help message
#
# Environment:
#   NETTSKJEMA_API_ACCESS_TOKEN   Required API bearer token
#
# Example:
#   export NETTSKJEMA_API_ACCESS_TOKEN=TOKEN
#   ./list-requests.sh              # last 50
#   ./list-requests.sh --limit 100  # last 100
#   ./list-requests.sh --from-id 7500000
#
# API Reference:
#   https://www.uio.no/english/services/it/adm-services/nettskjema/help/api-clients-v3.md
#   https://nettskjema.no/api/v3/swagger-ui/index.html#/
#

set -euo pipefail

FORM_ID=289417
API_BASE="https://nettskjema.no/api/v3"
LIMIT=50
FROM_ID=0
SORT_ORDER="desc"

# --- Column widths ---
W_ID=10
W_AGE=8
W_DATE=19
W_EMAIL=28
W_TYPE=16
W_INST=14
W_PROJ=36

# --- Build format and separator from widths ---
fmt=""
sep=""
build_fmt_and_sep() {
    fmt=$(printf "%%-%ds %%-%ds %%-%ds %%-%ds %%-%ds %%-%ds %%-%ds" \
        "$W_ID" "$W_AGE" "$W_DATE" "$W_EMAIL" "$W_TYPE" "$W_INST" "$W_PROJ")
    sep=""
    for w in "$W_ID" "$W_AGE" "$W_DATE" "$W_EMAIL" "$W_TYPE" "$W_INST" "$W_PROJ"; do
        sep="${sep}$(printf '%*s' "$w" '' | tr ' ' '-') "
    done
    sep="${sep% }"   # trim trailing space
}

# --- Helper: human-readable age since ISO date ---
human_age() {
    local iso="$1"
    if [[ -z "$iso" || "$iso" == "null" || "$iso" == "N/A" ]]; then
        echo "N/A"
        return
    fi
    local now_sec then_sec
    now_sec=$(date +%s)
    # GNU date
    if date -d "$iso" +%s &>/dev/null; then
        then_sec=$(date -d "$iso" +%s)
    else
        # BSD date
        then_sec=$(date -j -f "%Y-%m-%dT%H:%M:%S" "${iso%%[+Z]*}" +%s 2>/dev/null || echo "")
    fi
    if [[ -z "$then_sec" ]]; then
        echo "N/A"
        return
    fi
    local diff=$(( now_sec - then_sec ))
    if (( diff < 3600 )); then
        printf "%dm\n" $(( diff / 60 ))
    elif (( diff < 86400 )); then
        printf "%dh\n" $(( diff / 3600 ))
    elif (( diff < 604800 )); then
        printf "%dd\n" $(( diff / 86400 ))
    else
        printf "%dw\n" $(( diff / 604800 ))
    fi
}

# --- Argument parsing ---
while [[ $# -gt 0 ]]; do
    case $1 in
        -l|--limit)
            LIMIT="$2"
            shift 2
            ;;
        -f|--from-id)
            FROM_ID="$2"
            shift 2
            ;;
        --oldest-first)
            SORT_ORDER="asc"
            shift
            ;;
        -h|--help)
            sed -n '2,37p' "$0"
            exit 0
            ;;
        *)
            echo "Unknown option: $1" >&2
            echo "Use -h or --help for usage." >&2
            exit 1
            ;;
    esac
done

# --- Prerequisites ---
if ! command -v jq &>/dev/null; then
    echo "Error: jq is required but not installed." >&2
    exit 1
fi
if ! command -v curl &>/dev/null; then
    echo "Error: curl is required but not installed." >&2
    exit 1
fi
if [[ -z "${NETTSKJEMA_API_ACCESS_TOKEN:-}" ]]; then
    echo "Error: NETTSKJEMA_API_ACCESS_TOKEN is not set." >&2
    echo "Set the token in your environment before running this script." >&2
    exit 1
fi

# --- Helper: resolve human-readable answer for an element ID ---
# Uses a global element_data JSON and elem_option_map associative array.
get_answer_text() {
    local adata="$1"
    local eid="$2"

    local ans
    ans=$(echo "$adata" | jq -r --argjson id "$eid" '
        (.answers[]? | select(.elementId == $id)) // empty
    ')

    if [[ -z "$ans" ]]; then
        echo "N/A"
        return
    fi

    # Text answer (free text / short text fields)
    local txt
    txt=$(echo "$ans" | jq -r '.textAnswer // empty')
    if [[ -n "$txt" ]]; then
        # Strip simple HTML tags for display
        echo "$txt" | sed 's/<[^>]*>//g'
        return
    fi

    # Multiple choice: map answerOptionIds to text via element_data
    local opts
    opts=$(echo "$ans" | jq -r '.answerOptionIds[]? // empty')
    if [[ -z "$opts" ]]; then
        echo "N/A"
        return
    fi

    local result=""
    for opt in $opts; do
        local opt_text
        opt_text=$(echo "${elem_option_map[$eid]}" | grep "^${opt}|" | cut -d'|' -f2-)
        if [[ -n "$result" ]]; then
            result="$result, $opt_text"
        else
            result="$opt_text"
        fi
    done
    [[ -n "$result" ]] && echo "$result" || echo "N/A"
}

# --- Helper: extract abbreviated institution from "Full Name (ABBREV)" ---
abbreviate_institution() {
    local text="$1"
    local abbrev
    abbrev=$(echo "$text" | sed -n 's/.*(\([^)]*\)).*/\1/p')
    if [[ -n "$abbrev" ]]; then
        echo "$abbrev"
    else
        echo "$text"
    fi
}

# --- Fetch form element data (for resolving multiple-choice answers) ---
echo "Fetching form data..." >&2
element_data=$(curl -sf -H "Authorization: Bearer ${NETTSKJEMA_API_ACCESS_TOKEN}" \
    "${API_BASE}/form/${FORM_ID}/elements") || {
    echo "Error: Failed to fetch form element data." >&2
    exit 1
}

# --- Build answer-option lookup maps for key elements ---
# Element IDs from new-project workflow:
#   4559698 = Project Type
#   4559711 = Educational Institution
declare -A elem_option_map
for eid in 4559698 4559711; do
    elem_option_map[$eid]=$(echo "$element_data" | jq -r --argjson id "$eid" '
        [.[]? | select(.elementId == $id) | .answerOptions[]? | "\(.answerOptionId)|\(.text)"] |
        join("\n")
    ')
done

# --- Fetch submission metadata ---
metadata=$(curl -sf -H "Authorization: Bearer ${NETTSKJEMA_API_ACCESS_TOKEN}" \
    "${API_BASE}/form/${FORM_ID}/submission-metadata") || {
    echo "Error: Failed to fetch submission metadata." >&2
    exit 1
}

# --- Extract submission IDs ---
submissionIds=$(echo "$metadata" | jq -r --argjson from_id "$FROM_ID" --argjson limit "$LIMIT" --arg sort "$SORT_ORDER" --slurp '
    [ .[] | select(type == "object" and has("submissionId") and .submissionId >= $from_id) ] |
    (if $sort == "asc" then sort_by(.submissionId | tonumber)
     else sort_by(.submissionId | tonumber) | reverse end) |
    (if $limit >= 0 then .[:$limit] else . end) |
    .[].submissionId
')

if [[ -z "$submissionIds" ]]; then
    echo "No submissions found."
    exit 0
fi

total=$(echo "$submissionIds" | wc -w)
echo "Fetching $total submission(s)..." >&2

# --- Print header ---
build_fmt_and_sep
printf "$fmt\n" "ID" "Age" "Date" "Email" "Type" "Institution" "Project"
echo "$sep"

# --- Iterate submissions ---
count=0
for sid in $submissionIds; do
    adata=$(curl -sf -H "Authorization: Bearer ${NETTSKJEMA_API_ACCESS_TOKEN}" \
        "${API_BASE}/form/submission/${sid}") || {
        echo "Warning: failed to fetch submission $sid, skipping." >&2
        continue
    }

    # Extract metadata
    sdate=$(echo "$adata" | jq -r '.submissionMetadata.createdDate // .submissionMetadata.modifiedDate // .submissionMetadata.submissionDate // .submissionMetadata.submissionTime // "N/A"')
    semail=$(echo "$adata" | jq -r '.submissionMetadata.respondentEmail // "N/A"')

    # Extract key answers
    ptype=$(get_answer_text "$adata" 4559698)
    inst=$(get_answer_text "$adata" 4559711)
    pname=$(get_answer_text "$adata" 4559713)

    # Abbreviate institution, e.g. "University of Oslo (UiO)" -> "UiO"
    inst=$(abbreviate_institution "$inst")

    # Compute human-readable age
    age=$(human_age "$sdate")

    # Truncate for clean display
    sdate="${sdate:0:$W_DATE}"
    semail="${semail:0:$W_EMAIL}"
    ptype="${ptype:0:$W_TYPE}"
    inst="${inst:0:$W_INST}"
    pname="${pname:0:$W_PROJ}"
    age="${age:0:$W_AGE}"

    printf "$fmt\n" "$sid" "$age" "$sdate" "$semail" "$ptype" "$inst" "$pname"

    count=$((count + 1))
done

echo ""
echo "Total: $count/$total submission(s) shown"
