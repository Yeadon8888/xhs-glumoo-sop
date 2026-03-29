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

DOG_BREEDS = ["玩具体贵宾（泰迪风）", "博美", "比熊", "金毛", "雪纳瑞"]
CAT_BREEDS = ["英短", "布偶", "波斯", "缅因", "曼赤肯"]
CAT_IDENTITY_PROFILES = [
    {
        "label": "暖橘色家养短毛猫",
        "anchor": "本篇固定同一只暖橘色家养短毛猫，短毛、自然家猫脸、暖橘/姜黄色主毛，可少量白下巴或白胸，但整体一眼看上去就是橘猫；体型匀称偏圆润，眼神自然，不得漂成英短脸、缅因、布偶、长毛猫或其他猫种感",
    },
    {
        "label": "奶油橘家养短毛猫",
        "anchor": "本篇固定同一只奶油橘家养短毛猫，短毛、自然家猫脸、浅暖橘到奶油橘主毛，五官稳定，体型家养感，不得漂成灰猫、银猫、重点色、长毛猫或其他品种脸",
    },
    {
        "label": "虎斑橘家养短毛猫",
        "anchor": "本篇固定同一只虎斑橘家养短毛猫，短毛、自然家猫脸、暖橘底色带自然虎斑纹，脸型稳定、毛色稳定、不是英短脸也不是缅因感，不得忽然变成长毛或其他花色主毛",
    },
    {
        "label": "金棕色家养短毛猫",
        "anchor": "本篇固定同一只金棕色家养短毛猫，短毛、自然家猫脸、金棕到暖棕主毛，体型自然、眼神稳定、家庭宠物感强，不得漂成品种猫宣传照风格",
    },
]
SCENE_KEYWORDS = ["别墅", "villa", "condo", "高端社区", "高级公寓", "公寓", "庭院", "阳台", "厨房", "客厅", "餐厅", "车棚", "泳池边", "露台"]
IMAGE_TEXT_RULE = "每张图都要有适量短文案：封面1句主标题，内页可有1句场景短句或1-2个小标签；禁止满屏大字、禁止海报风硬广。"


def load_env_file(path: Path) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def env_path(name: str, default: str) -> Path:
    return Path(os.environ.get(name, default)).expanduser()


SKILL_DIR = Path(__file__).resolve().parents[1]
AGENT_WORKSPACE = Path(__file__).resolve().parents[3]
DEFAULT_THEMES_JSON = SKILL_DIR / "config/themes.json"
DEFAULT_ENV_FILE = env_path("XHS_ENV_FILE", "~/.config/glumoo/xhs-sop.env")
load_env_file(DEFAULT_ENV_FILE)

WORKSPACE_WORKER = env_path("XHS_WORKSPACE_WORKER", "/Users/Apple/.openclaw/workspace-worker-xhs")
DAILY_OUT_BASE = env_path("XHS_DAILY_OUT_BASE", "/Users/Apple/Documents/Glumoo/02_每日内容生成")
REF_DIR = env_path("XHS_REF_DIR", "/Users/Apple/Documents/Glumoo/产品资料/产品照/三款产品")
FEISHU_OUTBOX_BASE = env_path("XHS_FEISHU_OUTBOX_BASE", "/Users/Apple/.openclaw/media/outbox/feishu-longxia-dabao")

FACTORY = WORKSPACE_WORKER / "bundles/_unpacked/xhs_glumoo_pipeline/glumoo_factory_v4.6.1_FESTIVAL_FINAL.py"
IMAGE_GEN = SKILL_DIR / "scripts/generate_image_compat.py"
AUTO_POST = WORKSPACE_WORKER / "bundles/_unpacked/xhs_glumoo_pipeline/xhs_auto_post.sh"
REPORT_DIR = WORKSPACE_WORKER / "reports"
MEDIA_OUT_BASE = WORKSPACE_WORKER / "media_out"

SKU_REFS = {
    1: {"outer": REF_DIR / "sku1.png", "stick": REF_DIR / "sku1小包装.png", "pack": "box"},
    2: {"outer": REF_DIR / "sku2.jpg", "stick": REF_DIR / "sku2小包装.png", "pack": "bag"},
    3: {"outer": REF_DIR / "sku3.jpg", "stick": REF_DIR / "sku3小包装.png", "pack": "bag"},
}

SKU_FIXED_TAGS = {
    1: ["Glumoo", "Glumoo氨糖羊奶粉", "Glumoo多维力", "宠物羊奶粉"],
    2: ["Glumoo", "Glumoo氨糖羊奶粉", "Glumoo关节守护", "GlumooNAG"],
    3: ["Glumoo", "Glumoo氨糖羊奶粉", "Glumoo畅清", "肠胃日常管理"],
}

SKU_TAG_GUARD = {
    1: {
        "allow_keywords": ["多维力", "泌尿", "恢复", "顺毛", "长肉", "体弱", "养猫", "宠物羊奶粉", "Glumoo"],
        "block_keywords": ["关节守护", "狗关节", "跃力", "畅清"],
    },
    2: {
        "allow_keywords": ["跃力", "关节", "行动", "老宠", "狗狗", "养狗", "宠物羊奶粉", "Glumoo", "NAG"],
        "block_keywords": ["畅清", "多猫", "肠胃", "排毛", "多维力"],
    },
    3: {
        "allow_keywords": ["畅清", "肠胃", "除臭", "多猫", "排毛", "毛球", "养猫", "宠物羊奶粉", "Glumoo"],
        "block_keywords": ["关节守护", "狗关节", "跃力", "多维力", "NAG"],
    },
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


def strip_storyboard_lines(text: str) -> str:
    cleaned_lines = []
    for line in (text or "").splitlines():
        s = line.strip()
        if not s:
            cleaned_lines.append("")
            continue
        if re.match(r"^(?:\d+[.)、：:]\s*)?(?:图片|图)\s*\d+", s):
            continue
        if re.match(r"^(场景|人物|动作|宠物|产品|细节|内容|图中文字|封面文案|内页文案|画面描述)\s*[：:]", s):
            continue
        if "沿用图1相同场景" in s or "沿用图片1" in s:
            continue
        if "图片1必须" in s or "图片2-5" in s:
            continue
        cleaned_lines.append(line.rstrip())

    cleaned = "\n".join(cleaned_lines)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned).strip()
    return cleaned


