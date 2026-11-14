#!/usr/bin/env bash
# =============================================================================
# _lib.sh — Shared library for Cosmic Ray tier scripts
# Source this file from each tier script — do not run directly.
# =============================================================================

# ── Terminal color codes ──────────────────────────────────────────────────────
CR_RESET="\033[0m"
CR_BOLD="\033[1m"
CR_DIM="\033[2m"
CR_GREEN="\033[32m"
CR_RED="\033[31m"
CR_YELLOW="\033[33m"
CR_CYAN="\033[36m"
CR_BLUE="\033[34m"
CR_WHITE="\033[37m"

# ── Menu ─────────────────────────────────────────────────────────────────────
# cr_show_menu — 3-section menu: Groups | Files | Admin
#
# Caller must define before calling:
#   GROUP_NAMES[]      — group display names
#   GROUP_TIMES[]      — per-group time estimates
#   GROUP_N_FILES[]    — source files for group N
#   GROUP_N_TESTS[]    — test files for group N
#
#   FILE_NAMES[]       — individual file display names (basename)
#   FILE_TIMES[]       — per-file time estimates
#   FILE_GROUP_REFS[]  — "(G1)" label showing parent group
#   FILE_N_SRC         — the single source file path for file entry N
#   FILE_N_GROUP       — which group's tests to use for file entry N (integer)
#
# After return, SELECTED_RESULT is one of:
#   "group:N"     — run group N
#   "file:N"      — run single file N
#   "all_groups"  — run all groups sequentially
#   (exits on E)
cr_show_menu() {
    local num_groups=${#GROUP_NAMES[@]}
    local num_files=${#FILE_NAMES[@]}
    local max_choice=$(( num_groups + num_files ))

    echo ""
    echo -e "${CR_BOLD}${CR_CYAN}  ── GROUPS ──────────────────────────────────────────────────────${CR_RESET}"
    for i in "${!GROUP_NAMES[@]}"; do
        local idx=$(( i + 1 ))
        echo -e "  ${CR_BOLD}[${idx}]${CR_RESET} ${GROUP_NAMES[$i]} ${CR_DIM}${GROUP_TIMES[$i]}${CR_RESET}"
    done
    echo ""
    echo -e "${CR_BOLD}${CR_CYAN}  ── FILES ───────────────────────────────────────────────────────${CR_RESET}"
    for i in "${!FILE_NAMES[@]}"; do
        local idx=$(( num_groups + i + 1 ))
        local gref="${FILE_GROUP_REFS[$i]:-}"
        echo -e "  ${CR_BOLD}[${idx}]${CR_RESET} ${FILE_NAMES[$i]} ${CR_DIM}${FILE_TIMES[$i]}${CR_RESET} ${CR_DIM}${gref}${CR_RESET}"
    done
    echo ""
    echo -e "${CR_BOLD}${CR_CYAN}  ── ADMIN ───────────────────────────────────────────────────────${CR_RESET}"
    echo -e "  ${CR_BOLD}[A]${CR_RESET} Run All groups sequentially"
    echo -e "  ${CR_BOLD}[E]${CR_RESET} Exit"
    echo ""
    while true; do
        read -rp "  Choice [1-${max_choice} / A / E]: " cr_menu_choice
        cr_menu_choice=$(echo "${cr_menu_choice}" | tr '[:lower:]' '[:upper:]')

        if [[ "${cr_menu_choice}" == "E" ]]; then
            echo -e "  ${CR_DIM}Exiting.${CR_RESET}"
            exit 0

        elif [[ "${cr_menu_choice}" == "A" ]]; then
            SELECTED_RESULT="all_groups"
            return

        elif [[ "${cr_menu_choice}" =~ ^[0-9]+$ ]]; then
            local choice_int="${cr_menu_choice}"
            if [ "${choice_int}" -ge 1 ] && [ "${choice_int}" -le "${num_groups}" ]; then
                SELECTED_RESULT="group:${choice_int}"
                return
            elif [ "${choice_int}" -gt "${num_groups}" ] && [ "${choice_int}" -le "${max_choice}" ]; then
                local file_idx=$(( choice_int - num_groups ))
                SELECTED_RESULT="file:${file_idx}"
                return
            else
                echo -e "  ${CR_YELLOW}Invalid — enter 1–${max_choice}, A, or E.${CR_RESET}"
            fi
        else
            echo -e "  ${CR_YELLOW}Invalid — enter 1–${max_choice}, A, or E.${CR_RESET}"
        fi
    done
}

# cr_run_selected — dispatch based on SELECTED_RESULT from cr_show_menu.
cr_run_selected() {
    local base_tier_name="${TIER_NAME}"
    local base_session_dir="${SESSION_DIR}"

    case "${SELECTED_RESULT}" in

        all_groups)
            for i in "${!GROUP_NAMES[@]}"; do
                local g=$(( i + 1 ))
                _cr_run_group "${g}" "${base_tier_name}" "${base_session_dir}"
            done
            ;;

        group:*)
            local g="${SELECTED_RESULT#group:}"
            _cr_run_group "${g}" "${base_tier_name}" "${base_session_dir}"
            ;;

        file:*)
            local f="${SELECTED_RESULT#file:}"
            _cr_run_file "${f}" "${base_tier_name}" "${base_session_dir}"
            ;;
    esac
}

