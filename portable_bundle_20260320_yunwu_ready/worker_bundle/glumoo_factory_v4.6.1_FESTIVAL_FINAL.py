import os
import requests
import re
import datetime

# Glumoo 智能生产线 v4.6.2 (STRATEGY UPGRADE)
# - 在原有内容工厂基础上，加入发现页/搜索页双策略骨架
# - 允许从外层 SOP 传入 audience / pain point / scenario / conversion goal / core keywords
# - 保留品牌三句、固定标签、Malaysia 场景、合规边界

API_KEY = (
    os.environ.get("XHS_TEXT_API_KEY")
    or os.environ.get("YUNWU_GEMINI_API_KEY")
    or os.environ.get("XHS_IMAGE_API_KEY")
    or os.environ.get("GEMINI_API_KEY")
    or os.environ.get("GOOGLE_API_KEY")
)
BASE_URL = (
    os.environ.get("XHS_TEXT_BASE_URL")
    or os.environ.get("XHS_IMAGE_BASE_URL")
    or os.environ.get("GEMINI_BASE_URL")
    or os.environ.get("GOOGLE_GENAI_BASE_URL")
    or "https://generativelanguage.googleapis.com"
).rstrip("/")
BASE_DIR = "/Users/Apple/Documents/Glumoo/02_每日内容生成"

MODEL_PRIORITY = [
    os.environ.get("XHS_TEXT_MODEL")
    or os.environ.get("GEMINI_TEXT_MODEL")
    or os.environ.get("GEMINI_MODEL")
    or "models/gemini-3-pro-preview",
    "models/gemini-3-flash-preview",
    "models/gemini-2.5-pro",
    "models/gemini-2.5-flash",
]


def build_auth_headers(api_key: str, base_url: str) -> dict:
    if "generativelanguage.googleapis.com" in base_url:
        return {
            "Content-Type": "application/json",
            "x-goog-api-key": api_key,
        }
    return {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }

FIXED_TAGS = [
    "#Glumoo",
    "#Glumoo氨糖羊奶粉",
    "#Glumoo关节守护",
    "#GlumooNAG",
    "#宠物羊奶粉",
]

BRAND_LINES = [
    "日本品牌，马来西亚制造（Japanese brand, Made in Malaysia）",
    "纯植物基发酵 NAG（plant-based fermented NAG）",
    "Glumoo 植物基发酵，给他0负担的爱",
]

CORE_KNOWLEDGE_BASE = r'''
# Glumoo 终极核心资料库 (v2.4 - 完整修复版)

---
## ❗ 第一部分：创作铁律与执行细则 (最高优先级)

### 1. 核心定位
深谙大马市场、极强落地执行力的品牌官方。卖的是"场景"和"结果"，绝非"参数"。

### 1.1 品牌口径「三条铁律」（强制）
> 任何平台（小红书/TikTok/Shopee/私域）文案都必须遵守。
- 身份必带：日本品牌，马来西亚制造（Japanese brand, Made in Malaysia）。
- 成分必带：纯植物基发酵 NAG（plant-based fermented NAG）。
- Slogan 必带：Glumoo 植物基发酵，给他0负担的爱

### 2. 文本输出「四大铁律」
- 标签强制包含: 所有文案必须在正文末尾挂载 "5个固定标签 + 5个动态爆款标签"，严禁拆分。
- 严禁说教黑话: 杜绝营销腔，说用户在乎的体感。
- 标题 20 字熔断: 标题严格限制在 20 个汉字/符号内。
- 纯文本输出: 严禁 Markdown 加粗符号 (**)。
- 允许少量表情/颜文字: 为了更像马来西亚华人小红书日常口吻，允许在正文中自然插入少量 emoji / 颜文字（例如：🥹✨😮‍💨🐾、(ง •̀_•́)ง、(ಥ_ಥ)、Aiyo…）。要求：每段最多 1-2 个，不要刷屏，不要影响阅读。

### 3. 视觉与 AI Prompt (3:4 精修)
- 图片数量: 4-6张。
- 风格: 必须是真实拍照感。
- 场景: 必须是马来西亚本地特色场景。
- 图中文字: 自然融入图片，醒目但不突兀。
- 封面图: 必须采用爆款设计思维，将核心价值点（钩子）与标题强关联并前置。

---
## 📦 第三部分：SKU 产品手册详解 (唯一且完整的事实来源)

### SKU 1: 多维力 (Multiforce) - 深蓝关节款
- 喂养场景: 拌饭最佳伴侣/骗水神器。

### SKU 2: 跃力 (Senior Foria) - 肉粉老年猫款
- 定位: 专为7岁以上老年猫/犬设计的关节营养品。
- 受众补充: 贵宾犬、老龄犬、大型犬、老猫、缅因猫。
- 核心卖点:
    1) NAG精准关节修复: 医药级，吸收率优，肝肾无负担。
    2) 黄金奶源: 新西兰进口A2蛋白奶源，低乳糖。
    3) 高适口性: 添加磷虾粉和鱼粉，自然提味。
    4) 全面营养: 含菊粉（益生元），无谷物。
- 喂养场景: 拌饭最佳伴侣/骗水神器。
- 喂食: 1条兑30-50ml温水，或拌粮/手喂。

### SKU 3: 畅清 (Gut Care) - 天蓝肠道款
- 喂养场景: 拌饭最佳伴侣/骗水神器。

---
## 🗣️ 第四部分：马来西亚华人语言特点与文案风格指南
- 自然中英混用 + 少量马来语口头禅（Aiyo、lah、lor、steady 等），中文为主英文为辅。
- 自然不刻意，保持可读性。

---
## ✅ 合规边界（强制执行）
- 严禁虚构/夸大疗效、热度、数据。
- 禁止输出不在事实库里的“科学数值结论/绝对化结论”（例如“3倍吸收/0 BCM-7”等），除非事实库明确给出且允许对外表达。
'''


