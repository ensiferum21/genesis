#!/bin/bash
# Resolve the base image digest and write it into containers/Containerfile and
# containers/container_digests.json. Requires registry access.
set -euo pipefail
cd "$(dirname "$0")/.."
image=python:3.13-slim-bookworm
digest=$(docker buildx imagetools inspect "$image" --format '{{json .Manifest}}' | python3 -c 'import json,sys;print(json.load(sys.stdin)["digest"])')
sed -i "s#python:3.13-slim-bookworm@sha256:[A-Za-z0-9_]*#${image}@${digest}#" containers/Containerfile
printf '{"base": "%s@%s"}\n' "$image" "$digest" > containers/container_digests.json
echo "pinned $image@$digest"