# _cr_run_group — internal: run group G with its files and tests.
_cr_run_group() {
    local g="$1"
    local base_tier_name="$2"
    local base_session_dir="$3"

    eval "SOURCE_FILES=(\"\${GROUP_${g}_FILES[@]}\")"
    eval "local _tests=(\"\${GROUP_${g}_TESTS[@]}\")"
    TEST_COMMAND=".venv/bin/pytest ${_tests[*]} -x -q --tb=no"

    # Slugify group name for session path
    local group_slug
    group_slug=$(echo "${GROUP_NAMES[$(( g - 1 ))]}" | tr '[:upper:]' '[:lower:]' | sed 's/[^a-z0-9]/-/g' | sed 's/--*/-/g' | sed 's/^-//' | sed 's/-$//')

    SESSION_DIR="${base_session_dir}/groups/g${g}-${group_slug}"
    TIER_NAME="${base_tier_name} › Group ${g}: ${GROUP_NAMES[$(( g - 1 ))]}"

    cr_run_tier

    TIER_NAME="${base_tier_name}"
    SESSION_DIR="${base_session_dir}"
}

# _cr_run_file — internal: run single file F using its parent group's tests.
_cr_run_file() {
    local f="$1"
    local base_tier_name="$2"
    local base_session_dir="$3"

    eval "local _src_file=\"\${FILE_${f}_SRC}\""
    eval "local _parent_group=\"\${FILE_${f}_GROUP}\""
    eval "local _tests=(\"\${GROUP_${_parent_group}_TESTS[@]}\")"

    SOURCE_FILES=("${_src_file}")
    TEST_COMMAND=".venv/bin/pytest ${_tests[*]} -x -q --tb=no"

    # Slugify file name for session path
    local file_slug
    file_slug=$(basename "${_src_file}" .py | tr '[:upper:]' '[:lower:]' | tr '_' '-')

    SESSION_DIR="${base_session_dir}/files/f${f}-${file_slug}"
    TIER_NAME="${base_tier_name} › File: $(basename ${_src_file}) ${FILE_GROUP_REFS[$(( f - 1 ))]:-}"

    cr_run_tier

    TIER_NAME="${base_tier_name}"
    SESSION_DIR="${base_session_dir}"
}

# cr_main_loop — show the menu, run the selection, then show the menu again.
# Continues until the user selects E (Exit).
# Replace the inline cr_show_menu + cr_run_selected calls in tier scripts with this.
cr_main_loop() {
    while true; do
        cr_show_menu
        cr_run_selected
        echo ""
        echo -e "  ${CR_BOLD}${CR_CYAN}── Press any key to return to the menu ──────────────────────────${CR_RESET}"
        read -r -s -n 1
        echo ""
    done
}

# ── Helpers ───────────────────────────────────────────────────────────────────
_cr_elapsed() {
    local start=$1
    local end=$2
    local secs=$(( end - start ))
    local mins=$(( secs / 60 ))
    local rem=$(( secs % 60 ))
    if [ "$mins" -gt 0 ]; then
        printf "%dm %02ds" "$mins" "$rem"
    else
        printf "%ds" "$secs"
    fi
}

_cr_bar() {
    # Draw a progress bar: _cr_bar <current> <total> <width>
    local current=$1
    local total=$2
    local width=${3:-40}
    local filled=$(( current * width / total ))
    local empty=$(( width - filled ))
    printf "["
    printf "%${filled}s" | tr ' ' '█'
    printf "%${empty}s" | tr ' ' '░'
    printf "]"
}