def call_gemini_with_retry(prompt: str):
    if not API_KEY:
        raise RuntimeError("Missing GEMINI_API_KEY / GOOGLE_API_KEY")

    for model_id in MODEL_PRIORITY:
        if not model_id:
            continue
        print(f"  - 尝试使用模型: {model_id}")
        try:
            url = f"{BASE_URL}/v1beta/{model_id}:generateContent"
            payload = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"temperature": 0.8},
            }
            response = requests.post(
                url,
                json=payload,
                timeout=90,
                headers=build_auth_headers(API_KEY, BASE_URL),
            )
            if response.status_code != 200:
                print(f"    ❌ 模型报错 ({response.status_code}): {response.text[:200]}")
                continue

            text = response.json()["candidates"][0]["content"][0]["parts"][0]["text"] if isinstance(response.json()["candidates"][0]["content"], list) else response.json()["candidates"][0]["content"]["parts"][0]["text"]
            if "绘图指令" not in text:
                print("    ❌ 返回缺少绘图指令，重试下一个模型...")
                continue
            return text
        except Exception as e:
            print(f"    ❌ 网络错误: {e}")
    return None


def _ensure_brand_lines(text: str) -> str:
    if not text:
        return text
    out = text.rstrip()
    for line in BRAND_LINES:
        if line not in out:
            out += "\n" + line
    return out


def _ensure_fixed_tags(text: str) -> str:
    if not text:
        return text
    out = text.rstrip()
    missing = [t for t in FIXED_TAGS if t not in out]
    if missing:
        out += "\n" + " ".join(missing)
    return out


def parse_output(raw_content: str):
    title = re.search(r"标题：\s*(.*?)(?:\n|$)", raw_content, re.DOTALL)
    body = re.search(r"正文：\s*(.*?)(?:\n绘图指令：|$)", raw_content, re.DOTALL)
    prompts = re.search(r"绘图指令：\s*(.*)", raw_content, re.DOTALL)

    parsed_title = title.group(1).strip() if title else "【标题生成失败】"
    parsed_body = re.sub(r"\*\*|\*", "", body.group(1).strip()) if body else "【正文生成失败】"
    parsed_prompts = prompts.group(1).strip() if prompts else "【绘图指令生成失败】"

    parsed_body = _ensure_brand_lines(parsed_body)
    parsed_body = _ensure_fixed_tags(parsed_body)

    return parsed_title, parsed_body, parsed_prompts


