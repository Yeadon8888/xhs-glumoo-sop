---
name: xhs-glumoo-sop
description: Run the Glumoo Xiaohongshu SOP end-to-end (copy+prompts -> image gen using real SKU refs -> send Feishu review -> publish to Xiaohongshu as only-me -> write report). Includes constraints: 🇲🇾 title prefix, cover badge, Malaysia scenes (indoor+outdoor), multi-image pet consistency.
---

# XHS Glumoo SOP

This skill packages the Glumoo Xiaohongshu SOP so others can reuse it.

## What it does

- Generates post copy + image prompts via the factory script.
- Generates images via Nano Banana Pro using real SKU reference images.
- Sends copy + images to Feishu for human review.
- After explicit approval, publishes to Xiaohongshu (visibility: only me) via MCP.
- Writes a markdown sending report.

## New strategy layer (2026 upgrade)

Before generating content, this SOP now supports a strategy decision layer:

- `discovery` = 发现页打法，适合情绪种草、生活方式、向往感、轻决策。
- `search` = 搜索页打法，适合高决策、高客单、用户带明确问题搜索。

How strategy is chosen:

- Explicit `--strategy discovery|search`
- Or inferred from `--unit-price`, `--user-intent`, `--content-type`, and SKU profile defaults

Extra business inputs now supported:

- `--audience`
- `--pain-point`
- `--scenario`
- `--conversion-goal`
- `--core-keywords`

These inputs are passed into the generation chain as strategy context and also saved into a strategy snapshot file for review.

## Glumoo-specific product strategy (new)

This SOP now carries product-level positioning for the three Glumoo SKUs:

- `SKU1 / 多维力` = 综合型日常养护底盘
  - main use: `discovery + light search`
  - theme bias: 长期主义、少而精、精细化喂养、秩序感、痒点和身份感
  - auto-theme should prefer lifestyle, long-term care, and refined feeding topics
- `SKU2 / 跃力` = 关节 / 老宠 / 高认知决策款
  - main use: `search`
  - theme bias: 成分逻辑、长期补充、价值解释、专业判断、高客单说服
  - auto-theme should prefer old-pet, joint-care, and decision-support topics
- `SKU3 / 畅清` = 肠胃 / 吸收 / 排泄环境管理款
  - main use: `search`
  - theme bias: 问题解决、刚需搜索、高频痛点、日常状态管理
  - auto-theme should prefer gut-care, poop-state, absorption, and home-environment topics

## Content principles (must keep)

- Content must not only dig pain points; it must also scratch itch points.
- Every run should build four things together:
  - pain point
  - itch point
  - value justification
  - identity signal
- `discovery` content should emphasize aspiration, lifestyle, and emotional curiosity.
- `search` content should emphasize keyword intent, scenario fit, decision support, and why the product is worth the higher ticket.

## Copy sanitization layer (new)

After copy is generated, the SOP should run a sanitization pass before review send-out.

What it does:

- Detects risky platform words, direct conversion words, currency/price words, medical-effect words, and extreme claims.
- Rewrites them into safer Xiaohongshu-friendly phrasing while keeping the MY local tone.
- Outputs both:
  - a risk hit list
  - a sanitized send-ready copy file

Sanitization principles:

- Platform words should use symbol isolation or alias replacement.
- Direct money / purchase / DM wording should be softened.
- Medical-effect claims should be rewritten into experience language.
- Extreme words should be downgraded.
- The sanitized version is the default review copy to send out.

## Trusted experience-post guidance (new)

When a post direction is correct but still feels too much like a product-intro/ad, optimize it toward a more credible Xiaohongshu experience post.

Priority adjustments:

- Reduce hard efficacy wording.
  - Avoid expressions like `医药级`, `精准修复`, `肝肾无负担`, `0负担` in final review copy.
  - Prefer safer wording like `有助于日常关节健康支持`, `配方更温和`, `适合长期管理`, `长期执行更安心`.
- Reduce brand-density.
  - Do not repeat the brand name or brand slogans too often.
  - Give more space to decision method, feeding method, and real-life scenario fit.
- Prefer an experience-post structure over a product-promo structure.
  - Recommended skeleton:
    - 1 pain-point opening
    - 3 avoid-pit / selection points
    - 1 practical feeding method
    - 1 medical reminder (`营养品不是药，如已出现明显异常先看兽医`)
- Improve completion/read-through rate.
  - Keep paragraphs shorter.
  - Reduce overfilled selling details.
  - Write more like a believable owner note than a brochure.

Important Glumoo-specific guardrail:

- Even after reducing ad tone, keep the SKU-specific value logic.
- For `SKU2 / 跃力`, the post should still preserve:
  - high-ticket justification
  - ingredient-logic credibility
  - multi-pet household convenience
- Goal is not to turn it into a generic pet post.
- Goal is to turn it into a `Glumoo-style credible experience post`.

## Paths (cross-machine)

This skill is designed to be portable. You provide paths via env vars or CLI flags.

Defaults (can be overridden):

- `XHS_WORKSPACE_WORKER` (default: `/Users/Apple/.openclaw/workspace-worker-xhs`)
- `XHS_DAILY_OUT_BASE` (default: `/Users/Apple/Documents/Glumoo/02_每日内容生成`)
- `XHS_REF_DIR` (default: `/Users/Apple/Documents/Glumoo/产品资料/产品照/三款产品`)

