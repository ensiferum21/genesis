#!/bin/bash
# Push the state of a running study (its rows so far and the research plane's live directory) to the branch
# wip/<study>, so that another session can resume it if this one stops. It never touches the study's worktree.
# Usage: snapshot_running_study.sh STUDY OUT_DIR WORK_DIR      (e.g. b20r187 /home/claude/r187-wt/evidence/... \
#        /home/claude/work/scratch-foundry/b20r187)
study=$1; out=$2; work=$3
repo=${GENESIS_REPO:-/home/claude/work/genesis}; wt=/home/claude/wip-$study
if [ ! -d "$wt" ]; then
  git -C "$repo" worktree add -q --detach "$wt" HEAD && git -C "$wt" checkout -q --orphan "wip/$study" && git -C "$wt" rm -rqf . && rm -rf "$wt"/*
fi
rm -rf "$wt/evidence" "$wt/research_plane"; mkdir -p "$wt/evidence" "$wt/research_plane"
cp -r "$out"/. "$wt/evidence/"
for f in rows.jsonl episodes.jsonl; do                 # keep whole lines only (a row may be half-written)
  [ -f "$wt/evidence/$f" ] && python3 -I -c "
import json, sys
p = sys.argv[1]; keep = []
for ln in open(p):
    try:
        json.loads(ln); keep.append(ln if ln.endswith(chr(10)) else ln + chr(10))
    except ValueError:
        break
open(p, 'w').writelines(keep)" "$wt/evidence/$f"
done
cp -r "$work/genesis-research"/. "$wt/research_plane/" 2>/dev/null
tail -20 /home/claude/chain.log > "$wt/chain_tail.log"
cat > "$wt/README.md" <<EOT
# A snapshot of the running study $study (not a record)

Taken $(date -Is). \`evidence/\` is the study's output directory so far (its rows are complete episodes only);
\`research_plane/\` is the research plane's live directory (Genesis's library as it grows). To resume in another
container: check out the study's preregistration commit (see docs/HANDOVER.md), put \`evidence/\` at the output path
and \`research_plane/\` at <work>/genesis-research (the script's \`work\` directory), and run the same command
(scripts/ops/run_slice.sh): the script skips recorded rows. Disclose the move in the record.
EOT
git -C "$wt" add -A && git -C "$wt" commit -q -m "Snapshot of the running $study, $(date -Is) (not a record)

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>" && git -C "$wt" push -q -f github "wip/$study" 2>&1 | tail -1
echo "snapshot $(wc -l < $out/rows.jsonl) rows $(date -Is)"