def strategy_fields():
    return {
        "strategy": os.environ.get("XHS_STRATEGY", "discovery"),
        "strategy_brief": os.environ.get("XHS_STRATEGY_BRIEF", "").strip(),
        "audience": os.environ.get("XHS_AUDIENCE", "泛养宠家庭").strip(),
        "pain_point": os.environ.get("XHS_PAIN_POINT", "多宠家庭喂养与营养管理").strip(),
        "scenario": os.environ.get("XHS_SCENARIO", "马来西亚多宠家庭日常").strip(),
        "conversion_goal": os.environ.get("XHS_CONVERSION_GOAL", "激发兴趣与收藏").strip(),
        "core_keywords": os.environ.get("XHS_CORE_KEYWORDS", "Glumoo, 多宠家庭, 宠物营养").strip(),
        "pet_type": os.environ.get("XHS_PET_TYPE", "dog").strip(),
        "pet_breed": os.environ.get("XHS_PET_BREED", "玩具体贵宾（泰迪风）").strip(),
        "pet_anchor": os.environ.get("XHS_PET_ANCHOR", "浅杏棕色卷毛，小体型，圆脸，杏眼，黑色小鼻头").strip(),
        "cover_copy_rule": os.environ.get("XHS_COVER_COPY_RULE", "封面必须带强关联短文案").strip(),
        "packaging_rule": os.environ.get("XHS_PACKAGING_RULE", "产品外盒与小包装必须和SKU严格一致，不可串包装").strip(),
    }


def build_strategy_prompt(fields: dict, content_type: str) -> str:
    strategy = fields["strategy"]
    audience = fields["audience"]
    pain_point = fields["pain_point"]
    scenario = fields["scenario"]
    conversion_goal = fields["conversion_goal"]
    core_keywords = fields["core_keywords"]
    pet_type = fields["pet_type"]
    pet_breed = fields["pet_breed"]
    pet_anchor = fields["pet_anchor"]
    cover_copy_rule = fields["cover_copy_rule"]
    packaging_rule = fields["packaging_rule"]
    extra_brief = fields["strategy_brief"]

    common = f'''
商业上下文（必须消化后再写，不要原样照抄）：
- 当前策略: {strategy}
- 目标人群: {audience}
- 核心痛点: {pain_point}
- 真实场景: {scenario}
- 转化目标: {conversion_goal}
- 核心关键词: {core_keywords}
- 宠物类型: {pet_type}
- 宠物品种: {pet_breed}
- 宠物外貌锚点: {pet_anchor}
- 封面文案规则: {cover_copy_rule}
- 包装规则: {packaging_rule}
{extra_brief}
'''

    if strategy == "search":
        return common + f'''
【搜索页打法】
你现在不是在写泛种草文，而是在拦截用户决策。
要求：
1) 标题优先围绕“核心词 + 细分人群 + 痛点/场景”来写，避免空泛情绪词。
2) 正文结构优先使用：问题/症状 -> 原因解释 -> 解决方案 -> 使用方式/判断依据 -> 产品作为可选解法。
3) 语气要像懂用户的人，不要像广告，不要追求虚高互动。
4) 尽量让用户看完感觉“这篇正好说的是我”。
5) 在不堆砌的前提下，自然融入搜索词和场景词。
6) {content_type} 类型也要服从搜索页逻辑，重点是转化和决策支持。
优先可借用这些内容模板：求助型、测评/避雷型、经验科普型、晒结果型、体验教程型。
'''

    return common + f'''
【发现页打法】
你现在是在做货找人的情绪种草。
要求：
1) 标题优先制造第一眼吸引力、生活方式代入感和想点开的冲动。
2) 正文结构优先使用：生活场景/情绪切口 -> 真实体验/前后变化 -> 产品自然出现 -> 评论区互动承接。
3) 允许有一点向往感、轻松感，但不要悬浮，不要硬广。
4) 要让用户在本来没有明确需求时，也会觉得“这个好像适合我家毛孩”。
5) {content_type} 类型也要服从发现页逻辑，重点是画面感、情绪价值和收藏分享欲。
优先可借用这些内容模板：日常陪伴、轻体验、反差前后、周末生活感、低门槛种草。
'''