Derived from `XHS_WORKSPACE_WORKER`:
- Factory: `$XHS_WORKSPACE_WORKER/bundles/_unpacked/xhs_glumoo_pipeline/glumoo_factory_v4.6.1_FESTIVAL_FINAL.py`
- Image gen: `$XHS_WORKSPACE_WORKER/bundles/_unpacked/xhs_glumoo_pipeline/skills/nano-banana-pro/scripts/generate_image.py`
- Auto post: `$XHS_WORKSPACE_WORKER/bundles/_unpacked/xhs_glumoo_pipeline/xhs_auto_post.sh`
- Reports dir: `$XHS_WORKSPACE_WORKER/reports`
- Media out: `$XHS_WORKSPACE_WORKER/media_out`

## Reference images

- SKU1: outer `sku1.png`, stick `sku1小包装.png` (box packaging)
- SKU2: outer `sku2.jpg`, stick `sku2小包装.png` (bag packaging)
- SKU3: outer `sku3.jpg`, stick `sku3小包装.png` (bag packaging)

## Creative constraints (must keep)

- Product ↔ copy must match.
  - The SKU chosen for a run is the single source of truth: copy, prompts, and images must all reflect the same SKU and packaging (outer + stick).
  - Never mix SKU visuals or talk about a different SKU in copy.
- Scene tier must be controllable.
  - Scenes should support the target consumer tier: high-end community / normal residential / villa.
  - Support indoor + outdoor rotation.
  - If `--scenario` is provided, treat it as **single source of truth** across all images; do not drift back to other styles.
- Copy should be structured.
  - Prefer short paragraphs; avoid one huge block of text.
  - Use: opening pain point → method/steps → feeding method → result/feel → reminder.
- Avoid sensitive words & hard-sell tone.
  - Use the sanitization layer; keep brand density low.
  - When explaining ingredients, prefer an ingredient-focused post type (科普/测评) rather than forcing it into every post.
- Title must start with `🇲🇾`.
- Cover (image1) must include a fixed badge at bottom-right: `日本品牌｜大马制造`.
- Malaysia scenes must be recognizable.
- Multi-image pet consistency: image1 defines appearance anchors.
- Search strategy should emphasize keyword intent, scenario match, and decision support.
- Discovery strategy should emphasize emotion, aspiration, and visual curiosity.

## How to run

### Review only with strategy explicitly set

```bash
XHS_WORKSPACE_WORKER="/path/to/workspace-worker-xhs" \
XHS_DAILY_OUT_BASE="/path/to/02_每日内容生成" \
XHS_REF_DIR="/path/to/三款产品" \
python3 scripts/run_xhs_sop.py \
  --strategy search \
  --content-type 科普 \
  --sku 3 \
  --theme "多宠家庭解决方案：一包搞定所有" \
  --unit-price 299 \
  --audience "多宠家庭猫狗同养人群" \
  --pain-point "多宠家庭喂养复杂、营养补充难统一" \
  --scenario "马来西亚城市家庭早晚喂养场景" \
  --conversion-goal "完成搜索拦截与购买决策" \
  --core-keywords "多宠家庭营养包, 猫狗一起吃, 宠物营养补充" \
  --review-only
```

### Auto rotate theme/sku/content_type by date

```bash
XHS_WORKSPACE_WORKER="/path/to/workspace-worker-xhs" \
XHS_DAILY_OUT_BASE="/path/to/02_每日内容生成" \
XHS_REF_DIR="/path/to/三款产品" \
python3 scripts/run_xhs_sop.py \
  --auto-theme \
  --auto-sku \
  --auto-content-type \
  --themes-json ./config/themes.json \
  --unit-price 159 \
  --user-intent discovery \
  --audience "年轻养宠女生" \
  --pain-point "想补营养但怕麻烦" \
  --scenario "居家轻松喂养" \
  --conversion-goal "激发兴趣与收藏" \
  --core-keywords "宠物营养, 日常喂养, 多宠家庭" \
  --review-only
```

### After approval (publish)

```bash
python3 scripts/run_xhs_sop.py \
  --strategy search \
  --content-type 科普 \
  --sku 3 \
  --theme "多宠家庭解决方案：一包搞定所有" \
  --publish
```

## Daily default SOP (2026-03-15 locked)

This skill now also carries a locked daily-default SOP for Glumoo pet content generation.

Daily default behavior:
- Rotate SKU by day
- Rotate pet breed by day
- Rotate Malaysia premium scenes by day
- Prefer owner-in-frame natural interaction
- Allow subtle premium car exposure as a background identity cue
- Keep copy / prompts / packaging / pet breed / appearance anchors fully aligned

Locked breed pools:
- Dogs: 玩具体贵宾（泰迪风）, 博美, 比熊, 金毛, 雪纳瑞
- Cats: 英短, 布偶, 波斯, 缅因, 曼赤肯

Locked scene persona:
- Malaysia high-end Chinese pet-owning household
- City = high-end condo / premium community / luxury apartment
- Low-density = landed villa / premium garden house
- Home should feel clean, aesthetic, ordered, and affluent-but-not-showy

Locked image rules:
- Cover must contain a strong hook copy
- Each image should have its own short text
- Same post must use one pet breed only
- Image1 defines appearance anchors; later images must reuse them verbatim
- Packaging must strictly match current SKU
- Powder / feeding / mixing scenes must use the correct stick pack of the current SKU

Owner-in-frame rules:
- Prefer owner feeding, mixing, walking, accompanying, or interacting naturally
- Avoid all-images-as-isolated-pet glamour shots

Premium car rule:
- A high-end SUV/sedan may appear in driveway/car porch/condo basement scenes
- Only as a subtle background cue; never as the subject

See also:
- `PET_SCENE_PERSONA_SOP.md`

## Notes

- `--publish` assumes Xiaohongshu login is already valid.
- This skill does not bypass human review; it only publishes when `--publish` is used.
- Strategy inputs improve generation context, but the upstream factory script still determines the base copy structure; if needed, upgrade the factory prompt template next.
- Each run now records a `00_策略快照.json` file in the output folder for auditability.
