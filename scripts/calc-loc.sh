#!/usr/bin/env bash
# Calculate lines of code in the AutoBuilder codebase
# Usage: ./scripts/calc-loc.sh [--all]
#   --all: include non-code files (docs, config, etc.)

set -uo pipefail
cd "$(git -C "$(dirname "$0")/.." rev-parse --show-toplevel)"

BLUE='\033[0;34m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BOLD='\033[1m'
RESET='\033[0m'

# Accumulators
sum_code=0 sum_blank=0 sum_comment=0 sum_files=0

# Count and print a row; accumulates into sum_* variables
print_row() {
    local label="$1"
    local files="$2"
    if [[ -z "$files" ]]; then
        printf "  %-20s %8d %8d %8d %6d\n" "$label" 0 0 0 0
        return
    fi
    local total blank comment code file_count
    total=$(echo "$files" | xargs wc -l 2>/dev/null | tail -1 | awk '{print $1}')
    blank=$(echo "$files" | xargs grep -c '^[[:space:]]*$' 2>/dev/null | awk -F: '{s+=$2} END{print s+0}') || true
    comment=$(echo "$files" | xargs grep -cE '^\s*(#|//|/\*|\*|"""|'"'"'""")' 2>/dev/null | awk -F: '{s+=$2} END{print s+0}') || true
    code=$((total - blank - comment))
    file_count=$(echo "$files" | wc -l)
    printf "  %-20s %8d %8d %8d %6d\n" "$label" "$code" "$blank" "$comment" "$file_count"
    sum_code=$((sum_code + code))
    sum_blank=$((sum_blank + blank))
    sum_comment=$((sum_comment + comment))
    sum_files=$((sum_files + file_count))
}

# Gather file lists (mutually exclusive categories)
py_app=$(git ls-files -- 'app/**/*.py' 'app/*.py') || true
py_tests=$(git ls-files -- 'tests/**/*.py' 'tests/*.py') || true
py_other=$(git ls-files -- '*.py' | grep -vE '^(app|tests)/' ) || true
ts_files=$(git ls-files -- '**/*.ts' '**/*.tsx' '*.ts' '*.tsx') || true
js_files=$(git ls-files -- '**/*.js' '**/*.jsx' '*.js' '*.jsx') || true
sh_files=$(git ls-files -- '**/*.sh' '*.sh') || true
sql_files=$(git ls-files -- '**/*.sql' '*.sql') || true
css_files=$(git ls-files -- '**/*.css' '*.css') || true
html_files=$(git ls-files -- '**/*.html' '*.html') || true

echo ""
repo_name=$(basename "$(git rev-parse --show-toplevel)")
echo -e "${BOLD}${repo_name} — Lines of Code${RESET}"
echo -e "${BOLD}$(printf '=%.0s' $(seq 1 $((${#repo_name} + 17))))${RESET}"
echo ""

printf "  ${BLUE}%-20s %8s %8s %8s %6s${RESET}\n" "Category" "Code" "Blank" "Comment" "Files"
printf "  %-20s %8s %8s %8s %6s\n" "--------------------" "--------" "--------" "--------" "------"

echo -e "${GREEN}Source:${RESET}"
print_row "Python (app/)" "$py_app"
print_row "Python (tests/)" "$py_tests"
print_row "Python (other)" "$py_other"
print_row "TypeScript" "$ts_files"
print_row "JavaScript" "$js_files"
print_row "Shell" "$sh_files"
print_row "SQL" "$sql_files"
print_row "CSS" "$css_files"
print_row "HTML" "$html_files"

printf "  %-20s %8s %8s %8s %6s\n" "--------------------" "--------" "--------" "--------" "------"
code_total_code=$sum_code code_total_blank=$sum_blank
code_total_comment=$sum_comment code_total_files=$sum_files
printf "  ${BOLD}%-20s %8d %8d %8d %6d${RESET}\n" "TOTAL (code)" "$sum_code" "$sum_blank" "$sum_comment" "$sum_files"

if [[ "${1:-}" == "--all" ]]; then
    echo ""
    sum_code=0 sum_blank=0 sum_comment=0 sum_files=0

    echo -e "${YELLOW}Non-code:${RESET}"
    md_files=$(git ls-files -- '*.md' '**/*.md') || true
    config_files=$(git ls-files -- '*.json' '*.yaml' '*.yml' '*.toml' '**/*.json' '**/*.yaml' '**/*.yml' '**/*.toml') || true
    docker_files=$(git ls-files -- 'Dockerfile' 'docker-compose*.yml' '.github/**/*') || true
    other_files=$(git ls-files -- '*.mako' '*.ini' '*.lock' '*.example' '*.gitkeep' '*.gitignore' '*.dockerignore' 'LICENSE') || true

    print_row "Markdown" "$md_files"
    print_row "JSON/YAML/TOML" "$config_files"
    print_row "Docker/CI" "$docker_files"
    print_row "Other" "$other_files"

    printf "  %-20s %8s %8s %8s %6s\n" "--------------------" "--------" "--------" "--------" "------"
    printf "  ${BOLD}%-20s %8d %8d %8d %6d${RESET}\n" "TOTAL (non-code)" "$sum_code" "$sum_blank" "$sum_comment" "$sum_files"

    echo ""
    printf "  %-20s %8s %8s %8s %6s\n" "====================" "========" "========" "========" "======"
    combined_code=$((code_total_code + sum_code))
    combined_blank=$((code_total_blank + sum_blank))
    combined_comment=$((code_total_comment + sum_comment))
    combined_files=$((code_total_files + sum_files))
    printf "  ${BOLD}%-20s %8d %8d %8d %6d${RESET}\n" "COMBINED" "$combined_code" "$combined_blank" "$combined_comment" "$combined_files"
    printf "  ${BLUE}All git-tracked files (code + docs + config + assets)${RESET}\n"
fi

echo ""
