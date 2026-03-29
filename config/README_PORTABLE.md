# Glumoo XHS SOP Portable Pack

这个包的目标：
把整套 **Glumoo 小红书 SOP** 迁移到另一台 OpenClaw 机器上，做到：
- 默认可直接跑 **review-only**（生成文案 + 图片）
- 不打包任何真实密钥
- 默认预留 **Yunwu 文本 + Yunwu 生图** 两组接入位
- 目标机器只要补齐 **API Key + 路径 + SKU 参考图** 就能直接生成

---

## 一、这个包里有什么

- `skills/xhs-glumoo-sop/SKILL.md`
- `skills/xhs-glumoo-sop/PET_SCENE_PERSONA_SOP.md`
- `skills/xhs-glumoo-sop/config/themes.json`
- `skills/xhs-glumoo-sop/config/.env.portable.example`
- `skills/xhs-glumoo-sop/scripts/run_xhs_sop.py`
- `worker_bundle/glumoo_factory_v4.6.1_FESTIVAL_FINAL.py`
- `worker_bundle/xhs_auto_post.sh`

---

## 二、这个包里没有什么

不会包含：
- Gemini API Key
- 小红书登录态
- `mcporter.json` 的私密配置
- 每日产出的文案和图片结果

---

## 三、目标机器最少需要补什么

### 1）API Key
推荐直接填这两组：
- `XHS_TEXT_API_KEY`
- `XHS_IMAGE_API_KEY`

默认配套模型 / endpoint 已预设为：
- `XHS_TEXT_BASE_URL=https://yunwu.ai`
- `XHS_TEXT_MODEL=models/gemini-3.1-flash-lite-preview`
- `XHS_IMAGE_BASE_URL=https://yunwu.ai`
- `XHS_IMAGE_MODEL=gemini-3.1-flash-image-preview`

如果对方不用 yunwu，也可以改回官方 Gemini：
- `GOOGLE_API_KEY`
- `GEMINI_API_KEY`

### 2）三个路径
推荐放到环境变量里：
- `XHS_WORKSPACE_WORKER`
- `XHS_DAILY_OUT_BASE`
- `XHS_REF_DIR`

### 3）SKU 参考图
这次 portable 包里已经一并带上 6 张参考图，位于：
- `ref_images/sku1.png`
- `ref_images/sku1小包装.png`
- `ref_images/sku2.jpg`
- `ref_images/sku2小包装.png`
- `ref_images/sku3.jpg`
- `ref_images/sku3小包装.png`

迁移时只要把它们复制到目标机器的 `XHS_REF_DIR` 即可。

只要 API Key + 路径补齐，**review-only** 就能跑。

---

## 四、推荐目录结构

```bash
~/openclaw-xhs-worker/
  bundles/_unpacked/xhs_glumoo_pipeline/
    glumoo_factory_v4.6.1_FESTIVAL_FINAL.py
    xhs_auto_post.sh
    skills/nano-banana-pro/scripts/generate_image.py

~/Glumoo/02_每日内容生成/
~/Glumoo/产品资料/产品照/三款产品/
```

---

## 五、迁移步骤

### Step 1：解压 portable zip
把 zip 解压到目标 OpenClaw workspace。

### Step 2：复制 worker 文件
把：
- `worker_bundle/glumoo_factory_v4.6.1_FESTIVAL_FINAL.py`
- `worker_bundle/xhs_auto_post.sh`

放到：
- `$XHS_WORKSPACE_WORKER/bundles/_unpacked/xhs_glumoo_pipeline/`

### Step 3：配置环境变量
参考：
- `skills/xhs-glumoo-sop/config/.env.portable.example`

推荐直接复制一份并填写：
```bash
cp skills/xhs-glumoo-sop/config/.env.portable.example .env
```

至少把下面两项替换成目标机器自己的 key：
- `XHS_TEXT_API_KEY`
- `XHS_IMAGE_API_KEY`

### Step 4：放 SKU 参考图
把 6 张 SKU 参考图放入 `XHS_REF_DIR`。

### Step 5：测试 review-only
示例：

```bash
XHS_WORKSPACE_WORKER="~/openclaw-xhs-worker" \
XHS_DAILY_OUT_BASE="~/Glumoo/02_每日内容生成" \
XHS_REF_DIR="~/Glumoo/产品资料/产品照/三款产品" \
XHS_TEXT_API_KEY="your_yunwu_text_key" \
XHS_TEXT_BASE_URL="https://yunwu.ai" \
XHS_TEXT_MODEL="models/gemini-3.1-flash-lite-preview" \
XHS_IMAGE_API_KEY="your_yunwu_image_key" \
XHS_IMAGE_BASE_URL="https://yunwu.ai" \
XHS_IMAGE_MODEL="gemini-3.1-flash-image-preview" \
python3 skills/xhs-glumoo-sop/scripts/run_xhs_sop.py \
  --auto-theme \
  --auto-sku \
  --auto-content-type \
  --review-only
```

---

## 六、如果还要发布到小红书
只有生成不需要小红书登录态。\n如果你还要 publish，再补下面三项：

- 安装 `mcporter`
- 配置小红书 MCP
- 在目标机器扫码登录

也就是说：
- **review-only：只要 Gemini Key 就能跑**
- **publish：还要补小红书 MCP 登录态**

---

## 七、当前这套 SOP 已经内置的规则

- SKU 轮换
- 宠物品种轮换
- 马来西亚中高端华人养宠场景
- 主人同框优先
- 豪车低调露出
- 文案 / 图 / 包装 / 外貌锚点一致
- review-only 与 publish 分离

---

## 八、迁移成功标准

目标机器上满足以下 4 点，就算迁移成功：
- 能跑出当天正文
- 能跑出 5 张图
- 生成路径正确
- 不需要再改主逻辑代码
