#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
WORKSPACE_DIR="$(cd "$SCRIPT_DIR/../../.." && pwd)"

export XHS_WORKSPACE_WORKER="${XHS_WORKSPACE_WORKER:-/Users/Apple/.openclaw/workspace-worker-xhs}"
export XHS_DAILY_OUT_BASE="${XHS_DAILY_OUT_BASE:-/Users/Apple/Documents/Glumoo/02_每日内容生成}"
export XHS_REF_DIR="${XHS_REF_DIR:-/Users/Apple/Documents/Glumoo/产品资料/产品照/三款产品}"

# Locked stable defaults: image gen goes to Yunwu only.
export XHS_IMAGE_BASE_URL="${XHS_IMAGE_BASE_URL:-https://yunwu.ai}"
export XHS_IMAGE_MODEL="${XHS_IMAGE_MODEL:-gemini-3.1-flash-image-preview}"
export XHS_IMAGE_ASPECT_RATIO="${XHS_IMAGE_ASPECT_RATIO:-4:5}"

# Locked text defaults for the daily SOP.
export XHS_TEXT_BASE_URL="${XHS_TEXT_BASE_URL:-https://yunwu.ai}"
export XHS_TEXT_MODEL="${XHS_TEXT_MODEL:-models/gemini-3.1-flash-lite-preview}"

if [[ -z "${XHS_IMAGE_API_KEY:-}" ]]; then
  echo "Missing XHS_IMAGE_API_KEY" >&2
  exit 1
fi

if [[ -z "${XHS_TEXT_API_KEY:-}" && -z "${GEMINI_API_KEY:-}" && -z "${GOOGLE_API_KEY:-}" ]]; then
  echo "Missing text API key: set XHS_TEXT_API_KEY (preferred) or GEMINI_API_KEY / GOOGLE_API_KEY" >&2
  exit 1
fi

python3 "$WORKSPACE_DIR/skills/xhs-glumoo-sop/scripts/run_xhs_sop.py" \
  --auto-theme \
  --auto-sku \
  --auto-content-type \
  --review-only \
  "$@"
