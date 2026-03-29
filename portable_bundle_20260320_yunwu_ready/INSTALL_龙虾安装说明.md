# Glumoo 小红书 SOP 安装说明

## 1）拿包并解压
把这个包解压到目标机器的 OpenClaw 工作目录：

`xhs-glumoo-sop_portable_20260320_yunwu_ready.zip`

## 2）放置 worker 文件
把压缩包里的这些文件放到目标机器：
- `worker_bundle/glumoo_factory_v4.6.1_FESTIVAL_FINAL.py`
- `worker_bundle/xhs_auto_post.sh`
- `worker_bundle/skills/nano-banana-pro/scripts/generate_image.py`

目标目录建议：
```bash
$XHS_WORKSPACE_WORKER/bundles/_unpacked/xhs_glumoo_pipeline/
$XHS_WORKSPACE_WORKER/bundles/_unpacked/xhs_glumoo_pipeline/skills/nano-banana-pro/scripts/
```

## 3）放 SKU 参考图
把这 6 张图放到：`$XHS_REF_DIR`
- `sku1.png`
- `sku1小包装.png`
- `sku2.jpg`
- `sku2小包装.png`
- `sku3.jpg`
- `sku3小包装.png`

## 4）配置环境变量
参考：`skills/xhs-glumoo-sop/config/.env.portable.example`

最少填写：
```bash
XHS_WORKSPACE_WORKER=~/openclaw-xhs-worker
XHS_DAILY_OUT_BASE=~/Glumoo/02_每日内容生成
XHS_REF_DIR=~/Glumoo/产品资料/产品照/三款产品

XHS_TEXT_API_KEY=你的_yunwu_文本_key
XHS_TEXT_BASE_URL=https://yunwu.ai
XHS_TEXT_MODEL=models/gemini-3.1-flash-lite-preview

XHS_IMAGE_API_KEY=你的_yunwu_生图_key
XHS_IMAGE_BASE_URL=https://yunwu.ai
XHS_IMAGE_MODEL=gemini-3.1-flash-image-preview
XHS_IMAGE_ASPECT_RATIO=4:5
```

## 5）先跑 review-only 测试
```bash
python3 skills/xhs-glumoo-sop/scripts/run_xhs_sop.py \
  --auto-theme \
  --auto-sku \
  --auto-content-type \
  --review-only
```

跑通标准：
- 能生成正文
- 能生成 5 张图
- 输出目录正常
- 文案、SKU、包装、图片一致

## 6）如果之后要接小红书发布
- review-only：填 yunwu key 就能跑
- publish：还要补 `mcporter`、小红书 MCP 配置、目标机器扫码登录

## 7）这套 SOP 已固定的能力
- 自动轮换 SKU
- 自动轮换内容类型
- 马来西亚场景
- 主人同框优先
- 包装与文案强一致
- review-only / publish 分离
- 已预留 yunwu 文本与生图接口