def generate_smart(date_str, theme, product_focus, holiday=None, content_type="科普"):
    print(f"🚀 开始生产 {date_str} - {theme} | 类型: {content_type}...")
    if holiday:
        print(f"✨ 节日模式已激活: {holiday}")

    holiday_instruction = ""
    if holiday:
        holiday_instruction = f"\n节日背景：今天是 {holiday}，请将节日氛围（团圆/祝福/庆典等）自然融入。"

    fields = strategy_fields()
    strategy_prompt = build_strategy_prompt(fields, content_type)

    sop_prompt = f'''你是一位严格遵循品牌资料的 Glumoo 内容运营。{holiday_instruction}
你的唯一事实来源是这份"产品事实库"：
{CORE_KNOWLEDGE_BASE}

内容类型：{content_type}
- 若为“科普”：采用“症状/异常行为 -> 原因解释 -> 可执行建议 -> 产品作为可选解决方案”的结构，语气专业但不说教。
- 若为“体验”：采用“使用前后对比 + 过程记录 + 真实感受”的结构。
- 若为“故事”：采用“陪伴叙事 + 生活细节 + 情绪价值”的结构。
- 若为“挑战”：给出可参与的挑战玩法与话题标签。
- 若为“转化”：给出更偏晒单/开箱/购买建议的结构，但不夸大。
- 若为“对比”：采用“使用场景对比/人群对比/方案对比”的结构，帮助用户选型。
- 若为“测评”：采用“多维评价 + 真实体验 + 适用人群”的结构。
- 若为“避雷”：采用“常见误区/错误做法 -> 正确判断”的结构，但不要恐吓。
- 若为“教程”：采用“步骤拆解 + 使用门槛降低 + 新手友好”的结构。
- 若为“搜索”：按高意图搜索内容来写，优先解决问题。

最高指令：
1) 严禁虚构任何事实库中不存在的细节。
2) 禁止输出任何不在事实库中的“科学数值结论/绝对化结论”。
3) 围绕“{product_focus}”创作关于“{theme}”的小红书内容。
4) SEO 标签：正文末尾必须包含“5个固定标签 + 5个动态爆款标签”。固定标签必须完整包含：{' '.join(FIXED_TAGS)}
5) 语言风格：马来西亚华人口吻，中英混杂自然（Aiyo、lah、lor、steady 等），但保持中文为主。

【强制品牌口径】正文中必须同时包含以下三句（建议放在结尾固定三行）：
- {BRAND_LINES[0]}
- {BRAND_LINES[1]}
- {BRAND_LINES[2]}

{strategy_prompt}

视觉增强最高指令 (VISION PRO)：
- 图片比例严格 3:4
- 真实拍照感 + 马来西亚本地特色场景（必须让人一眼看出是马来西亚）
- 图片数量 4-6 张
- 多图中宠物一致性：图片1定义“外貌锚点”，后续逐字复用
- 画面合规与元素：图片内不得出现“SKU1/SKU2/SKU3”等字样；统一使用产品名（多维力/跃力/畅清）。
- 马来西亚识别要素（强制）：每张图必须包含 1-2 个可识别线索，例如：高端 condo 社区、公寓大堂、双层高端别墅/landed villa、排屋/住宅氛围（terrace house）、铁花窗/Grille、吊扇、复古花砖/水磨石地、藤编家具、车棚走廊、热带植物、强烈热带日照与阴影。
- 场景人设（强制）：整体视觉必须服务“马来西亚中高端华人养宠家庭”人设，家居环境要整洁、有审美、有秩序，不能廉价、杂乱或像普通电商白底图。
- 城市/乡村场景映射（强制）：如果是城市场景，优先生成高端社区、高档 condo、高级公寓、城市高端住宅；如果是低密度/乡村/户外家庭场景，优先生成高端别墅、landed villa、花园庭院式住宅，不要生成破旧、低配、拥挤环境。
- 主人同框规则（强制优先）：整组图中尽量让主人自然同框，优先出现主人喂食、拌饭、陪伴、散步、互动等生活化动作；不要把宠物永远单独摆拍。若无法每张都同框，至少保证多数图片有自然的人宠互动。
- 豪车露出规则（可选但优先）：可在车棚、前院、driveway、condo 地库、门前接送等场景中低调露出高端 SUV / sedan 作为家庭身份线索，但只能做背景点缀，不可喧宾夺主，不可拍成汽车广告。
- 室内/户外（强制）：同一组图必须同时包含室内与户外场景（至少 1 张室内 + 1 张户外）。
- 品牌角标规则（强制）：仅封面图（图片1）必须在画面中加入固定角标/贴纸“日本品牌｜大马制造”（清晰可读，位置固定在右下角）。图片2-6可不强制出现该角标。
- 宠物规则（强制）：
  - 本次生成使用的宠物品种必须严格等于商业上下文中的“宠物品种”，不得自行替换成别的狗/猫品种。
  - 图片1必须先定义宠物外貌锚点；图片2-6必须逐字复用该外貌锚点，确保是同一只宠物。
  - 若宠物品种为“玩具体贵宾（泰迪风）”，禁止画成标准赛级贵宾长嘴脸、比熊脸或其他卷毛犬。
  - 若文案是小型犬长期管理方向，默认优先使用家养感强、马来西亚华人家庭常见审美的画法，不要偏赛级、冷门或猎奇风格。
- 封面文案规则（强制）：
  - 图片1必须出现明确封面短文案，且要与标题强关联，不可空缺。
  - 封面短文案必须是用户一眼能看懂的口语表达，不要只有概念词。
- 包装与粉末规则（强制）：
  - 产品外盒与小包装必须和当前 SKU 严格一致，不可串包装，不可使用其他 SKU 的 stick 或外盒。
  - 凡出现“倒粉/拌饭/准备喂养”的画面，必须使用当前 SKU 对应的小包装作为画面道具与参考，不能画错颜色、结构和包装形态。
  - SKU2（跃力 Senior Foria）包装为肉粉色，但粉末必须呈“白色为主、夹杂少量肉色/浅粉颗粒”的乳粉质感，禁止把粉末画成纯肉粉色。
- 如果当前策略是 search，图片也要服务“解决问题/判断方案/真实使用”的感觉，而不只是漂亮。
- 如果当前策略是 discovery，图片要服务“第一眼想点开、想收藏、想看同款生活”的感觉。

输出格式（严格遵守）：
标题：[20字内标题；必须以🇲🇾开头]

正文：[纯文本正文，含10个标签（5固定+5动态）]

绘图指令：
[图片1/封面图]
- 设计思维: (强反差对比/标题党排版/信息前置 任选一)
- 场景: (马来西亚中高端本地特色场景 + 真实拍照感)
- 人物安排: (主人是否同框；若同框，说明动作与互动)
- 豪车线索: (如适合则低调露出，不可抢主角)
- 画面描述: (详细描述画面)
- 封面文案: (与标题强关联)
- 文字排版: (描述文字位置)
- 图片比例: 3:4

[图片2-6]
- 图中文字: (建议有；如果有必须与该张场景功能强关联)
- 文字排版: (必须说明位置与风格)
- 场景层级: (高端社区 / 高档 condo / 高端别墅 / landed villa / 庭院 / 车棚 / 公寓室内等)
- 人物安排: (主人是否同框；优先自然互动)
- 豪车线索: (如适合则低调露出，不可抢主角)
- 画面描述(中文): (必须逐字复用图片1的外貌锚点，并严格匹配当前SKU包装)
- 图片比例: 3:4
'''

    raw_content = call_gemini_with_retry(sop_prompt)

    if raw_content:
        title, body, prompts = parse_output(raw_content)

        folder_name = f"{date_str}_{holiday or theme}_{product_focus.split(':')[0]}_v4.6.2"
        output_dir = os.path.join(BASE_DIR, re.sub(r"[\s/:]+", "_", folder_name))
        os.makedirs(output_dir, exist_ok=True)

        with open(os.path.join(output_dir, "01_正文与标签_复制即发.txt"), "w", encoding="utf-8") as f:
            f.write(f"{title}\n\n{body}")
        print(f"✅ 正文已写入: {os.path.join(output_dir, '01_正文与标签_复制即发.txt')}")

        with open(os.path.join(output_dir, "02_生图提示词_中文精修.txt"), "w", encoding="utf-8") as f:
            f.write(prompts)
        print(f"✅ 绘图指令已写入: {os.path.join(output_dir, '02_生图提示词_中文精修.txt')}")

    else:
        print("💥 生产事故：所有模型均无法响应。")