_cr_score_color() {
    local score=$1
    if [ "$score" -ge 80 ]; then
        echo -n "${CR_GREEN}"
    elif [ "$score" -ge 60 ]; then
        echo -n "${CR_YELLOW}"
    else
        echo -n "${CR_RED}"
    fi
}

# ── Main runner ───────────────────────────────────────────────────────────────
# Usage: cr_run_tier <tier_name> <session_dir> <test_command> <source_files_array_name>
# Caller sets:   TIER_NAME, SESSION_DIR, TEST_COMMAND, SOURCE_FILES (array)
cr_run_tier() {
    local tier_name="$TIER_NAME"
    local session_dir="$SESSION_DIR"
    local test_command="$TEST_COMMAND"

    local total_files=${#SOURCE_FILES[@]}
    local tier_start=$(date +%s)
    local report_dir="${session_dir}/reports"
    mkdir -p "${session_dir}" "${report_dir}"

    local report_name_safe
    report_name_safe=$(echo "${tier_name}" | sed 's/›/-/g; s/:/-/g; s/  */ /g')
    local report_file="${report_dir}/$(date +%Y-%m-%d_%H-%M-%S)_${report_name_safe}.md"

    # ── Header ────────────────────────────────────────────────────────────────
    echo ""
    echo -e "${CR_BOLD}${CR_CYAN}╔══════════════════════════════════════════════════════════════════╗${CR_RESET}"
    echo -e "${CR_BOLD}${CR_CYAN}║  COSMIC RAY MUTATION TESTING                                     ║${CR_RESET}"
    echo -e "${CR_BOLD}${CR_CYAN}║  ${tier_name}$(printf '%*s' $((64 - ${#tier_name} - 2)) '')║${CR_RESET}"
    echo -e "${CR_BOLD}${CR_CYAN}╚══════════════════════════════════════════════════════════════════╝${CR_RESET}"
    echo -e "${CR_DIM}  Started:      $(date '+%Y-%m-%d %H:%M:%S')${CR_RESET}"
    echo -e "${CR_DIM}  Source files: ${total_files}${CR_RESET}"
    echo -e "${CR_DIM}  Sessions:     ${session_dir}${CR_RESET}"
    echo -e "${CR_DIM}  Report:       ${report_file}${CR_RESET}"
    echo ""

    # ── Init markdown report ──────────────────────────────────────────────────
    cat > "${report_file}" << HEADER
# Cosmic Ray Mutation Testing Report

**Tier**: ${tier_name}
**Date**: $(date '+%Y-%m-%d %H:%M:%S')
**Tool**: cosmic-ray $(cosmic-ray --version 2>/dev/null || echo "unknown")

---

## Summary (filled in after run)

| Metric | Value |
|---|---|
| Total Files | ${total_files} |
| Started | $(date '+%H:%M:%S') |
| Finished | TBD |
| Elapsed | TBD |
| Total Killed | TBD |
| Total Survived | TBD |
| Total Incompetent | TBD |
| **Mutation Score** | **TBD** |

---

## Per-File Results

| File | Killed | Survived | Incompetent | Score | Time |
|---|---|---|---|---|---|
HEADER

    # ── Per-file variables ────────────────────────────────────────────────────
    declare -a FILE_RESULTS=()
    local total_killed=0
    local total_survived=0
    local total_incompetent=0
    local current_file=0

    # ── File loop ─────────────────────────────────────────────────────────────
    for source_file in "${SOURCE_FILES[@]}"; do
        current_file=$(( current_file + 1 ))
        local file_start=$(date +%s)

        local safe_name="${source_file//\//_}"
        safe_name="${safe_name//.py/}"
        local session_file="${session_dir}/${safe_name}.sqlite"
        local temp_config
        # macOS mktemp does not support filename suffixes — use a plain temp file
        temp_config=$(mktemp /tmp/cr-XXXXXX)
        # Rename to .toml so cosmic-ray TOML parser is unambiguous
        mv "${temp_config}" "${temp_config}.toml"
        temp_config="${temp_config}.toml"

        # Progress header
        echo ""
        echo -e "${CR_BOLD}  $(_cr_bar "$current_file" "$total_files") ${current_file}/${total_files}${CR_RESET}"
        echo -e "${CR_BOLD}  File:    ${CR_WHITE}${source_file}${CR_RESET}"
        echo -e "${CR_DIM}  Started: $(date '+%H:%M:%S')${CR_RESET}"

        # Write temp config
        cat > "${temp_config}" << TOML
[cosmic-ray]
module-path = "${source_file}"
timeout = 30
test-command = "${test_command}"

[cosmic-ray.distributor]
name = "local"
TOML

        # Baseline check
        echo -ne "  ${CR_DIM}[1/3] Baseline check ...${CR_RESET}"
        if .venv/bin/cosmic-ray baseline "${temp_config}" > /dev/null 2>&1; then
            echo -e "\r  ${CR_GREEN}[1/3] Baseline: PASS${CR_RESET}               "
        else
            echo -e "\r  ${CR_RED}[1/3] Baseline: FAIL — skipping file${CR_RESET}"
            echo "| \`${source_file}\` | SKIP | SKIP | SKIP | BASELINE FAILED | — |" >> "${report_file}"
            rm -f "${temp_config}"
            continue
        fi

        # Init session
        echo -ne "  ${CR_DIM}[2/3] Generating mutants ...${CR_RESET}"
        .venv/bin/cosmic-ray init "${temp_config}" "${session_file}" --force > /dev/null 2>&1
        # Count pending work items using dump (cr-report only counts completed jobs)
        local num_mutants
        num_mutants=$(.venv/bin/cosmic-ray dump "${session_file}" 2>/dev/null | python3 -c "import sys,json; data=sys.stdin.read(); print(data.count('\"job_id\"'))" 2>/dev/null || echo 0)
        num_mutants="${num_mutants//[^0-9]/}"
        [ -z "${num_mutants}" ] && num_mutants="?"
        echo -e "\r  ${CR_CYAN}[2/3] Mutants to test: ${num_mutants}${CR_RESET}         "
        echo -e "  ${CR_DIM}[3/3] Running ${num_mutants} mutations (this takes time — ~4 sec each) ...${CR_RESET}"

        # Execute mutations
        local exec_start=$(date +%s)
        .venv/bin/cosmic-ray exec "${temp_config}" "${session_file}" 2>/dev/null
        local exec_end=$(date +%s)
        echo -e "  ${CR_CYAN}[3/3] Done — $(_cr_elapsed "$exec_start" "$exec_end")${CR_RESET}"

        # Parse results — strip non-numeric chars to avoid newline arithmetic errors
        local killed survived incompetent
        killed=$(.venv/bin/cr-report "${session_file}" 2>/dev/null | grep -c "TestOutcome.KILLED" || true)
        survived=$(.venv/bin/cr-report "${session_file}" 2>/dev/null | grep -c "TestOutcome.SURVIVED" || true)
        incompetent=$(.venv/bin/cr-report "${session_file}" 2>/dev/null | grep -c "TestOutcome.INCOMPETENT" || true)
        killed="${killed//[^0-9]/}"; [ -z "${killed}" ] && killed=0
        survived="${survived//[^0-9]/}"; [ -z "${survived}" ] && survived=0
        incompetent="${incompetent//[^0-9]/}"; [ -z "${incompetent}" ] && incompetent=0

        local total=$(( killed + survived ))
        local score=0
        [ "${total}" -gt 0 ] && score=$(( (killed * 100) / total ))

        local file_end=$(date +%s)
        local file_elapsed
        file_elapsed=$(_cr_elapsed "${file_start}" "${file_end}")

        # Per-file result line
        local score_color
        score_color=$(_cr_score_color "${score}")
        echo -e "  ${CR_BOLD}Result:  ${score_color}Score ${score}%${CR_RESET} | Killed ${CR_GREEN}${killed}${CR_RESET} | Survived ${CR_RED}${survived}${CR_RESET} | Incompetent ${CR_YELLOW}${incompetent}${CR_RESET} | ${CR_DIM}${file_elapsed}${CR_RESET}"

        # Append to report
        echo "| \`${source_file}\` | ${killed} | ${survived} | ${incompetent} | **${score}%** | ${file_elapsed} |" >> "${report_file}"

        # Accumulate totals
        total_killed=$(( total_killed + killed ))
        total_survived=$(( total_survived + survived ))
        total_incompetent=$(( total_incompetent + incompetent ))

        rm -f "${temp_config}"
    done

    # ── Tier summary ──────────────────────────────────────────────────────────
    local tier_end=$(date +%s)
    local tier_elapsed
    tier_elapsed=$(_cr_elapsed "${tier_start}" "${tier_end}")
    local grand_total=$(( total_killed + total_survived ))
    local grand_score=0
    [ "${grand_total}" -gt 0 ] && grand_score=$(( (total_killed * 100) / grand_total ))
    local grand_score_color
    grand_score_color=$(_cr_score_color "${grand_score}")

    echo ""
    echo -e "${CR_BOLD}${CR_CYAN}╔══════════════════════════════════════════════════════════════════╗${CR_RESET}"
    echo -e "${CR_BOLD}${CR_CYAN}║  ${tier_name} COMPLETE${CR_RESET}${CR_BOLD}${CR_CYAN}$(printf '%*s' $((57 - ${#tier_name})) '')║${CR_RESET}"
    echo -e "${CR_BOLD}${CR_CYAN}╠══════════════════════════════════════════════════════════════════╣${CR_RESET}"
    echo -e "${CR_BOLD}${CR_CYAN}║${CR_RESET}  Total elapsed:   ${CR_BOLD}${tier_elapsed}${CR_RESET}$(printf '%*s' $((49 - ${#tier_elapsed})) '')${CR_BOLD}${CR_CYAN}║${CR_RESET}"
    echo -e "${CR_BOLD}${CR_CYAN}║${CR_RESET}  Files mutated:   ${current_file}/${total_files}$(printf '%*s' $((47 - ${#current_file} - ${#total_files} - 1)) '')${CR_BOLD}${CR_CYAN}║${CR_RESET}"
    echo -e "${CR_BOLD}${CR_CYAN}║${CR_RESET}  Killed:          ${CR_GREEN}${CR_BOLD}${total_killed}${CR_RESET}$(printf '%*s' $((49 - ${#total_killed})) '')${CR_BOLD}${CR_CYAN}║${CR_RESET}"
    echo -e "${CR_BOLD}${CR_CYAN}║${CR_RESET}  Survived:        ${CR_RED}${CR_BOLD}${total_survived}${CR_RESET}$(printf '%*s' $((49 - ${#total_survived})) '')${CR_BOLD}${CR_CYAN}║${CR_RESET}"
    echo -e "${CR_BOLD}${CR_CYAN}║${CR_RESET}  Incompetent:     ${CR_YELLOW}${total_incompetent}${CR_RESET}$(printf '%*s' $((49 - ${#total_incompetent})) '')${CR_BOLD}${CR_CYAN}║${CR_RESET}"
    echo -e "${CR_BOLD}${CR_CYAN}║${CR_RESET}  Mutation Score:  ${grand_score_color}${CR_BOLD}${grand_score}%${CR_RESET}$(printf '%*s' $((48 - ${#grand_score})) '')${CR_BOLD}${CR_CYAN}║${CR_RESET}"
    echo -e "${CR_BOLD}${CR_CYAN}╚══════════════════════════════════════════════════════════════════╝${CR_RESET}"
    echo ""
    echo -e "  ${CR_DIM}Full report: ${report_file}${CR_RESET}"
    if [ "${total_survived}" -gt 0 ]; then
        echo -e "  ${CR_YELLOW}⚠  ${total_survived} survived mutants found — see report for details.${CR_RESET}"
        echo -e "  ${CR_DIM}  Inspect: .venv/bin/cr-report ${session_dir}/<file>.sqlite${CR_RESET}"
    else
        echo -e "  ${CR_GREEN}✓  All mutants killed — excellent test coverage!${CR_RESET}"
    fi
    echo ""

    # ── Finalize markdown report ──────────────────────────────────────────────
    # Append surviving mutants section
    echo "" >> "${report_file}"
    echo "---" >> "${report_file}"
    echo "" >> "${report_file}"
    echo "## Surviving Mutants (Test Gaps)" >> "${report_file}"
    echo "" >> "${report_file}"

    if [ "${total_survived}" -gt 0 ]; then
        # Write the surviving mutants intro using individual echo calls.
        # NOTE: Do NOT use a heredoc here — macOS bash 3.x has a known parser bug
        # where backtick characters inside heredocs cause "unexpected EOF" errors.
        echo "These mutations were **not caught** by the test suite." >> "${report_file}"
        echo "" >> "${report_file}"
        echo "**Key insight**: Multiple operators at the same occurrence number all target" >> "${report_file}"
        echo "**the same source line**. One new assertion kills all of them simultaneously." >> "${report_file}"
        echo "" >> "${report_file}"
        echo "**How to investigate a surviving line**:" >> "${report_file}"
        echo "" >> "${report_file}"
        echo "    # 1. Apply the mutation:" >> "${report_file}"
        echo "    cd backend" >> "${report_file}"
        echo "    .venv/bin/cosmic-ray apply <source_file> <operator> <occurrence>" >> "${report_file}"
        echo "" >> "${report_file}"
        echo "    # 2. Read the diff:" >> "${report_file}"
        echo "    git diff <source_file>" >> "${report_file}"
        echo "" >> "${report_file}"
        echo "    # 3. Write a test asserting the CORRECT value" >> "${report_file}"
        echo "" >> "${report_file}"
        echo "    # 4. Restore: git restore <source_file>" >> "${report_file}"
        echo "" >> "${report_file}"

        for source_file in "${SOURCE_FILES[@]}"; do
            local safe_name="${source_file//\//_}"
            safe_name="${safe_name//.py/}"
            local session_file="${session_dir}/${safe_name}.sqlite"
            if [ -f "${session_file}" ]; then
                local survived_in_file
                survived_in_file=$(.venv/bin/cr-report "${session_file}" 2>/dev/null | grep -c "TestOutcome.SURVIVED" || true)
                survived_in_file="${survived_in_file//[^0-9]/}"; [ -z "${survived_in_file}" ] && survived_in_file=0
                if [ "${survived_in_file}" -gt 0 ]; then
                    echo "### \`${source_file}\` — ${survived_in_file} surviving mutations" >> "${report_file}"
                    echo "" >> "${report_file}"

                    # Extract surviving operators: format is "<file> <operator_path> <occurrence>"
                    # Group by occurrence to identify unique source lines
                    local raw_survived
                    raw_survived=$(.venv/bin/cr-report "${session_file}" 2>/dev/null | \
                        grep -B1 "TestOutcome.SURVIVED" | grep -v "TestOutcome" | grep -v "^--$" | grep -v "WorkerOutcome")

                    # Count unique occurrence numbers = unique lines to fix
                    local unique_lines
                    unique_lines=$(echo "${raw_survived}" | grep -oE '[0-9]+$' | sort -u | wc -l)
                    unique_lines="${unique_lines//[[:space:]]/}"

                    echo "> **${unique_lines} unique source lines** need new assertions to kill all ${survived_in_file} mutations." >> "${report_file}"
                    echo "> Each group below = one source line. Fix one line = kills all operators in that group." >> "${report_file}"
                    echo "" >> "${report_file}"

                    # Group surviving operators by occurrence number
                    local prev_occurrence=""
                    while IFS= read -r line; do
                        # Line format: "services/sms_quota.py core/ReplaceOperator_X_Y N"
                        [ -z "${line}" ] && continue
                        local occurrence
                        occurrence=$(echo "${line}" | grep -oE '[0-9]+$')
                        [ -z "${occurrence}" ] && continue

                        if [ "${occurrence}" != "${prev_occurrence}" ]; then
                            [ -n "${prev_occurrence}" ] && echo "" >> "${report_file}"
                            echo "**Occurrence ${occurrence}** — apply to see the source line:" >> "${report_file}"
                            echo "\`\`\`bash" >> "${report_file}"
                            local operator_name
                            operator_name=$(echo "${line}" | awk '{print $2}')
                            echo ".venv/bin/cosmic-ray apply ${source_file} ${operator_name} ${occurrence}" >> "${report_file}"
                            echo "\`\`\`" >> "${report_file}"
                            echo "Operators that survived at this line:" >> "${report_file}"
                            prev_occurrence="${occurrence}"
                        fi
                        local short_op
                        short_op=$(echo "${line}" | awk '{print $2}' | sed 's|core/||')
                        echo "- \`${short_op}\`" >> "${report_file}"

                    done <<< "${raw_survived}"

                    echo "" >> "${report_file}"
                fi
            fi
        done
    else
        echo "✅ No surviving mutants — all mutations were killed." >> "${report_file}"
    fi

    # Update summary table in report (replace TBD values)
    sed -i '' \
        -e "s/| Finished | TBD |/| Finished | $(date '+%H:%M:%S') |/" \
        -e "s/| Elapsed | TBD |/| Elapsed | ${tier_elapsed} |/" \
        -e "s/| Total Killed | TBD |/| Total Killed | ${total_killed} |/" \
        -e "s/| Total Survived | TBD |/| Total Survived | ${total_survived} |/" \
        -e "s/| Total Incompetent | TBD |/| Total Incompetent | ${total_incompetent} |/" \
        -e "s/| \*\*Mutation Score\*\* | \*\*TBD\*\* |/| **Mutation Score** | **${grand_score}%** |/" \
        "${report_file}" 2>/dev/null || true

    echo -e "  ${CR_DIM}Report saved: ${report_file}${CR_RESET}"
    echo ""
}
