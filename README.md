# xhs-glumoo-sop

小红书内容生产 SOP，支持格日盈（Glumoo）宠物营养品三款 SKU 的全套创作流程。

## 功能

- 文案生成 + 图片提示词生产（支持 discovery / search 两种策略）
- 图片生成（Yunwu / Nano Banana Pro）
- 飞书审批发送
- 小红书发布（仅自己可见）
- 敏感词清洗层
- 马来西亚本地化场景支持

## 快速使用

```bash
# 加载 skill 后，运行 review 版
python3 scripts/run_xhs_sop.py \
  --strategy search \
  --content-type 科普 \
  --sku 3 \
  --theme "多宠家庭解决方案" \
  --unit-price 299 \
  --audience "多宠家庭猫狗同养人群" \
  --pain-point "多宠家庭喂养复杂" \
  --scenario "马来西亚城市家庭" \
  --review-only
```

## 文档

- `SKILL.md` — 主 skill 说明
- `PET_SCENE_PERSONA_SOP.md` — 场景/人物 SOP
- `config/themes.json` — 主题轮转配置
- `portable_bundle/` — 便携打包版（含完整依赖）