def get_malaysia_context():
    forced_date = os.environ.get("XHS_DATE", "").strip()
    forced_theme = os.environ.get("XHS_THEME", "").strip()
    forced_product = os.environ.get("XHS_PRODUCT_FOCUS", "").strip()

    now = datetime.datetime.now()
    if forced_date:
        try:
            now = datetime.datetime.strptime(forced_date, "%Y-%m-%d")
        except ValueError:
            pass

    day_month = now.strftime("%m-%d")
    weekday = now.weekday()

    m_holidays = {
        "01-01": "元旦 New Year",
        "01-29": "农历新年 Chinese New Year",
        "02-14": "情人节 Valentine's Day",
        "03-31": "开斋节 Hari Raya Puasa",
        "05-01": "劳动节 Labor Day",
        "08-31": "国庆日 Merdeka Day",
        "09-16": "马来西亚日 Malaysia Day",
        "10-20": "屠妖节 Deepavali",
        "12-25": "圣诞节 Christmas",
    }

    holiday = m_holidays.get(day_month)

    if forced_theme and forced_product:
        return now.strftime("%Y-%m-%d"), forced_theme, forced_product, None

    optimized = get_optimized_schedule(now)
    if optimized:
        return optimized

    if holiday:
        theme, sku = f"{holiday} 特别策划", "SKU 1: 多维力 (Multiforce)"
    elif weekday == 0:
        theme, sku = "新一周活力开启：告别周一综合症", "SKU 1: 多维力 (Multiforce) - 深蓝关节款"
    elif weekday == 6:
        theme, sku = "一周健康总结：爱与陪伴的记录", "SKU 2: 跃力 (Senior Foria) - 肉粉老年猫款"
    else:
        theme, sku = "日常健康守护：肠胃好便便香", "SKU 3: 畅清 (Gut Care) - 天蓝肠道款"

    return now.strftime("%Y-%m-%d"), theme, sku, holiday


