#!/usr/bin/env python3

import argparse
import datetime
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Optional


def env_path(name: str, default: str) -> Path:
    return Path(os.environ.get(name, default)).expanduser()


SKILL_DIR = Path(__file__).resolve().parents[1]
AGENT_WORKSPACE = Path(__file__).resolve().parents[3]
DEFAULT_THEMES_JSON = SKILL_DIR / "config/themes.json"

WORKSPACE_WORKER = env_path("XHS_WORKSPACE_WORKER", "/Users/Apple/.openclaw/workspace-worker-xhs")
DAILY_OUT_BASE = env_path("XHS_DAILY_OUT_BASE", "/Users/Apple/Documents/Glumoo/02_每日内容生成")
REF_DIR = env_path("XHS_REF_DIR", "/Users/Apple/Documents/Glumoo/产品资料/产品照/三款产品")
FEISHU_OUTBOX_BASE = env_path("XHS_FEISHU_OUTBOX_BASE", "/Users/Apple/.openclaw/media/outbox/feishu-longxia-dabao")

FACTORY = WORKSPACE_WORKER / "bundles/_unpacked/xhs_glumoo_pipeline/glumoo_factory_v4.6.1_FESTIVAL_FINAL.py"
IMAGE_GEN = WORKSPACE_WORKER / "bundles/_unpacked/xhs_glumoo_pipeline/skills/nano-banana-pro/scripts/generate_image.py"
AUTO_POST = WORKSPACE_WORKER / "bundles/_unpacked/xhs_glumoo_pipeline/xhs_auto_post.sh"
REPORT_DIR = WORKSPACE_WORKER / "reports"
MEDIA_OUT_BASE = WORKSPACE_WORKER / "media_out"

SKU_REFS = {
    1: {"outer": REF_DIR / "sku1.png", "stick": REF_DIR / "sku1小包装.png", "pack": "box"},
    2: {"outer": REF_DIR / "sku2.jpg", "stick": REF_DIR / "sku2小包装.png", "pack": "bag"},
    3: {"outer": REF_DIR / "sku3.jpg", "stick": REF_DIR / "sku3小包装.png", "pack": "bag"},
}

DISCOVERY_TYPES = {"种草", "故事", "体验", "挑战", "转化"}
SEARCH_TYPES = {"科普", "对比", "测评", "避雷", "教程", "搜索"}
ALL_CONTENT_TYPES = sorted(DISCOVERY_TYPES | SEARCH_TYPES)

SENSITIVE_REPLACEMENTS = [
    {"variants": ("Shopee", "shopee"), "replacement": "橙/色/软/件", "mode": "word"},
    {"variants": ("Lazada", "lazada"), "replacement": "蓝/色/软/件", "mode": "word"},
    {"variants": ("TikTok", "tiktok"), "replacement": "某音", "mode": "word"},
    {"variants": ("抖音",), "replacement": "某音", "mode": "plain"},
    {"variants": ("link", "Link"), "replacement": "🔗", "mode": "word"},
    {"variants": ("链接",), "replacement": "🔗", "mode": "plain"},
    {"variants": ("RM", "rm"), "replacement": "💰位", "mode": "currency"},
    {"variants": ("价格", "价钱", "多少钱", "钱"), "replacement": "💰位", "mode": "plain"},
    {"variants": ("优惠", "折扣", "促销"), "replacement": "羊毛", "mode": "plain"},
    {"variants": ("加我", "私信", "联系我"), "replacement": "💬我", "mode": "plain"},
    {"variants": ("下单", "购买", "订购"), "replacement": "拿走", "mode": "plain"},
    {"variants": ("治疗", "根治"), "replacement": "舒缓", "mode": "plain"},
    {"variants": ("过敏",), "replacement": "对敏感肌友好", "mode": "plain"},
    {"variants": ("增强免疫力", "提高免疫力"), "replacement": "身体棒棒", "mode": "plain"},
    {"variants": ("第一",), "replacement": "NO.1", "mode": "plain"},
    {"variants": ("100%",), "replacement": "超", "mode": "plain"},
]

HARD_RISK_REWRITES = [
    (r"医药级", "高规格"),
    (r"精准修复", "更有针对性的日常支持"),
    (r"吸收率优", "更适合长期管理"),
    (r"肝肾无负担", "配方更温和"),
    (r"0负担", "更安心"),
    (r"提高免疫力", "帮助维持日常状态"),
    (r"增强免疫力", "帮助维持日常状态"),
]