def dedupe_leading_title(title: str, content: str) -> str:
    def _norm(s: str) -> str:
        s = (s or "").strip()
        s = s.replace("🇲🇾", "")
        s = re.sub(r"[？?！!。．、,，:：'\"“”‘’·…—-]", "", s)
        s = re.sub(r"\s+", "", s)
        return s

    t = _norm(title)
    if not t:
        return (content or "").strip()

    lines = (content or "").splitlines()
    while lines and not lines[0].strip():
        lines.pop(0)
    if not lines:
        return ""

    first = _norm(lines[0])
    if first == t:
        lines = lines[1:]
        while lines and not lines[0].strip():
            lines.pop(0)
    return "\n".join(lines).strip()


def split_tags_and_content(body: str):
    hashtags = re.findall(r"#\S+", body)
    tags = [h.lstrip("#") for h in hashtags if h.strip("#")]
    content = re.sub(r"\s*#\S+", "", body).strip()
    content = strip_storyboard_lines(content)
    content = re.sub(r"\n{3,}", "\n\n", content)

    # Encourage structured copy: keep paragraphs short and readable.
    # If content is a single long paragraph, insert breaks on strong sentence boundaries.
    lines = [ln.rstrip() for ln in content.splitlines()]
    if len(lines) <= 2 and len(content) >= 200:
        content = re.sub(r"(。|！|\!|\?|？)(?=\S)", r"\1\n\n", content)
        content = re.sub(r"\n{3,}", "\n\n", content).strip()

    return tags, content


MAINLAND_BUZZWORDS = [
    "宝子们", "闭眼入", "谁懂啊", "天花板", "冲就完事了", "冲就完事",
    "种草神器", "狠狠拿捏", "直接锁死", "封神", "绝绝子", "YYDS",
]


LOCAL_COPY_REPLACEMENTS = [
    ("种草", "留意"),
    ("宝子们", "养宠家庭"),
    ("闭眼入", "可以先看自己家适不适合"),
    ("谁懂啊", "真的会懂"),
    ("天花板", "我自己会继续留着"),
    ("种草神器", "会想继续留着的日常搭配"),
]


SKU_LOCAL_OPENERS = {
    "多维力": "老实讲，",
    "跃力": "Aiyo，",
    "畅清": "讲真的，",
}


def localize_copy_voice(text: str, sku_profile: Optional[dict] = None) -> str:
    out = (text or "").strip()
    if not out:
        return out

    for a, b in LOCAL_COPY_REPLACEMENTS:
        out = out.replace(a, b)
    for word in MAINLAND_BUZZWORDS:
        out = out.replace(word, "")

    out = re.sub(r"\n{3,}", "\n\n", out).strip()
    lines = out.splitlines()
    if lines:
        first = lines[0].strip()
        opener = SKU_LOCAL_OPENERS.get((sku_profile or {}).get("name", ""), "")
        if opener and first and opener not in first[:8]:
            lines[0] = opener + first
    return "\n".join(lines).strip()


def filter_tags_for_sku(tags, sku: int):
    guard = SKU_TAG_GUARD.get(sku)
    if not guard:
        return tags

    allow_keywords = guard.get("allow_keywords", [])
    block_keywords = guard.get("block_keywords", [])
    filtered = []
    seen = set()
    for tag in tags:
        t = (tag or "").strip()
        if not t or t in seen:
            continue
        if any(bad and bad in t for bad in block_keywords):
            continue
        if t.startswith("Glumoo"):
            filtered.append(t)
            seen.add(t)
            continue
        if any(ok and ok in t for ok in allow_keywords):
            filtered.append(t)
            seen.add(t)
    return filtered


def safe_title(title: str) -> str:
    title = title.strip().replace("*", "")
    if not title.startswith("🇲🇾"):
        title = "🇲🇾" + title
    if len(title) > 20:
        title = title[:20].rstrip("，。！？、：； ")
    return title


