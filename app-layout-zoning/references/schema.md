# zones.json 结构

`zones.json` 用来描述一张截图上的矩形分区。

## 最小示例

```json
{
  "image": "01.png",
  "zones": [
    {
      "id": "header",
      "label": "顶部搜索与入口",
      "x": 0,
      "y": 0,
      "width": 750,
      "height": 420,
      "color": "#FF8A00"
    },
    {
      "id": "banner",
      "label": "活动 Banner",
      "x": 0,
      "y": 420,
      "width": 750,
      "height": 220
    }
  ]
}
```

## 顶层字段

- `image`: 可选。建议写图片文件名，用来避免拿错截图。
- `zones`: 必填。数组，至少包含一个分区。

## 分区字段

- `id`: 必填。英文或稳定标识，必须唯一。
- `label`: 必填。展示给人看的中文名称。
- `x`: 必填。左上角横坐标，整数，单位像素。
- `y`: 必填。左上角纵坐标，整数，单位像素。
- `width`: 必填。分区宽度，正整数。
- `height`: 必填。分区高度，正整数。
- `color`: 可选。十六进制颜色，例如 `#FF8A00`；不填时脚本自动分配。

## 规则

- 所有坐标基于原图左上角
- 第一版只支持矩形分区
- 分区允许留白，但留白会体现在 `uncovered_pct`
- 分区不建议重叠；如果重叠，脚本会在校验结果中报告

## 输出重点

脚本会导出：

- 标注图：`annotated.png`
- 结构化统计：`stats.json`
- 便于表格处理的扁平结果：`stats.csv`

`stats.json` 中重点关注：

- `zones[].coverage_pct`
- `summary.coverage_pct`
- `summary.uncovered_pct`
- `validation.out_of_bounds`
- `validation.overlaps`