SKU_DEFAULTS = {
    1: {
        "name": "多维力",
        "positioning": "综合型日常养护底盘",
        "traffic_focus": "discovery",
        "pain_points": ["喂养太散", "补充太杂", "不会搭配", "缺少长期基础养护"],
        "itch_points": ["更轻松的喂养方式", "更讲究的长期管理", "少而精的营养选择", "更有秩序的养宠日常"],
        "identity_signal": "高认知家长的长期管理型选择",
        "value_justification": "一包覆盖多维支持，减少重复购买和乱搭配",
        "frameworks": ["场景种草型", "故事叙事型", "身份信任型"],
    },
    2: {
        "name": "跃力",
        "positioning": "关节/老宠/高认知决策款",
        "traffic_focus": "search",
        "pain_points": ["老宠行动力下降", "担心关节和长期负担", "怕买错乱补", "不知道怎么选更稳的长期关节方案"],
        "itch_points": ["更讲究的家长身份", "有判断逻辑的产品选择", "让宠物老得更轻松一点", "从随便补升级到精细化养护"],
        "identity_signal": "懂成分逻辑和长期补充的高认知家长",
        "value_justification": "不是泛泛补充，而是更适合长期关节养护的高客单逻辑型产品",
        "frameworks": ["对比评测型", "教程干货型", "身份信任型"],
    },
    3: {
        "name": "畅清",
        "positioning": "肠胃/吸收/排泄环境管理款",
        "traffic_focus": "search",
        "pain_points": ["便便状态不稳", "肠胃敏感", "吃进去但状态一般", "排泄气味重", "不知道怎么做更友好的日常肠胃管理"],
        "itch_points": ["更干净的家里环境", "更轻松省事的喂养日常", "更稳定的宠物状态", "更会管理日常状态的家长感"],
        "identity_signal": "会管理宠物整体日常状态的家长",
        "value_justification": "把吃进去、吸收掉、排出来、家里更舒服这一整条链路串起来",
        "frameworks": ["问题解决型", "教程干货型", "身份信任型"],
    },
}


def run(cmd, env=None, timeout=None):
    subprocess.check_call(cmd, env=env, timeout=timeout)


def run_capture_filtered(cmd, env=None, timeout=None, stdout_filter=None):
    proc = subprocess.run(
        cmd,
        env=env,
        timeout=timeout,
        check=False,
        capture_output=True,
        text=True,
        errors="replace",
    )

    if proc.stdout:
        for line in proc.stdout.splitlines():
            if stdout_filter and stdout_filter(line):
                continue
            print(line)

    if proc.stderr:
        for line in proc.stderr.splitlines():
            print(line, file=sys.stderr)

    if proc.returncode != 0:
        raise subprocess.CalledProcessError(proc.returncode, cmd)

    return proc


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8").strip()


def split_tags_and_content(body: str):
    hashtags = re.findall(r"#\S+", body)
    tags = [h.lstrip("#") for h in hashtags if h.strip("#")]
    content = re.sub(r"\s*#\S+", "", body).strip()
    content = re.sub(r"\n{3,}", "\n\n", content)

    # Encourage structured copy: keep paragraphs short and readable.
    # If content is a single long paragraph, insert breaks on strong sentence boundaries.
    lines = [ln.rstrip() for ln in content.splitlines()]
    if len(lines) <= 2 and len(content) >= 200:
        content = re.sub(r"(。|！|\!|\?|？)(?=\S)", r"\1\n\n", content)
        content = re.sub(r"\n{3,}", "\n\n", content).strip()

    return tags, content


def safe_title(title: str) -> str:
    title = title.strip().replace("*", "")
    if not title.startswith("🇲🇾"):
        title = "🇲🇾" + title
    if len(title) > 14:
        title = title[:14]
    return title


