# sketch-layout-zoning

从 Sketch 原文件中提取最多三层的页面分区，并计算每个分区的面积占比。

适合场景：

- 客户提供 `.sketch` 设计源文件
- 需要按一级、二级、三级模块做页面结构统计
- 需要同时看“占整页比例”和“占父级比例”

## 功能

- 从 Sketch 中抽取最多三层的业务分区
- 自动过滤一部分装饰性图层和通用命名图层
- 输出标准 `zones.json`
- 输出统计结果 `stats.json`
- 输出表格结果 `stats.csv`
- 输出树形层级结构，便于继续做报告

## 要求

- Python 3.11+
- 本地可运行 `python3`
- 无需安装额外依赖

## 用法

提取分区：

```bash
./sketch-layout-zoning extract /path/to/page.sketch --output sketch-zones.json
```

提取并统计：

```bash
./sketch-layout-zoning report /path/to/page.sketch \
  --zones-output sketch-zones.json \
  --json-output sketch-stats.json \
  --csv-output sketch-stats.csv
```

可选参数：

- `--page-name` 指定 Sketch page
- `--root-name` 指定目标根分组或 artboard
- `--max-depth` 控制最多提取几层，默认 `3`
- `--min-area-ratio` 过滤过小分组
- `--min-width-ratio` 过滤过窄分组

## 输出说明

`sketch-zones.json`：

- 原始分区结果
- 包含层级、父子关系、Sketch 图层 id

`sketch-stats.json`：

- `zones[].coverage_pct`：当前元素占整页的百分比
- `zones[].parent_coverage_pct`：当前元素占父级的百分比
- `level_summary`：每一层整体覆盖率
- `tree`：树形结构结果

`sketch-stats.csv`：

- 适合给表格、报表或 BI 工具继续处理

## 测试

```bash
python3 -m unittest discover -s tests -v
```

与真实 Sketch 文件相关的测试默认通过环境变量提供样例文件：

```bash
export SKETCH_LAYOUT_ZONING_FIXTURE=/path/to/example.sketch
python3 -m unittest discover -s tests -v
```

如果没有提供样例文件，这些集成测试会自动跳过。