def ensure_full_copy_content(title: str, content: str, sku_profile: dict, args, contract: Optional[dict] = None) -> str:
    cleaned = (content or "").strip()
    non_brand_lines = []
    for line in cleaned.splitlines():
        s = line.strip()
        if not s:
            continue
        if s.startswith("#"):
            continue
        if s in {
            "日本品牌，马来西亚制造（Japanese brand, Made in Malaysia）",
            "纯植物基发酵 NAG（plant-based fermented NAG）",
            "Glumoo 植物基发酵，给他0负担的爱",
            "（如已出现明显跛行/疼痛，建议先就医评估）",
            "（如持续软便、频繁呕吐或精神明显变差，建议先就医评估）",
            "（如已出现持续尿闭、血尿或明显精神不振，建议先就医评估）",
            "（如出现持续不适或症状加重，建议先就医评估）",
        }:
            continue
        non_brand_lines.append(s)

    body_blob = re.sub(r"\s+", "", "\n".join(non_brand_lines))
    if len(body_blob) >= 120:
        return localize_copy_voice(cleaned, sku_profile)

    pet_type = "猫咪" if (contract or {}).get("pet_type") == "cat" else ("狗狗" if (contract or {}).get("pet_type") == "dog" else "毛孩子")
    sku_name = sku_profile.get("name", "Glumoo")
    theme = getattr(args, "theme", None) or getattr(args, "topic", None) or "这段时间的日常记录"
    scenario = getattr(args, "scenario", None) or "日常喂养"

    fallback = "\n\n".join([
        f"最近我更明显感觉到，家里这只{pet_type}的状态是在慢慢往好的方向走。不是那种特别夸张的变化，而是你每天相处时，会发现它看起来更有精神，毛感更顺，整只宠物的状态更在线。",
        f"我自己现在更在意的是能不能长期坚持，所以会优先选那种容易放进{scenario}里的方式。像平时拌粮、顺手安排进去，对我来说执行门槛比较低，也比较适合长期观察变化。",
        f"这次这条主要就是记录一下最近的真实感受：围绕“{theme}”这件事，我更看重的是稳定、自然、能持续，而不是那种一上来就写得很夸张的效果词。对我来说，{sku_name}这种日常型搭配，反而更适合慢慢养出状态。",
    ])
    return localize_copy_voice(fallback.strip(), sku_profile)


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

    traffic_focus = (sku_profile or {}).get("traffic_focus")
    positioning = (sku_profile or {}).get("positioning", "")
    pain_points_blob = " ".join((sku_profile or {}).get("pain_points", []))
    search_signal_blob = f"{positioning} {pain_points_blob}"

    if traffic_focus == "search":
        if unit_price is not None and unit_price >= 200:
            return "search"
        if content_type in SEARCH_TYPES:
            return "search"
        if content_type == "体验" and any(k in search_signal_blob for k in ["关节", "老宠", "挑食", "长期", "怎么选", "管理"]):
            return "search"

    if traffic_focus == "discovery" and content_type in DISCOVERY_TYPES:
        return "discovery"

    if unit_price is not None and unit_price > 200:
        return "search"
    if content_type in SEARCH_TYPES:
        return "search"
    if content_type in DISCOVERY_TYPES:
        return "discovery"
    if traffic_focus in {"search", "discovery"}:
        return traffic_focus
    return "discovery"


def get_sku_profile(theme_cfg: Optional[dict], sku: int) -> dict:
    if theme_cfg:
        raw = theme_cfg.get("sku_profiles", {}).get(str(sku))
        if raw:
            return raw
    return SKU_DEFAULTS[sku]


def choose_auto(theme_cfg: dict, date_str: str, content_type: Optional[str], sku: Optional[int]):
    rotation = theme_cfg.get("rotation", {})
    daily_plan = theme_cfg.get("daily_plan") or []
    plan_entry = None

    if daily_plan:
        d = datetime.date.fromisoformat(date_str)
        plan_entry = daily_plan[d.toordinal() % len(daily_plan)]

    if content_type is None:
        if plan_entry and plan_entry.get("content_type"):
            content_type = plan_entry["content_type"]
        else:
            cts = rotation.get("content_types") or ["科普", "体验", "故事", "挑战", "转化"]
            content_type = pick_from_rotation(cts, date_str)

    if sku is None:
        if plan_entry and plan_entry.get("sku") is not None:
            sku = int(plan_entry["sku"])
        else:
            skus = rotation.get("skus") or [1, 2, 3]
            sku = int(pick_from_rotation(skus, date_str))

    sku_cfg = (theme_cfg.get("sku_profiles") or {}).get(str(sku), {})
    sku_theme_map = sku_cfg.get("theme_map") or {}
    themes_map = theme_cfg.get("themes", {})

    if plan_entry and plan_entry.get("theme"):
        theme = plan_entry["theme"]
    else:
        candidates = sku_theme_map.get(content_type) or themes_map.get(content_type) or ["多宠家庭解决方案：一包搞定所有"]
        theme = pick_from_rotation(candidates, date_str)

    return theme, content_type, sku


def choose_existing_path(*candidates: Path) -> Path:
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0]


def build_runtime_sku_refs(ref_dir: Path) -> dict:
    return {
        1: {"outer": choose_existing_path(ref_dir / "sku1.png", ref_dir / "sku1.jpg"), "stick": choose_existing_path(ref_dir / "sku1小包装.png", ref_dir / "sku1小包装.jpg"), "pack": "box"},
        2: {"outer": choose_existing_path(ref_dir / "sku2外包装正面图.png", ref_dir / "sku2.png", ref_dir / "sku2.jpg"), "stick": choose_existing_path(ref_dir / "sku2小包装.png", ref_dir / "sku2小包装.jpg"), "pack": "bag"},
        3: {"outer": choose_existing_path(ref_dir / "sku3.jpg", ref_dir / "sku3.png", ref_dir.parent / "sku3畅清外包装正面图.png"), "stick": choose_existing_path(ref_dir / "sku3小包装.png", ref_dir / "sku3小包装.jpg"), "pack": "bag"},
    }