def load_themes(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def pick_from_rotation(items, date_str: str):
    d = datetime.date.fromisoformat(date_str)
    idx = d.toordinal() % len(items)
    return items[idx]


def infer_strategy(unit_price: Optional[float], user_intent: Optional[str], content_type: Optional[str], sku_profile: Optional[dict] = None) -> str:
    normalized_intent = (user_intent or "").strip().lower()
    if normalized_intent in {"搜索", "search", "决策", "高决策", "人找货"}:
        return "search"
    if normalized_intent in {"发现", "discovery", "种草", "冲动消费", "货找人"}:
        return "discovery"
    if sku_profile and sku_profile.get("traffic_focus") in {"search", "discovery"}:
        if sku_profile["traffic_focus"] == "search" and unit_price is not None and unit_price >= 200:
            return "search"
        if sku_profile["traffic_focus"] == "discovery" and content_type in DISCOVERY_TYPES:
            return "discovery"
    if unit_price is not None and unit_price > 200:
        return "search"
    if content_type in SEARCH_TYPES:
        return "search"
    if content_type in DISCOVERY_TYPES:
        return "discovery"
    if sku_profile and sku_profile.get("traffic_focus") in {"search", "discovery"}:
        return sku_profile["traffic_focus"]
    return "discovery"


def get_sku_profile(theme_cfg: Optional[dict], sku: int) -> dict:
    if theme_cfg:
        raw = theme_cfg.get("sku_profiles", {}).get(str(sku))
        if raw:
            return raw
    return SKU_DEFAULTS[sku]


def choose_auto(theme_cfg: dict, date_str: str, content_type: Optional[str], sku: Optional[int]):
    rotation = theme_cfg.get("rotation", {})

    if content_type is None:
        cts = rotation.get("content_types") or ["科普", "体验", "故事", "挑战", "转化"]
        content_type = pick_from_rotation(cts, date_str)

    if sku is None:
        skus = rotation.get("skus") or [3, 1, 2]
        sku = int(pick_from_rotation(skus, date_str))

    sku_cfg = (theme_cfg.get("sku_profiles") or {}).get(str(sku), {})
    sku_theme_map = sku_cfg.get("theme_map") or {}
    themes_map = theme_cfg.get("themes", {})
    candidates = sku_theme_map.get(content_type) or themes_map.get(content_type) or ["多宠家庭解决方案：一包搞定所有"]
    theme = pick_from_rotation(candidates, date_str)

    return theme, content_type, sku


def find_latest_daily_folder(date_str: str, theme: str, sku: int, daily_out_base: Path) -> Path:
    patterns = [
        f"{date_str}_{theme}_SKU_{sku}_v4.6.2",
        f"{date_str}_{theme}_SKU_{sku}_v4.6.1",
        f"{date_str}_{theme}_SKU_{sku}_v*",
        f"{date_str}_{theme}_*_v4.6.2",
        f"{date_str}_{theme}_*_v4.6.1",
        f"{date_str}_{theme}_*_v*",
    ]
    candidates = []
    for patt in patterns:
        candidates.extend(daily_out_base.glob(patt))
    filtered = []
    for path in set(candidates):
        name = path.name
        if theme not in name:
            continue
        if f"SKU_{sku}" in name or any(alias in name for alias in ["多维力", "跃力", "畅清"]):
            filtered.append(path)
    candidates = sorted(filtered or set(candidates), key=lambda p: p.stat().st_mtime, reverse=True)
    if not candidates:
        raise FileNotFoundError(f"No daily output folder found for theme={theme}, sku={sku} under {daily_out_base}")
    return candidates[0]


def extract_prompt_blocks_from_text(text: str):
    if "【绘图指令生成失败】" in text:
        return []

    parts = re.split(r"(?=\n\[图片\d+\])|(?=\A\[图片1/封面图\])", text)
    return [p.strip() for p in parts if p.strip().startswith("[图片")]


def build_strategy_brief(strategy: str, args, sku_profile: dict) -> str:
    audience = args.audience or "泛养宠家庭"
    pain_point = args.pain_point or " / ".join(sku_profile.get("pain_points", [])) or "多宠家庭喂养与营养管理"
    scenario = args.scenario or "马来西亚多宠家庭日常"
    conversion_goal = args.conversion_goal or ("激发兴趣与收藏" if strategy == "discovery" else "完成搜索拦截与购买决策")
    keywords = args.core_keywords or "Glumoo, 多宠家庭, 宠物营养"
    itch_points = " / ".join(sku_profile.get("itch_points", []))
    frameworks = " / ".join(sku_profile.get("frameworks", []))

    lines = [
        f"XHS_STRATEGY={strategy}",
        f"XHS_SKU_NAME={sku_profile.get('name', '')}",
        f"XHS_SKU_POSITIONING={sku_profile.get('positioning', '')}",
        f"XHS_AUDIENCE={audience}",
        f"XHS_PAIN_POINT={pain_point}",
        f"XHS_ITCH_POINT={itch_points}",
        f"XHS_IDENTITY_SIGNAL={sku_profile.get('identity_signal', '')}",
        f"XHS_VALUE_JUSTIFICATION={sku_profile.get('value_justification', '')}",
        f"XHS_FRAMEWORKS={frameworks}",
        f"XHS_SCENARIO={scenario}",
        f"XHS_CONVERSION_GOAL={conversion_goal}",
        f"XHS_CORE_KEYWORDS={keywords}",
        "XHS_CONTENT_PRINCIPLE=内容不能只挖痛点，还要同时挠痒点，建立高价值感和身份认同。",
    ]

    if strategy == "search":
        lines.extend(
            [
                "XHS_STRATEGY_RULE=搜索页打法：围绕明确需求、细分人群、痛点场景来写，优先转化，不追泛流量。",
                "XHS_COPY_REQUIREMENT=标题和正文优先出现核心词+细分人群+痛点，强调解决方案、对比、教程、结果感，并解释为什么更值得买。",
            ]
        )
    else:
        lines.extend(
            [
                "XHS_STRATEGY_RULE=发现页打法：围绕情绪共鸣、向往感、视觉吸引和轻决策体验来写，先激发兴趣。",
                "XHS_COPY_REQUIREMENT=标题和正文优先强调生活方式、场景代入、轻松种草、身份感和评论区互动承接。",
            ]
        )

    return "\n".join(lines)


def sanitize_copy_text(text: str, sku_profile: Optional[dict] = None):
    sanitized = text
    hits = []
    for rule in SENSITIVE_REPLACEMENTS:
        replacement = rule["replacement"]
        mode = rule.get("mode", "plain")
        for needle in rule["variants"]:
            if mode == "word":
                pattern = re.compile(rf"\b{re.escape(needle)}\b")
            elif mode == "currency":
                pattern = re.compile(rf"(?<![A-Za-z]){re.escape(needle)}(?![A-Za-z])")
            else:
                pattern = re.compile(re.escape(needle))
            sanitized, count = pattern.subn(replacement, sanitized)
            if count:
                hits.append({"source": needle, "replacement": replacement, "count": count, "mode": mode})

    for pattern_text, replacement in HARD_RISK_REWRITES:
        pattern = re.compile(pattern_text)
        sanitized, count = pattern.subn(replacement, sanitized)
        if count:
            hits.append({"source": pattern_text, "replacement": replacement, "count": count, "mode": "risk_rewrite"})

    sanitized, count = re.subn(r"(?<=[^A-Za-z])最(?=[^A-Za-z])|^最(?=[^A-Za-z])|(?<=[^A-Za-z])最$", "敲", sanitized)
    if count:
        hits.append({"source": "最", "replacement": "敲", "count": count, "mode": "bounded_cn"})

    sanitized = sanitized.replace("免疫系统", "身体状态")
    sanitized = sanitized.replace("治好", "舒服一点")

    if sku_profile and sku_profile.get("name"):
        brand_name = "Glumoo"
        name = sku_profile.get("name")
        brand_hits = 0

        def reduce_brand(match):
            nonlocal brand_hits
            brand_hits += 1
            return match.group(0) if brand_hits <= 2 else name

        sanitized = re.sub(rf"{brand_name}\s*的?\s*{name}|{brand_name}", reduce_brand, sanitized)
        if brand_hits > 2:
            hits.append({"source": brand_name, "replacement": name, "count": brand_hits - 2, "mode": "brand_limit"})

    medical_line = "（如已出现明显跛行/疼痛，建议先就医评估）"
    if medical_line not in sanitized:
        if sanitized.endswith("\n"):
            sanitized += medical_line + "\n"
        else:
            sanitized += "\n\n" + medical_line
        hits.append({"source": "medical_disclaimer", "replacement": medical_line, "count": 1, "mode": "append"})

    return sanitized, hits


def maybe_write_strategy_snapshot(out_dir: Path, strategy: str, args, sku_profile: dict, sanitize_hits: Optional[list] = None):
    snapshot = {
        "strategy": strategy,
        "sku_name": sku_profile.get("name"),
        "sku_positioning": sku_profile.get("positioning"),
        "traffic_focus": sku_profile.get("traffic_focus"),
        "unit_price": args.unit_price,
        "user_intent": args.user_intent,
        "audience": args.audience,
        "pain_point": args.pain_point,
        "itch_points": sku_profile.get("itch_points"),
        "identity_signal": sku_profile.get("identity_signal"),
        "value_justification": sku_profile.get("value_justification"),
        "frameworks": sku_profile.get("frameworks"),
        "scenario": args.scenario,
        "conversion_goal": args.conversion_goal,
        "core_keywords": args.core_keywords,
        "sanitize_hits": sanitize_hits or [],
    }
    path = out_dir / "00_策略快照.json"
    path.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def enforce_scene_rules(block: str, idx: int, strategy: str, args) -> str:
    scenario = (args.scenario or "马来西亚多宠家庭日常").strip()
    pain_point = args.pain_point or "多宠家庭喂养与营养管理"
    keywords = args.core_keywords or "Glumoo, 多宠家庭, 宠物营养"

    # Scene tier rotation rule:
    # - If user provides scenario, treat it as single source of truth.
    # - Otherwise default to MY normal housing cues.
    if scenario:
        block += f"\n- 场景强制(单一真源): {scenario}（所有图片必须一致遵守，不得回退到其他住宅/院子/走廊风格）"
        block += "\n- 场景禁止(硬禁): 铁花窗Grille/老旧走廊/乡村院子/复古阳台/铁门铁栅/破旧家具/杂乱背景（除非场景真源明确要求）"
    else:
        block += "\n- 场景强制: 马来西亚可识别住宅/街区（铁花窗Grille/吊扇/复古花砖或水磨石/排屋车棚走廊/热带植物/强日照阴影，至少1-2项）"

    if strategy == "search":
        block += f"\n- 搜索页强化: 强化真实使用问题、解决路径与结果感，围绕痛点‘{pain_point}’表达。"
        block += f"\n- 搜索关键词暗示: 画面和道具尽量贴近这些搜索意图：{keywords}。"
    else:
        block += "\n- 发现页强化: 强调第一眼吸引力、情绪氛围、轻松种草和生活方式代入。"

    if idx == 1:
        block += "\n- 角标强制: 右下角固定角标/贴纸‘日本品牌｜大马制造’（清晰可读，位置固定）"
        block += "\n- 多图一致性: 这一张定义宠物外观锚点、产品主体比例和主色调，后续图片必须延续。"

    return block


def stage_feishu_send_images(image_paths, out_dir: Path):
    out_dir.mkdir(parents=True, exist_ok=True)
    staged_items = []
    for idx, image_path in enumerate(image_paths, 1):
        src = Path(image_path)
        if not src.exists():
            raise FileNotFoundError(f"Missing generated image for Feishu send staging: {src}")
        suffix = src.suffix.lower() or ".png"
        prefix = "01_cover_ref" if idx == 1 else f"{idx:02d}"
        dest = out_dir / f"{prefix}{suffix}"
        shutil.copy2(src, dest)
        staged_items.append(
            {
                "source": str(src),
                "staged": str(dest),
            }
        )
    return staged_items


def is_unsafe_worker_media_line(line: str, worker_media_dir: Path):
    stripped = line.strip()
    if not stripped:
        return False

    for prefix in ("MEDIA:", "Image saved:"):
        if not stripped.startswith(prefix):
            continue
        candidate = stripped[len(prefix):].strip()
        return candidate.startswith(str(worker_media_dir))

    return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default=datetime.date.today().strftime("%Y-%m-%d"))
    ap.add_argument("--theme")
    ap.add_argument("--auto-theme", action="store_true")
    ap.add_argument("--themes-json", default=str(DEFAULT_THEMES_JSON))

    ap.add_argument("--sku", type=int, choices=[1, 2, 3])
    ap.add_argument("--auto-sku", action="store_true")

    ap.add_argument("--content-type", default="科普", choices=ALL_CONTENT_TYPES)
    ap.add_argument("--auto-content-type", action="store_true")

    ap.add_argument("--strategy", choices=["discovery", "search"])
    ap.add_argument("--unit-price", type=float)
    ap.add_argument("--user-intent")
    ap.add_argument("--audience")
    ap.add_argument("--pain-point")
    ap.add_argument("--scenario")
    ap.add_argument("--conversion-goal")
    ap.add_argument("--core-keywords")

    ap.add_argument("--workspace-worker", default=str(WORKSPACE_WORKER))
    ap.add_argument("--daily-out-base", default=str(DAILY_OUT_BASE))
    ap.add_argument("--ref-dir", default=str(REF_DIR))
    ap.add_argument("--image-model", default=os.environ.get("XHS_IMAGE_MODEL") or os.environ.get("GEMINI_IMAGE_MODEL") or os.environ.get("GEMINI_MODEL") or "gemini-3-pro-image-preview")
    ap.add_argument("--image-base-url", default=os.environ.get("XHS_IMAGE_BASE_URL") or os.environ.get("GEMINI_BASE_URL") or os.environ.get("GOOGLE_GENAI_BASE_URL"))
    ap.add_argument("--image-aspect-ratio", default=os.environ.get("XHS_IMAGE_ASPECT_RATIO") or "4:5")

    ap.add_argument("--review-only", action="store_true")
    ap.add_argument("--publish", action="store_true")
    args = ap.parse_args()

    if args.review_only and args.publish:
        raise SystemExit("Choose one: --review-only or --publish")

    workspace_worker = Path(args.workspace_worker).expanduser()
    daily_out_base = Path(args.daily_out_base).expanduser()
    ref_dir = Path(args.ref_dir).expanduser()

    factory = workspace_worker / "bundles/_unpacked/xhs_glumoo_pipeline/glumoo_factory_v4.6.1_FESTIVAL_FINAL.py"
    image_gen = workspace_worker / "bundles/_unpacked/xhs_glumoo_pipeline/skills/nano-banana-pro/scripts/generate_image.py"
    auto_post = workspace_worker / "bundles/_unpacked/xhs_glumoo_pipeline/xhs_auto_post.sh"
    report_dir = workspace_worker / "reports"
    media_out_base = workspace_worker / "media_out"
    feishu_outbox_base = Path(os.environ.get("XHS_FEISHU_OUTBOX_BASE", str(FEISHU_OUTBOX_BASE))).expanduser()

    sku_refs = {
        1: {"outer": ref_dir / "sku1.png", "stick": ref_dir / "sku1小包装.png", "pack": "box"},
        2: {"outer": ref_dir / "sku2.jpg", "stick": ref_dir / "sku2小包装.png", "pack": "bag"},
        3: {"outer": ref_dir / "sku3.jpg", "stick": ref_dir / "sku3小包装.png", "pack": "bag"},
    }

    themes_cfg = load_themes(Path(args.themes_json)) if (args.auto_theme or args.auto_sku or args.auto_content_type) else None

    theme = args.theme
    content_type = args.content_type
    sku = args.sku

    if args.auto_content_type:
        content_type = None
    if args.auto_sku:
        sku = None
    if args.auto_theme:
        theme = None

    if themes_cfg is not None and (theme is None or content_type is None or sku is None):
        auto_theme, auto_ct, auto_sku = choose_auto(themes_cfg, args.date, content_type, sku)
        if theme is None:
            theme = auto_theme
        if content_type is None:
            content_type = auto_ct
        if sku is None:
            sku = auto_sku

    if theme is None:
        raise SystemExit("Missing --theme (or use --auto-theme)")
    if sku is None:
        raise SystemExit("Missing --sku (or use --auto-sku)")

    sku_profile = get_sku_profile(themes_cfg, sku)
    strategy = args.strategy or infer_strategy(args.unit_price, args.user_intent, content_type, sku_profile)

    sku_ref = sku_refs[sku]
    if not sku_ref["outer"].exists():
        raise FileNotFoundError(f"Missing outer ref: {sku_ref['outer']}")
    if not sku_ref["stick"].exists():
        raise FileNotFoundError(f"Missing stick ref: {sku_ref['stick']}")

    env = os.environ.copy()
    if env.get("XHS_IMAGE_API_KEY") and not env.get("XHS_TEXT_API_KEY"):
        env["XHS_TEXT_API_KEY"] = env["XHS_IMAGE_API_KEY"]
    if env.get("XHS_IMAGE_BASE_URL") and not env.get("XHS_TEXT_BASE_URL"):
        env["XHS_TEXT_BASE_URL"] = env["XHS_IMAGE_BASE_URL"]
    env.setdefault("XHS_TEXT_MODEL", "models/gemini-3.1-flash-lite-preview")
    env["CONTENT_TYPE"] = content_type
    env["XHS_DATE"] = args.date
    env["XHS_THEME"] = theme
    env["XHS_PRODUCT_FOCUS"] = f"{sku_profile.get('name', f'SKU {sku}')} / {sku_profile.get('positioning', theme)}: {theme}"
    env["XHS_STRATEGY"] = strategy
    env["XHS_SKU_NAME"] = sku_profile.get("name", f"SKU {sku}")
    env["XHS_SKU_POSITIONING"] = sku_profile.get("positioning", "")
    env["XHS_SKU_TRAFFIC_FOCUS"] = sku_profile.get("traffic_focus", "")
    env["XHS_STRATEGY_BRIEF"] = build_strategy_brief(strategy, args, sku_profile)
    if args.audience:
        env["XHS_AUDIENCE"] = args.audience
    if args.pain_point:
        env["XHS_PAIN_POINT"] = args.pain_point
    if args.scenario:
        env["XHS_SCENARIO"] = args.scenario
    if args.conversion_goal:
        env["XHS_CONVERSION_GOAL"] = args.conversion_goal
    if args.core_keywords:
        env["XHS_CORE_KEYWORDS"] = args.core_keywords
    run(["python3", str(factory)], env=env, timeout=300)

    out_dir = find_latest_daily_folder(args.date, theme, sku, daily_out_base)
    copy_path = out_dir / "01_正文与标签_复制即发.txt"
    prompt_path = out_dir / "02_生图提示词_中文精修.txt"

    copy_text = read_text(copy_path)
    sanitized_copy_text, sanitize_hits = sanitize_copy_text(copy_text, sku_profile)
    sanitized_copy_path = out_dir / "01_正文与标签_可发版.txt"
    sanitized_copy_path.write_text(sanitized_copy_text, encoding="utf-8")
    sanitize_report_path = out_dir / "00_文案脱敏检测.json"
    sanitize_report_path.write_text(json.dumps({"hits": sanitize_hits}, ensure_ascii=False, indent=2), encoding="utf-8")
    strategy_snapshot_path = maybe_write_strategy_snapshot(out_dir, strategy, args, sku_profile, sanitize_hits)

    copy_lines = sanitized_copy_text.splitlines()
    title = safe_title(copy_lines[0] if copy_lines else "🇲🇾Glumoo")

    body = "\n".join(copy_lines[1:]).strip()
    body = re.split(r"\n---\n\n### 绘图指令", body, maxsplit=1)[0].strip()
    tags, content = split_tags_and_content(body)

    # Tags: fixed 6 + dynamic 4 (user SOP rule).
    # We take the first 6 tags as the fixed pack, then fill up to 10 with the next 4 dynamic tags.
    sanitized_copy_lines = sanitized_copy_text.splitlines()
    sanitized_body = "\n".join(sanitized_copy_lines[1:]).strip()
    sanitized_body = re.split(r"\n---\n\n### 绘图指令", sanitized_body, maxsplit=1)[0].strip()
    _tags, _content = split_tags_and_content(sanitized_body)
    # Fixed tags required by SOP (always included, first):
    required_fixed = [
        "Glumoo",
        "Glumoo氨糖羊奶粉",
        "Glumoo关节守护",
        "NAGlumoo",
    ]

    # Preserve original order for any tags that are not in required_fixed.
    # Rule: required fixed tags + (other tags in original order, de-duplicated) => take first 10.
    seen = set()
    final_tags = []
    for t in required_fixed:
        if t and t not in seen:
            final_tags.append(t)
            seen.add(t)

    for t in _tags:
        if t and t not in seen:
            final_tags.append(t)
            seen.add(t)

    final_tags = final_tags[:10]
    sanitized_copy_text = "\n".join([
        sanitized_copy_lines[0].strip(),
        "",
        _content.strip(),
        "",
        " ".join([f"#{t}" for t in final_tags]),
    ]).strip() + "\n"
    sanitized_copy_path.write_text(sanitized_copy_text, encoding="utf-8")

    prompt_text = read_text(prompt_path)
    blocks = extract_prompt_blocks_from_text(prompt_text)
    if not blocks:
        m = re.search(r"### 绘图指令[\s\S]*", copy_text)
        if m:
            blocks = extract_prompt_blocks_from_text(m.group(0))

    if not blocks:
        raise RuntimeError("No image prompt blocks available")

    out_media_dir = media_out_base / f"{args.date}_skill_{strategy}_{content_type}_SKU{sku}"
    out_media_dir.mkdir(parents=True, exist_ok=True)

    out_images = []
    for idx, blk in enumerate(blocks, 1):
        blk = enforce_scene_rules(blk, idx, strategy, args)
        if idx == 1:
            blk += "\n- 产品参考强制: 封面图必须严格参考提供的产品外盒图与小包装图，包装配色、版式、正面主视觉、外盒形状必须尽量一致，不得擅自改成其他包装设计。"
            blk += "\n- 产品出镜强制: 封面图里产品必须清晰、完整、可识别，优先展示外盒正面与小包装，不可只出现模糊色块或错误包装。"
        else:
            blk += "\n- 产品参考强制: 产品外观继续严格参考提供的产品图，保持同一SKU包装，不得画错款。"
        fn = out_media_dir / ("01_cover_ref.png" if idx == 1 else f"{idx:02d}.png")
        image_cmd = [
            "python3",
            str(image_gen),
            "--prompt",
            blk,
            "--input-image",
            str(sku_ref["outer"]),
            "--input-image",
            str(sku_ref["stick"]),
            "--filename",
            str(fn),
            "--model",
            args.image_model,
            "--aspect-ratio",
            args.image_aspect_ratio,
        ]
        if args.image_base_url:
            image_cmd.extend(["--base-url", args.image_base_url])
        image_env = os.environ.copy()
        if image_env.get("XHS_IMAGE_API_KEY") and not image_env.get("GEMINI_API_KEY"):
            image_env["GEMINI_API_KEY"] = image_env["XHS_IMAGE_API_KEY"]
        if image_env.get("XHS_IMAGE_MODEL") and not image_env.get("GEMINI_IMAGE_MODEL"):
            image_env["GEMINI_IMAGE_MODEL"] = image_env["XHS_IMAGE_MODEL"]
        if image_env.get("XHS_IMAGE_BASE_URL") and not image_env.get("GEMINI_BASE_URL"):
            image_env["GEMINI_BASE_URL"] = image_env["XHS_IMAGE_BASE_URL"]
        run_capture_filtered(
            image_cmd,
            env=image_env,
            timeout=1800,
            stdout_filter=lambda line: is_unsafe_worker_media_line(line, out_media_dir),
        )
        out_images.append(str(fn))

    staged_send_dir = feishu_outbox_base / f"{args.date}_skill_{strategy}_{content_type}_SKU{sku}"
    staged_send_items = stage_feishu_send_images(out_images, staged_send_dir)
    staged_send_images = [item["staged"] for item in staged_send_items]

    print(f"Feishu-safe image dir: {staged_send_dir}")
    for safe_path in staged_send_images:
        print(f"MEDIA:{safe_path}")

    report_dir.mkdir(parents=True, exist_ok=True)

    report_path = report_dir / f"xhs_skill_report_{strategy}_{content_type}_SKU{sku}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    report_path.write_text(
        "\n".join(
            [
                "# XHS SOP Skill Report",
                "",
                f"- date: {args.date}",
                f"- theme: {theme}",
                f"- strategy: {strategy}",
                f"- content_type: {content_type}",
                f"- sku: {sku}",
                f"- unit_price: {args.unit_price}",
                f"- user_intent: {args.user_intent}",
                f"- audience: {args.audience}",
                f"- pain_point: {args.pain_point}",
                f"- scenario: {args.scenario}",
                f"- conversion_goal: {args.conversion_goal}",
                f"- core_keywords: {args.core_keywords}",
                f"- title: {title}",
                f"- sku_name: {sku_profile.get('name')}",
                f"- sku_positioning: {sku_profile.get('positioning')}",
                f"- traffic_focus: {sku_profile.get('traffic_focus')}",
                f"- itch_points: {json.dumps(sku_profile.get('itch_points'), ensure_ascii=False)}",
                f"- identity_signal: {sku_profile.get('identity_signal')}",
                f"- value_justification: {sku_profile.get('value_justification')}",
                f"- frameworks: {json.dumps(sku_profile.get('frameworks'), ensure_ascii=False)}",
                f"- strategy_snapshot: `{strategy_snapshot_path}`",
                f"- sanitize_report: `{sanitize_report_path}`",
                f"- copy: `{copy_path}`",
                f"- sanitized_copy: `{sanitized_copy_path}`",
                f"- prompt: `{prompt_path}`",
                f"- feishu_send_dir: `{staged_send_dir}`",
                f"- image_model: `{args.image_model}`",
                f"- image_base_url: `{args.image_base_url}`",
                f"- image_aspect_ratio: `{args.image_aspect_ratio}`",
                "",
                "## images",
                *[f"- `{p}`" for p in staged_send_images],
                "",
                "## debug_source_image_names_do_not_send",
                "- 这里只保留原始文件名供排障，不提供可直接发送的 worker 绝对路径。",
                *[f"- `{Path(p).name}`" for p in out_images],
                "",
                "## tags",
                f"- {json.dumps(tags, ensure_ascii=False)}",
            ]
        ),
        encoding="utf-8",
    )

    if args.publish:
        env2 = os.environ.copy()
        env2["XHS_TITLE"] = title
        env2["XHS_VISIBILITY"] = "仅自己可见"
        env2["XHS_CONTENT"] = content
        env2["XHS_TAGS_JSON"] = json.dumps(tags, ensure_ascii=False)
        env2["XHS_IMAGES_JSON"] = json.dumps(out_images, ensure_ascii=False)
        run(["bash", str(auto_post)], env=env2, timeout=600)

    print(str(report_path))


if __name__ == "__main__":
    main()
