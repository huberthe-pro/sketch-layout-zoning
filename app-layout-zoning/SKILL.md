---
name: app-layout-zoning
description: Analyze app screenshots by applying manually defined rectangle zones, generating annotated images, and calculating area share statistics for each major section. Use when the user wants to mark screenshot regions, compute module占比, export annotation artifacts, or reuse a screenshot zoning workflow.
---

# App Layout Zoning

对 App 截图做一级模块分区标注，并统计每个分区相对整张截图的面积占比。

## 什么时候用

- 用户已经有截图，想标出主要模块并统计占比
- 用户接受“人工/半自动定义分区”，不要求第一版自动识别模块边界
- 用户需要可重复运行的结果：标注图、JSON、CSV

## 输入

需要两份输入：

- 一张截图图片，例如 `image.png`
- 一份分区定义文件，例如 `zones.json`

优先阅读 [`references/schema.md`](references/schema.md) 了解 JSON 结构和字段规则。

如果客户提供了 `.sketch` 原文件，优先用 Sketch 作为分区来源：

```bash
./sketch-layout-zoning report \
  /path/to/page.sketch \
  --zones-output /path/to/sketch-zones.json \
  --json-output /path/to/sketch-stats.json \
  --csv-output /path/to/sketch-stats.csv
```

如果只想抽取分区，不做统计：

```bash
./sketch-layout-zoning extract /path/to/page.sketch --output /path/to/sketch-zones.json
```

## 标准用法

```bash
python3 app-layout-zoning/scripts/analyze_zones.py \
  /path/to/image.png \
  /path/to/zones.json \
  --output-dir /path/to/output
```

默认输出：

- `annotated.png`
- `stats.json`
- `stats.csv`

## 何时只做统计，何时需要补标注

- 如果用户已经能给出每个一级模块的矩形坐标，直接运行脚本
- 如果用户只有“人工画框图”但没有坐标，先把框整理成 `zones.json`
- 如果页面结构稳定，可以复用旧的 `zones.json` 作为模板再微调

## 校验与失败策略

脚本默认会在 `stats.json` 中报告这些问题，但仍然输出结果：

- 分区越界
- 分区重叠
- 总覆盖率不足

如果希望发现问题就直接失败，可加：

```bash
--fail-on-overlap
--fail-on-bounds
```

## 结果解释

- `coverage_pct`: 当前分区面积 / 整张截图面积
- `sum_of_zone_areas_pct`: 所有分区面积简单求和后的占比
- `summary.coverage_pct`: 去重后的联合覆盖率

当存在分区重叠时：

- `sum_of_zone_areas_pct` 可能大于 `coverage_pct`
- 应优先检查 `validation.overlaps`

## 扩展边界

这个 skill 当前只处理：

- 一级模块
- 矩形分区
- 单张截图

补充：

- `sketch-layout-zoning` 可以直接从 Sketch 中抽出最多三层的结构化 group
- `report` 会同时输出分区 JSON、统计 JSON、统计 CSV
- 统计结果包含每个元素相对整张图的占比，以及相对父级容器的占比

不要在没有明确要求时擅自扩展到：

- 二级组件拆分
- 自动视觉识别
- GUI 标注器
- 多图汇总分析
