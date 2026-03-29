# OpenClaw Agent Handoff — Glumoo XHS Portable Pack

你是接手这个包的 OpenClaw 代理。你的目标不是解释历史，而是**在新机器上自主恢复这套 Glumoo 小红书生成系统**。

## 你的任务
请基于当前压缩包内容，自主完成以下事情：

1. 读取 `PORTABLE_MANIFEST.json`
2. 读取 `README_PORTABLE.md`
3. 理解目录中这些关键资产：
   - `skills/xhs-glumoo-sop/SKILL.md`
   - `skills/xhs-glumoo-sop/PET_SCENE_PERSONA_SOP.md`
   - `skills/xhs-glumoo-sop/scripts/run_xhs_sop.py`
   - `worker_bundle/glumoo_factory_v4.6.1_FESTIVAL_FINAL.py`
   - `worker_bundle/xhs_auto_post.sh`
   - `ref_images/*`

## 成功标准
你需要在目标机器上恢复出一个可运行的 **review-only** Glumoo XHS 生成系统，使其满足：
- 能生成当天标题与正文
- 能生成 5 张图
- 能使用正确 SKU 包装参考图
- 能遵守马来西亚中高端华人养宠场景规则
- 能执行宠物品种轮换 / SKU轮换 / 场景轮换 / 内容类型轮换

## 你必须自行识别的迁移动作
### A. 放置 skill
把：
- `skills/xhs-glumoo-sop/`
放到目标 OpenClaw workspace 的 skills 目录中。

### B. 放置 worker 文件
把：
- `worker_bundle/glumoo_factory_v4.6.1_FESTIVAL_FINAL.py`
- `worker_bundle/xhs_auto_post.sh`
复制到目标机器的：
- `$XHS_WORKSPACE_WORKER/bundles/_unpacked/xhs_glumoo_pipeline/`

### C. 放置产品参考图
把：
- `ref_images/sku1.png`
- `ref_images/sku1小包装.png`
- `ref_images/sku2.jpg`
- `ref_images/sku2小包装.png`
- `ref_images/sku3.jpg`
- `ref_images/sku3小包装.png`
复制到：
- `$XHS_REF_DIR`

### D. 环境变量
至少确保以下变量可用：
- `GOOGLE_API_KEY` 或 `GEMINI_API_KEY`
- `XHS_WORKSPACE_WORKER`
- `XHS_DAILY_OUT_BASE`
- `XHS_REF_DIR`

## 默认原则
如果用户没有特别要求，你应优先恢复并验证 **review-only** 版本，而不是 publish 版本。

原因：
- review-only 只需要 Gemini key + 路径 + 参考图
- publish 还依赖小红书 MCP 与登录态，不应默认假设可用

## publish 是可选增强
只有当目标机器明确具备以下条件时，才启用 publish：
- 安装了 `mcporter`
- 配好了小红书 MCP
- 已扫码登录成功

## 你应该如何验证迁移成功
建议最少执行一次：

```bash
python3 skills/xhs-glumoo-sop/scripts/run_xhs_sop.py \
  --auto-theme \
  --auto-sku \
  --auto-content-type \
  --review-only
```

并验证：
- 生成目录中有正文
- 有生图提示词
- 有 5 张图
- 没有再依赖原机器的 `/Users/Apple/...` 绝对路径

## 约束
- 不要编造用户没有给的密钥
- 不要假装 publish 可用
- 先恢复 review-only，再谈发布链路
- 发现路径错误时，应自动修正为目标机器路径，而不是沿用原机绝对路径

## 结论
这个包的设计意图是：
**给另一个 OpenClaw 代理后，它应该能够靠阅读本包内容，自主完成部署与恢复。**
