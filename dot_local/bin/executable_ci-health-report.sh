#!/bin/bash
# CI Health Report — standalone version of .github/workflows/ci-health-report.yml
#
# Required environment variables:
#   GH_TOKEN   — GitHub personal access token with actions:read
#   GH_REPO    — owner/repo (e.g. canonical/microceph)
#
# Optional environment variables:
#   LOOKBACK_DAYS — number of days to look back (default: 30)
#   OUTPUT_FILE   — file to write the report to (default: ci-health-report.md)

set -euo pipefail

: "${GH_TOKEN:?GH_TOKEN must be set}"
: "${GH_REPO:?GH_REPO must be set}"
LOOKBACK_DAYS="${LOOKBACK_DAYS:-30}"

lookback_date=$(date -u -d "${LOOKBACK_DAYS} days ago" +%Y-%m-%dT%H:%M:%SZ)
now=$(date -u +%Y-%m-%dT%H:%M:%SZ)

echo "Fetching workflow runs since ${lookback_date}..." >&2

# Fetch all completed runs within the lookback window (paginated)
page=1
runs_json="[]"
while true; do
  batch=$(gh api \
    "/repos/{owner}/{repo}/actions/runs?status=completed&created=>=${lookback_date}&per_page=100&page=${page}" \
    --jq '.workflow_runs | map({id: .id, name: .name})')

  count=$(echo "${batch}" | jq 'length')
  if [ "${count}" -eq 0 ]; then
    break
  fi

  runs_json=$(echo "${runs_json}" "${batch}" | jq -s '.[0] + .[1]')
  page=$((page + 1))
done

total_runs=$(echo "${runs_json}" | jq 'length')
echo "Found ${total_runs} completed runs." >&2

if [ "${total_runs}" -eq 0 ]; then
  echo "No runs found in the lookback window. Skipping report." >&2
  exit 0
fi

# Fetch jobs for each run and build a TSV of workflow_name, job_name, conclusion
jobs_tsv=$(mktemp)

echo "${runs_json}" | jq -c '.[]' | while read -r run; do
  run_id=$(echo "${run}" | jq -r '.id')
  workflow_name=$(echo "${run}" | jq -r '.name')

  gh api \
    "/repos/{owner}/{repo}/actions/runs/${run_id}/jobs?per_page=100" \
    --jq ".jobs[] | [\"${workflow_name}\", .name, .conclusion] | @tsv" \
    >> "${jobs_tsv}" || true
done

if [ ! -s "${jobs_tsv}" ]; then
  echo "No job data collected. Skipping report." >&2
  rm -f "${jobs_tsv}"
  exit 0
fi

# Aggregate job data with awk: group by workflow+job, count runs and failures
report_table=$(awk -F'\t' '
{
  key = $1 "\t" $2
  total[key]++
  if ($3 == "failure") failures[key]++
}
END {
  for (key in total) {
    f = (key in failures) ? failures[key] : 0
    rate = (f / total[key]) * 100
    printf "%s\t%d\t%d\t%.1f\n", key, total[key], f, rate
  }
}' "${jobs_tsv}" | sort -t$'\t' -k5 -rn)

# Build the markdown report

# Job Failure Rates table
table_rows=""
while IFS=$'\t' read -r wf job runs fails rate; do
  table_rows="${table_rows}| ${wf} | ${job} | ${runs} | ${fails} | ${rate}% |
"
done <<< "${report_table}"

# Top 5 Most Failing Jobs (by absolute failure count)
top5=$(echo "${report_table}" | sort -t$'\t' -k4 -rn | head -5)
top5_list=""
rank=1
while IFS=$'\t' read -r wf job runs fails rate; do
  [ -z "${wf}" ] && continue
  top5_list="${top5_list}${rank}. **${wf} / ${job}** — ${fails} failures (${rate}%)
"
  rank=$((rank + 1))
done <<< "${top5}"

# Summary stats
total_job_runs=$(awk -F'\t' '{sum += $3} END {print sum}' <<< "${report_table}")
total_failures=$(awk -F'\t' '{sum += $4} END {print sum}' <<< "${report_table}")
if [ "${total_job_runs}" -gt 0 ]; then
  overall_rate=$(awk "BEGIN {printf \"%.1f\", (${total_failures}/${total_job_runs})*100}")
else
  overall_rate="0.0"
fi

report="## CI Health Report

_Last ${LOOKBACK_DAYS} days — generated ${now}_

### Job Failure Rates

| Workflow | Job | Runs | Failures | Rate |
|----------|-----|------|----------|------|
${table_rows}
### Top 5 Most Failing Jobs

${top5_list}
### Summary

- **Total job runs:** ${total_job_runs}
- **Total failures:** ${total_failures}
- **Overall failure rate:** ${overall_rate}%"

# Write to file
OUTPUT_FILE="${OUTPUT_FILE:-ci-health-report.md}"
echo "${report}" > "${OUTPUT_FILE}"
echo "Report written to ${OUTPUT_FILE}" >&2

# Clean up
rm -f "${jobs_tsv}"

echo "Report generated successfully." >&2
