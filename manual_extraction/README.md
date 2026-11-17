# 寄存器表抽取（PyMuPDF）

真实脚本，不是示例代码。在 TI 手册上抽出了 300+ 张寄存器表。

## 用法

    python extract_register_tables.py --pdf path/to/manual.pdf
    python extract_register_tables.py --pdf manual.pdf --max-pages 200

输出：

    out/raw/<table-id>.md     保真文本（按 Table 标题锚点聚合，含续表）
    out/csv/<table-id>.csv    当页面有可检测的表格几何时输出结构化版本
    out/manifest.csv          表号 / 标题 / 页码 / 行列统计

## 思路

1. 用表标题正则（`Table x-y. Title`）做锚点，把跨页内容归到同一张表；
2. 先用纯文本块兜底（保证每张表至少有内容），再用 `page.find_tables()` 尝试结构化；
3. 过滤页眉页脚与版权行，避免污染。

## 局限

- 无框线表格、合并单元格、跨页续表需要额外规则；
- 位域图（bit 编号画在矢量图里）无法从文本层还原，只能靠相邻的字段描述表反推。

这两条是这类抽取任务的真实上限，也是为什么生产版本要配人工校对白名单。