def get_optimized_schedule(date_obj):
    date_str = date_obj.strftime("%Y-%m-%d")
    weekday = date_obj.weekday()

    optimized_schedule = {
        0: {"theme": "元气周一：多宠家庭的活力早餐", "product": "SKU 1: 多维力 (Multiforce) - 深蓝关节款"},
        1: {"theme": "肠道健康日：告别软便烦恼", "product": "SKU 3: 畅清 (Gut Care) - 天蓝肠道款"},
        2: {"theme": "肠道健康日：告别软便烦恼", "product": "SKU 3: 畅清 (Gut Care) - 天蓝肠道款"},
        3: {"theme": "多宠家庭解决方案：一包搞定所有", "product": "SKU 3: 畅清 (Gut Care) - 天蓝肠道款"},
        4: {"theme": "周末前的关节准备：带它去公园", "product": "SKU 1: 多维力 (Multiforce) - 深蓝关节款"},
        5: {"theme": "周末亲子时光：和毛孩子的甜蜜约会", "product": "SKU 1: 多维力 (Multiforce) - 深蓝关节款"},
        6: {"theme": "一周健康总结：粉丝真实反馈分享", "product": "SKU 2: 跃力 (Senior Foria) - 肉粉老年猫款"},
    }

    day_month = date_obj.strftime("%m-%d")
    m_holidays = {
        "01-01": "元旦 New Year",
        "01-29": "农历新年 Chinese New Year",
        "02-14": "情人节 Valentine's Day",
        "03-31": "开斋节 Hari Raya Puasa",
        "05-01": "劳动节 Labor Day",
        "08-31": "国庆日 Merdeka Day",
        "09-16": "马来西亚日 Malaysia Day",
        "10-20": "屠妖节 Deepavali",
        "12-25": "圣诞节 Christmas",
    }

    holiday = m_holidays.get(day_month)
    if holiday:
        return date_str, f"{holiday} 特别策划", "SKU 1: 多维力 (Multiforce)", holiday

    if weekday in optimized_schedule:
        schedule = optimized_schedule[weekday]
        return date_str, schedule["theme"], schedule["product"], None

    return None


if __name__ == "__main__":
    content_type = os.environ.get("CONTENT_TYPE", "科普")

    date_str, theme, sku, holiday = get_malaysia_context()
    print(f"🚀 Glumoo 动态生产线 [STRATEGY UPGRADE] | 日期: {date_str} | 任务: {theme} | 类型: {content_type}")
    generate_smart(date_str, theme, sku, holiday=holiday, content_type=content_type)