def find_latest_daily_folder(date_str: str, theme: str, sku: int, daily_out_base: Path) -> Path:
    theme_slug = re.sub(r"[\s/:]+", "_", theme)
    patterns = [
        f"{date_str}_{theme}_SKU_{sku}_v4.6.2",
        f"{date_str}_{theme}_SKU_{sku}_v4.6.1",
        f"{date_str}_{theme}_SKU_{sku}_v*",
        f"{date_str}_{theme}_*_v4.6.2",
        f"{date_str}_{theme}_*_v4.6.1",
        f"{date_str}_{theme}_*_v*",
        f"{date_str}_{theme_slug}_SKU_{sku}_v4.6.2",
        f"{date_str}_{theme_slug}_SKU_{sku}_v4.6.1",
        f"{date_str}_{theme_slug}_SKU_{sku}_v*",
        f"{date_str}_{theme_slug}_*_v4.6.2",
        f"{date_str}_{theme_slug}_*_v4.6.1",
        f"{date_str}_{theme_slug}_*_v*",
    ]
    candidates = []
    for patt in patterns:
        candidates.extend(daily_out_base.glob(patt))

    filtered = []
    normalized_theme_tokens = {theme, theme_slug, theme.replace(" ", "_"), theme.replace("/", "_")}
    sku_alias_map = {1: ["多维力"], 2: ["跃力"], 3: ["畅清"]}
    aliases = sku_alias_map.get(sku, [])

    for path in set(candidates):
        name = path.name
        if not any(token and token in name for token in normalized_theme_tokens):
            continue
        if f"SKU_{sku}" in name or any(alias in name for alias in aliases):
            filtered.append(path)

    candidates = sorted(filtered or set(candidates), key=lambda p: p.stat().st_mtime, reverse=True)
    if not candidates:
        raise FileNotFoundError(f"No daily output folder found for theme={theme}, sku={sku} under {daily_out_base}")
    return candidates[0]


def extract_prompt_blocks_from_text(text: str):
    normalized = (text or "").strip()
    if not normalized or "【绘图指令生成失败】" in normalized:
        return []

    header_re = re.compile(
        r"^\s*(?:\d+[.)、：:]\s*)?(?:\*\*)?(?:图片|图)\d+(?:[^\n:：]*?)(?:\*\*)?\s*[:：]\s*",
    )

    lines = normalized.splitlines()
    blocks = []
    current = []
    for line in lines:
        stripped = line.strip()
        if header_re.match(stripped) or stripped.startswith("[图片") or stripped.startswith("[图"):
            if current:
                blocks.append("\n".join(current).strip())
            current = [stripped]
        else:
            if current:
                current.append(line.rstrip())
    if current:
        blocks.append("\n".join(current).strip())

    if blocks:
        return blocks

    parts = re.split(
        r"(?=\n\[(?:图片|图)\d+.*?\])|(?=\A\[(?:图片|图)1.*?\])|(?=\n\*\*(?:图片|图)\d+.*?\*\*[:：])|(?=\A\*\*(?:图片|图)1.*?\*\*[:：])|(?=\n(?:图片|图)\d+.*?[:：])|(?=\A(?:图片|图)1.*?[:：])",
        normalized,
    )
    fallback_blocks = []
    for p in parts:
        s = p.strip()
        if (
            s.startswith("[图片")
            or s.startswith("[图")
            or re.match(r"^\*\*(?:图片|图)\d+.*?\*\*[:：]", s)
            or re.match(r"^(?:图片|图)\d+.*?[:：]", s)
            or re.match(r"^\d+[.)、：:]\s*\*\*(?:图片|图)\d+.*?\*\*[:：]", s)
            or re.match(r"^\d+[.)、：:]\s*(?:图片|图)\d+.*?[:：]", s)
        ):
            fallback_blocks.append(s)
    return fallback_blocks

def derive_runtime_defaults(sku: int, strategy: str, sku_profile: dict) -> dict:
    name = sku_profile.get("name", f"SKU {sku}")
    defaults = {
        "audience": "马来西亚养宠家庭",
        "pain_point": " / ".join(sku_profile.get("pain_points", [])) or "宠物日常营养管理",
        "scenario": "马来西亚华人家庭日常养宠场景",
        "conversion_goal": "激发兴趣与收藏" if strategy == "discovery" else "完成搜索拦截与购买决策",
        "core_keywords": f"Glumoo, {name}, 宠物营养, 马来西亚养宠",
        "pet_type": "dog" if sku == 2 else "cat",
        "pet_breed": "马来西亚华人家庭常见家养犬（中小型犬）" if sku == 2 else "本篇单一外貌家养短毛猫（跨篇可变，单篇固定）",
        "pet_anchor": "家养感、自然体态、精神稳定、毛发干净顺滑、不是赛级摆拍风" if sku == 2 else "本篇固定同一只家养短毛猫：脸型稳定、毛色稳定、自然眼神、干净顺毛、不是赛级或猫舍宣传照风格；允许跨篇更换外貌，但单篇内不得漂移",
    }

    if sku == 1:
        defaults.update(
            {
                "audience": "马来西亚精细养猫家庭，尤其是关注泌尿修复、恢复期调理、体弱猫营养支持的人群",
                "scenario": "马来西亚华人养猫家庭的真实日常：喝水偏少、恢复期护理、拌粮补给、换毛期观察、体态恢复记录",
                "core_keywords": "Glumoo, 多维力, 泌尿道日常支持, 膀胱粘膜, 恢复期猫咪, 长肉增重, 顺毛, 马来西亚养猫",
                "pet_type": "cat",
                "pet_breed": "本篇单一外貌家养短毛猫（恢复期/体弱/需要长期营养支持的家庭猫）",
                "pet_anchor": "自然家养猫感，不是猫舍宣传照；可偏瘦小恢复期、幼猫或高龄猫，但单篇必须同一只，重点体现恢复、补水、顺毛和体态慢慢变稳",
            }
        )
    elif sku == 2:
        defaults.update(
            {
                "audience": "马来西亚华人养狗家庭，尤其是关注关节管理、适口性和长期执行门槛的人群",
                "scenario": "马来西亚中高端华人养狗家庭的真实日常：拌粮、兑水、饭后观察、出门散步、回家休息",
                "core_keywords": "Glumoo, 跃力, 狗关节, 老龄行动支持, 起身困难, 走路打滑, 挑食狗狗, 骗水, 适口性, 马来西亚养狗",
                "pet_type": "dog",
                "pet_breed": "马来西亚华人家庭常见家养犬（可偏贵宾/米克斯/中小型犬，但不要锁死单一品种）",
                "pet_anchor": "家养感强、自然耐看、非赛级夸张造型、适合真实家庭长期喂养记录；重点体现行动力、关节照护和长期可坚持",
            }
        )
    elif sku == 3:
        defaults.update(
            {
                "audience": "马来西亚多猫或多宠家庭，尤其是关注肠胃敏感、排毛、猫砂盆异味和室内环境管理的人群",
                "scenario": "马来西亚室内养猫/多猫家庭的真实日常：猫砂盆清理、拌粮喂食、便便观察、换粮适应、排毛期护理",
                "core_keywords": "Glumoo, 畅清, 多猫家庭, 猫砂盆异味, 肠胃敏感, 软便, 排毛, 毛球, 拌粮神器, 马来西亚养猫",
                "pet_type": "cat",
                "pet_breed": "本篇单一外貌家养短毛猫或多猫家庭固定猫设（按正文决定单猫/多猫，但同篇要统一）",
                "pet_anchor": "真实室内家猫感，重点体现肠胃、排泄、异味与多猫环境管理；若正文写多猫，就必须真的多猫且角色稳定，不可忽单忽多",
            }
        )

    return defaults


