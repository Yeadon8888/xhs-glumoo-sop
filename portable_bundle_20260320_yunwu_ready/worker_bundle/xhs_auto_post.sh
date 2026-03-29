#!/usr/bin/env bash
set -euo pipefail

ROOT="/Users/Apple/.openclaw/workspace-worker-xhs"
cd "$ROOT"

# Inputs can be overridden by env vars.
TITLE="${XHS_TITLE:-夏天金毛不爱喝水？我用这招骗水成功了}"
VISIBILITY="${XHS_VISIBILITY:-仅自己可见}"

# Copy: keep hashtags out of content; MCP uses tags.
CONTENT=${XHS_CONTENT:-$'Aiyo… Malaysia 天气一热起来，我家金毛出门走两圈就 panting 到像小风扇，可是回到家 water bowl 摆在那边，它还可以当没看到。\n\n我以前真的以为它不渴，后来发现不是咯——它是觉得 plain water 很 boring。\n但这种 hot + humid 的季节，补水真的很重要，不然便便容易偏硬，整只狗也会看起来没什么 mood。\n\n最近我用一个很 “cheat” 的方法：\n把 Glumoo 跃力用温水冲开（大概 30–50ml），变成淡淡香味的 “broth water”。它闻到味道就自己走过来，喝完还会舔碗那种，真的 steady。\n\n我自己喜欢的点很 simple：\n- 味道香：挑嘴狗也比较肯\n- 很 flexible：冲水喝 / 拌粮 / 手喂都可以\n- 日常更省心：我不求什么立刻“回春”，只希望它夏天状态稳一点点\n\n如果你家毛孩也是 “水盆装饰派”，可以 try 这个思路：先让它愿意喝，之后再慢慢把水量加回正常。\n\n（温馨提醒：如果持续不喝水、精神差，记得 consult vet 啊。）\n\n日本品牌，马来西亚制造（Japanese brand, Made in Malaysia）\n纯植物基发酵 NAG（plant-based fermented NAG）\nGlumoo 植物基发酵，给他0负担的爱'}

TAGS_JSON=${XHS_TAGS_JSON:-'["Glumoo","Glumoo氨糖羊奶粉","Glumoo关节守护","GlumooNAG","宠物羊奶粉","金毛","狗狗补水","骗水神器","马来西亚养宠","夏季养狗"]'}

IMAGES_JSON=${XHS_IMAGES_JSON:-$(python3 - <<'PY'
import json
paths = [
  "/Users/Apple/.openclaw/workspace-worker-xhs/media_out/2026-03-01-glumoo-yueli-hydration-01.png",
  "/Users/Apple/.openclaw/workspace-worker-xhs/media_out/2026-03-01-glumoo-yueli-hydration-02.png",
  "/Users/Apple/.openclaw/workspace-worker-xhs/media_out/2026-03-01-glumoo-yueli-hydration-03.png",
  "/Users/Apple/.openclaw/workspace-worker-xhs/media_out/2026-03-01-glumoo-yueli-hydration-04.png",
]
print(json.dumps(paths, ensure_ascii=False))
PY
)}

python3 - <<PY
import json, subprocess
args = {
  "title": "${TITLE}",
  "content": """${CONTENT}""",
  "images": json.loads('''${IMAGES_JSON}'''),
  "tags": json.loads('''${TAGS_JSON}'''),
  "visibility": "${VISIBILITY}",
}
proc = subprocess.run([
  "python3", "scripts/xhs_mcp_bridge.py", "publish",
  "--config", "config/mcporter.json",
  "--out-dir", "${ROOT}/media_out",
  "--timeout-ms", "180000",
  "--payload-json", json.dumps(args, ensure_ascii=False)
], capture_output=True, text=True)
if proc.stdout:
  print(proc.stdout.strip())
if proc.stderr:
  print(proc.stderr.strip())
if proc.returncode != 0:
  raise SystemExit(proc.returncode)
PY
