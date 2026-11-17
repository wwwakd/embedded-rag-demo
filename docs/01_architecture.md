# 架构

    PDF 手册
      │
      ├─ manual_extraction/extract_register_tables.py
      │     表标题锚点（Table x-y）+ page.find_tables() 几何检测
      │     → raw markdown（保真） + 结构化 CSV（可用）
      │
      └─ retrieval/chunking.py
            标题层级 → section；表格独立成块；注入 section 标题 + zh 摘要
            →
      retrieval/normalize.py     查询侧：实体归一化 + 中英术语扩展
            ↓
      retrieval/hybrid.py        TF-IDF(char 2-5gram) + BM25 ──加权融合──> 章节聚合
            ↓
      retrieval/rerank_gate.py   导航题跳过重排 / 事实题词覆盖重排
            ↓
      eval/run_eval.py           section@1 / section@3 / hit@5 + 消融

## 模块职责

| 模块 | 输入 | 输出 | 说明 |
|---|---|---|---|
| chunking | markdown | Chunk[] | 块自带 section_id/title/zh，切分不丢上下文 |
| normalize | query | 归一化 query + 实体表 | GPIO12/gpio 12 → GPIO12；中文术语 → 英文术语 |
| bm25 | 文档集 | 稀疏打分 | 英文词面，抓寄存器名与术语 |
| hybrid | query | (chunk, score)[] | 两路归一化融合；章节分取块分最大值 |
| rerank_gate | query | bool | 导航题不重排，避免压掉章节入口 |
| run_eval | questions | 指标 | 支持 --ablate 做消融 |

## 为什么评测做到 section 级而不是 answer 级

答案对不对受生成模型影响，章节对不对只受检索影响。
把两件事分开量，改检索的时候才能确认是检索变好了，而不是模型当天状态好。