def build_strategy_brief(strategy: str, args, sku_profile: dict, runtime_defaults: dict) -> str:
    audience = args.audience or runtime_defaults["audience"]
    pain_point = args.pain_point or runtime_defaults["pain_point"]
    scenario = args.scenario or runtime_defaults["scenario"]
    conversion_goal = args.conversion_goal or runtime_defaults["conversion_goal"]
    keywords = args.core_keywords or runtime_defaults["core_keywords"]
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
    sanitized = localize_copy_voice(text, sku_profile)
    hits = []

    sku_name = (sku_profile or {}).get("name", "")
    if sku_name == "跃力":
        medical_line = "（如已出现明显跛行/疼痛，建议先就医评估）"
    elif sku_name == "畅清":
        medical_line = "（如持续软便、频繁呕吐或精神明显变差，建议先就医评估）"
    elif sku_name == "多维力":
        medical_line = "（如已出现持续尿闭、血尿或明显精神不振，建议先就医评估）"
    else:
        medical_line = "（如出现持续不适或症状加重，建议先就医评估）"
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

    for old_line in [
        "（如已出现明显跛行/疼痛，建议先就医评估）",
        "（如持续软便、频繁呕吐或精神明显变差，建议先就医评估）",
        "（如已出现持续尿闭、血尿或明显精神不振，建议先就医评估）",
        "（如出现持续不适或症状加重，建议先就医评估）",
    ]:
        if old_line != medical_line and old_line in sanitized:
            sanitized = sanitized.replace(old_line, "").strip()
            hits.append({"source": old_line, "replacement": "", "count": 1, "mode": "remove_wrong_disclaimer"})

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


def infer_image_copy_plan(copy_text: str, title: str, tags: list[str], contract: dict) -> dict:
    pet_type = contract.get("pet_type")
    breed = contract.get("breed", "家养宠物")
    short_title = (title or "").strip() or "🇲🇾 Glumoo"
    short_title = re.sub(r"\s+", "", short_title)
    short_title = short_title[:20]

    if pet_type == "dog":
        inner_lines = ["拌粮更省心", "日常养护更稳", "同一主人持续记录", "袋装更好认"]
    else:
        inner_lines = ["挑食期也愿意吃", "日常更稳一点", "同一主人持续记录", "袋装更好认"]

    tag_labels = []
    for raw in tags:
        clean = str(raw).strip().lstrip("#")
        if clean and clean not in tag_labels:
            tag_labels.append(clean)
    if breed and breed not in tag_labels:
        tag_labels.insert(0, breed)

    return {
        "cover_title": short_title,
        "inner_lines": inner_lines[:4],
        "tag_labels": tag_labels[:2],
    }


def infer_pet_contract(copy_text: str, prompt_text: str, runtime_defaults: dict, theme: str, scenario: Optional[str]) -> dict:
    text = f"{copy_text}\n{prompt_text}\n{theme}"
    is_dog = any(token in text for token in ["狗", "狗狗", "犬"])
    is_cat = any(token in text for token in ["猫", "猫咪", "主子"])
    pet_type = "dog" if is_dog and not is_cat else ("cat" if is_cat and not is_dog else runtime_defaults.get("pet_type", "pet"))

    breed_pool = DOG_BREEDS if pet_type == "dog" else CAT_BREEDS
    breed = None
    for candidate in breed_pool:
        if candidate in text:
            breed = candidate
            break
    if breed is None:
        default_breed = runtime_defaults.get("pet_breed", "")
        for candidate in breed_pool:
            if candidate in default_breed:
                breed = candidate
                break
    if breed is None:
        breed = runtime_defaults.get("pet_breed", "家养宠物")

    anchor = runtime_defaults.get("pet_anchor", "家养感、自然耐看")
    if pet_type == "dog" and ("泰迪" in breed or "贵宾" in breed):
        anchor = "本篇固定同一只浅杏/奶油或暖棕色卷毛小狗，圆眼、短嘴、下垂耳，泰迪感但不是赛级长嘴贵宾；允许跨篇换狗，但本篇内必须是同一只，体型和脸型不得漂移"
    elif pet_type == "dog":
        anchor = f"本篇固定同一只{breed}，家养感强、自然体态、毛发干净顺滑、五官稳定；允许跨篇换狗，但本篇内不得变成其他犬种或混成别的脸型"
    elif pet_type == "cat":
        cat_signal = text
        profile_seed = sum(ord(ch) for ch in (theme or "")) + sum(ord(ch) for ch in copy_text[:80])
        profile = CAT_IDENTITY_PROFILES[profile_seed % len(CAT_IDENTITY_PROFILES)]
        breed = profile["label"]
        anchor = profile["anchor"]
        if "橘猫" in cat_signal or "橘色" in cat_signal or "橘白" in cat_signal:
            breed = "暖橘色家养短毛猫"
            anchor = "本篇固定同一只暖橘色/姜黄色家养短毛猫，主体毛色必须一眼可见为暖橘色或姜黄色，可少量白下巴/白胸；自然家猫脸、短毛、体型匀称偏圆润。允许跨篇换猫，但本篇内不得漂成灰猫、银猫、蓝猫、黑猫、长毛猫、英短脸、缅因、布偶或其他猫种感"

    person = "默认同一位马来西亚华人主人（若出镜：年龄感、穿搭、发型、手部特征保持一致；若某张无人，则视为同一家庭场景延续）"
    scene = (scenario or runtime_defaults.get("scenario") or "马来西亚中高端住宅日常").strip()
    normalized_scene = scene
    for keyword in SCENE_KEYWORDS:
        if keyword.lower() in scene.lower() or keyword in text:
            normalized_scene = scene
            break

    return {
        "pet_type": pet_type,
        "breed": breed,
        "anchor": anchor,
        "person": person,
        "scene": normalized_scene,
    }


def enforce_scene_rules(block: str, idx: int, strategy: str, args, contract: dict, image_copy_plan: dict, sku_ref: dict) -> str:
    scenario = contract.get("scene") or (args.scenario or "马来西亚多宠家庭日常").strip()
    pain_point = args.pain_point or "多宠家庭喂养与营养管理"
    keywords = args.core_keywords or "Glumoo, 多宠家庭, 宠物营养"
    breed = contract.get("breed", "家养宠物")
    pet_type_cn = "狗" if contract.get("pet_type") == "dog" else ("猫" if contract.get("pet_type") == "cat" else "宠物")
    anchor = contract.get("anchor", "家养感、自然耐看")
    person = contract.get("person", "若出镜则必须同一主人")

    block += f"\n- 宠物强制(单一真源): 本组只允许出现同一只{pet_type_cn}，固定品种={breed}；禁止改成其他品种、其他毛色、其他脸型、其他体型。"
    block += f"\n- 外貌锚点强制: {anchor}（图片1定义后，图片2-5逐字继承，不得漂移）。"
    block += f"\n- 人物一致性强制: {person}"
    block += f"\n- 图片文案强制: {IMAGE_TEXT_RULE}"
    block += "\n- 宠物身份机制: 宠物外貌按单篇固定、跨篇可变执行；也就是这一套图里必须是同一只宠物，但下一篇可以换成另一只。"
    block += "\n- 猫设防漂移强制: 若本篇正文/标题写橘猫，则本篇全组必须是同一只橘猫，而且主体毛色必须明确为暖橘色/姜黄色；可少量白胸白下巴，但禁止变成灰猫、银猫、蓝猫、黑猫、重点色或其他非橘色主毛。禁止出现英短、缅因、布偶、波斯、曼赤肯、狸花等其他品种感，也禁止忽然从短毛变成长毛。"
    block += "\n- 品种标签禁令: 图中文字里禁止出现‘英短’‘缅因’‘布偶’等品种标签，除非正文明确要求且与全组一致。"
    block += "\n- 文案泄漏禁令: 禁止把 Search、SKU、科普、体验、策略词、检索词、提示词结构写到画面上。"

    if scenario:
        block += f"\n- 场景强制(单一真源): {scenario}（所有图片必须一致遵守，不得回退到其他住宅/院子/走廊风格；若定义为别墅就全组别墅，若定义为高端社区/condo就全组高端社区/condo）"
        block += "\n- 场景禁止(硬禁): 铁花窗Grille/老旧走廊/乡村院子/复古阳台/铁门铁栅/破旧家具/杂乱背景（除非场景真源明确要求）"
    else:
        block += "\n- 场景强制: 马来西亚可识别住宅/街区（铁花窗Grille/吊扇/复古花砖或水磨石/排屋车棚走廊/热带植物/强日照阴影，至少1-2项）"

    if strategy == "search":
        block += f"\n- 搜索页强化: 强化真实使用问题、解决路径与结果感，围绕痛点‘{pain_point}’表达。"
        block += f"\n- 搜索关键词暗示: 画面和道具尽量贴近这些搜索意图：{keywords}。"
    else:
        block += "\n- 发现页强化: 强调第一眼吸引力、情绪氛围、轻松种草和生活方式代入。"

    block += "\n- 文案对齐强制: 图里宠物、人物、场景、包装必须和正文描述一致；若正文写明具体品种/人物/住宅层级，图片不得自行改写。"
    block += f"\n- 包装强制: 本组必须使用{sku_ref.get('pack','指定')}包装形态；外包装与小包装都要和参考图一致。若为袋装，严禁画成盒装；若为盒装，严禁画成袋装。"

    cover_title = image_copy_plan.get("cover_title", "")
    inner_lines = image_copy_plan.get("inner_lines", [])
    tag_labels = image_copy_plan.get("tag_labels", [])
    if idx == 1:
        block += "\n- 角标强制: 右下角固定角标/贴纸‘日本品牌｜大马制造’（清晰可读，位置固定）"
        block += "\n- 多图一致性: 这一张定义宠物外观锚点、产品主体比例和主色调，后续图片必须延续。"
        block += f"\n- 图中文字强制: 封面只放1句主标题：{cover_title}。不要额外堆很多卖点字。"
    else:
        line = inner_lines[(idx - 2) % len(inner_lines)] if inner_lines else "日常记录"
        tag_hint = f"，可补1个小标签：{tag_labels[0]}" if tag_labels else ""
        block += f"\n- 图中文字强制: 本张仅允许1句短文案“{line}”{tag_hint}；保持自然融入画面，不做满屏字。"

    return block


def build_fallback_prompt_blocks(title: str, content: str, contract: dict, image_copy_plan: dict, sku_ref: dict, sku_profile: dict):
    breed = contract.get("breed", "家养宠物")
    pet_type = contract.get("pet_type")
    pet_cn = "狗" if pet_type == "dog" else ("猫" if pet_type == "cat" else "宠物")
    scenario = contract.get("scene", "马来西亚华人家庭真实日常")
    positioning = sku_profile.get("positioning", "日常营养管理")
    name = sku_profile.get("name", "Glumoo")
    pack = sku_ref.get("pack", "指定包装")
    cover_title = image_copy_plan.get("cover_title") or safe_title(title)
    inner_lines = (image_copy_plan.get("inner_lines") or ["日常更省心", "同一主人持续记录", "长期管理更稳", "包装更好认"])[:4]
    tag_labels = image_copy_plan.get("tag_labels") or [breed]
    tag_hint = " / ".join(tag_labels[:2]) if tag_labels else breed
    body_hint = re.sub(r"\s+", " ", (content or "").strip())[:120]

    scenes = [
        f"在{scenario}里，主人和同一只{breed}{pet_cn}同框，{name}{pack}包装清晰可见，画面自然像真实养宠记录。",
        f"主人在厨房或餐桌边给同一只{breed}{pet_cn}拌粮或兑水，突出{positioning}与日常执行感。",
        f"同一主人带同一只{breed}{pet_cn}在社区散步或饭后活动，画面强调轻松、稳定、真实生活感。",
        f"回到家中休息场景，同一只{breed}{pet_cn}放松趴卧，主人陪伴记录，延续同一住宅层级与人物设定。",
        f"产品特写：{name}{pack}包装与内容物近景，参考图一致，干净克制，不做硬广海报。",
    ]
    copies = [cover_title, *inner_lines]
    while len(copies) < 5:
        copies.append("真实养宠记录")

    blocks = []
    for idx in range(1, 6):
        extra = []
        if idx == 1:
            extra.append("角标：日本品牌｜大马制造；封面只放一句标题，控制在20字内。")
        elif idx == 5:
            extra.append(f"可加1个小标签：{tag_hint}。")
        else:
            extra.append(f"可加1句短文案或1个小标签：{tag_hint}。")
        if body_hint:
            extra.append(f"文案语气参考正文：{body_hint}")
        block = "\n".join([
            f"**图片{idx}{' (封面图)' if idx == 1 else ' (内页图)'}:**",
            f"*   **画面描述:** {scenes[idx - 1]}",
            f"*   **图片文案:** {copies[idx - 1]}",
            *[f"- {line}" for line in extra],
        ])
        blocks.append(block)
    return blocks


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
    ap.add_argument("--image-model", default=os.environ.get("XHS_IMAGE_MODEL") or "gemini-3.1-flash-image-preview")
    ap.add_argument("--image-base-url", default=os.environ.get("XHS_IMAGE_BASE_URL") or "https://yunwu.ai")
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
    image_gen = IMAGE_GEN
    auto_post = workspace_worker / "bundles/_unpacked/xhs_glumoo_pipeline/xhs_auto_post.sh"
    report_dir = workspace_worker / "reports"
    media_out_base = workspace_worker / "media_out"
    feishu_outbox_base = Path(os.environ.get("XHS_FEISHU_OUTBOX_BASE", str(FEISHU_OUTBOX_BASE))).expanduser()

    sku_refs = build_runtime_sku_refs(ref_dir)

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
    runtime_defaults = derive_runtime_defaults(sku, strategy, sku_profile)

    sku_ref = sku_refs[sku]
    if not sku_ref["outer"].exists():
        raise FileNotFoundError(f"Missing outer ref: {sku_ref['outer']}")
    if not sku_ref["stick"].exists():
        raise FileNotFoundError(f"Missing stick ref: {sku_ref['stick']}")

    env = os.environ.copy()
    if env.get("GEMINI_API_KEY") and not env.get("XHS_TEXT_API_KEY"):
        env["XHS_TEXT_API_KEY"] = env["GEMINI_API_KEY"]
    elif env.get("GOOGLE_API_KEY") and not env.get("XHS_TEXT_API_KEY"):
        env["XHS_TEXT_API_KEY"] = env["GOOGLE_API_KEY"]
    if env.get("GEMINI_BASE_URL") and not env.get("XHS_TEXT_BASE_URL"):
        env["XHS_TEXT_BASE_URL"] = env["GEMINI_BASE_URL"]
    elif not env.get("XHS_TEXT_BASE_URL"):
        env["XHS_TEXT_BASE_URL"] = "https://generativelanguage.googleapis.com"
    env.setdefault("XHS_TEXT_MODEL", "models/gemini-2.5-flash")
    env["CONTENT_TYPE"] = content_type
    env["XHS_DATE"] = args.date
    env["XHS_THEME"] = theme
    env["XHS_PRODUCT_FOCUS"] = f"{sku_profile.get('name', f'SKU {sku}')} / {sku_profile.get('positioning', theme)}: {theme}"
    env["XHS_STRATEGY"] = strategy
    env["XHS_SKU_NAME"] = sku_profile.get("name", f"SKU {sku}")
    env["XHS_SKU_POSITIONING"] = sku_profile.get("positioning", "")
    env["XHS_SKU_TRAFFIC_FOCUS"] = sku_profile.get("traffic_focus", "")
    env["XHS_STRATEGY_BRIEF"] = build_strategy_brief(strategy, args, sku_profile, runtime_defaults)
    env["XHS_AUDIENCE"] = args.audience or runtime_defaults["audience"]
    env["XHS_PAIN_POINT"] = args.pain_point or runtime_defaults["pain_point"]
    env["XHS_SCENARIO"] = args.scenario or runtime_defaults["scenario"]
    env["XHS_CONVERSION_GOAL"] = args.conversion_goal or runtime_defaults["conversion_goal"]
    env["XHS_CORE_KEYWORDS"] = args.core_keywords or runtime_defaults["core_keywords"]
    env["XHS_PET_TYPE"] = runtime_defaults["pet_type"]
    env["XHS_PET_BREED"] = runtime_defaults["pet_breed"]
    env["XHS_PET_ANCHOR"] = runtime_defaults["pet_anchor"]
    env["XHS_COVER_COPY_RULE"] = "封面必须是20字内强关联标题，开头优先保留🇲🇾；内页只允许适量短文案，不允许满屏大字海报风。"
    env["XHS_PACKAGING_RULE"] = f"SKU{sku}必须严格使用{sku_ref['pack']}包装形态，外包装和小包装都要与参考图一致，不得串包装。"
    env["XHS_COPY_IMAGE_MATCH_RULE"] = "文案和生图必须共享同一只宠物、同一品种、同一人物、同一住宅层级场景；若正文写狗/猫且出现具体品种，绘图必须严格一致；同一组图人物外观与穿搭保持一致。"
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
    body = strip_storyboard_lines(body)
    body = dedupe_leading_title(title, body)
    tags, content = split_tags_and_content(body)

    # Tags: fixed 6 + dynamic 4 (user SOP rule).
    # We take the first 6 tags as the fixed pack, then fill up to 10 with the next 4 dynamic tags.
    sanitized_copy_lines = sanitized_copy_text.splitlines()
    sanitized_body = "\n".join(sanitized_copy_lines[1:]).strip()
    sanitized_body = re.split(r"\n---\n\n### 绘图指令", sanitized_body, maxsplit=1)[0].strip()
    sanitized_body = strip_storyboard_lines(sanitized_body)
    sanitized_body = dedupe_leading_title(title, sanitized_body)
    _tags, _content = split_tags_and_content(sanitized_body)
    _content = dedupe_leading_title(title, _content)
    # Fixed tags required by SOP (always included, first), now SKU-aware.
    required_fixed = SKU_FIXED_TAGS.get(sku, SKU_FIXED_TAGS[1])
    _tags = filter_tags_for_sku(_tags, sku)

    if len(re.sub(r"\s+", "", _content)) < 120:
        _content = ensure_full_copy_content(title, _content, sku_profile, args, contract=None)
        _content = dedupe_leading_title(title, _content)

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
    contract = infer_pet_contract(sanitized_copy_text, prompt_text, runtime_defaults, theme, args.scenario)
    image_copy_plan = infer_image_copy_plan(sanitized_copy_text, title, final_tags, contract)
    blocks = extract_prompt_blocks_from_text(prompt_text)
    if not blocks:
        m = re.search(r"### 绘图指令[\s\S]*", copy_text)
        if m:
            blocks = extract_prompt_blocks_from_text(m.group(0))

    if not blocks:
        print("⚠️ 绘图指令解析失败，启用 fallback 5 图模板...", file=sys.stderr)
        blocks = build_fallback_prompt_blocks(title, _content, contract, image_copy_plan, sku_ref, sku_profile)

    out_media_dir = media_out_base / f"{args.date}_skill_{strategy}_{content_type}_SKU{sku}"
    out_media_dir.mkdir(parents=True, exist_ok=True)

    out_images = []
    image_failures = []
    for idx, blk in enumerate(blocks, 1):
        blk = enforce_scene_rules(blk, idx, strategy, args, contract, image_copy_plan, sku_ref)
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

        success = False
        last_err = None
        for attempt in range(1, 3):
            try:
                run_capture_filtered(
                    image_cmd,
                    env=image_env,
                    timeout=1800,
                    stdout_filter=lambda line: is_unsafe_worker_media_line(line, out_media_dir),
                )
                success = True
                out_images.append(str(fn))
                break
            except Exception as e:
                last_err = e
                print(f"Image generation failed for block {idx} [attempt {attempt}/2]: {e}", file=sys.stderr)
        if not success:
            image_failures.append({"index": idx, "file": str(fn), "error": str(last_err)})

    if image_failures:
        raise RuntimeError(f"Image generation failures: {json.dumps(image_failures, ensure_ascii=False)}")

    contract_path = out_dir / "00_图文一致性约束.json"
    contract_payload = {**contract, "image_copy_plan": image_copy_plan, "image_text_rule": IMAGE_TEXT_RULE, "packaging": sku_ref.get("pack")}
    contract_path.write_text(json.dumps(contract_payload, ensure_ascii=False, indent=2), encoding="utf-8")

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
                f"- consistency_contract: `{contract_path}`",
                f"- pet_contract: {json.dumps(contract, ensure_ascii=False)}",
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
