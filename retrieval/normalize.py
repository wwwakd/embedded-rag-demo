"""Entity normalization and CN/EN term aliasing.

Two failures this fixes:
  1. the same register is written GPIO12 / GPIO 12 / gpio12 in user queries;
  2. the Chinese term never appears in the English manual (input qualification vs
     "输入限定"), so lexical retrieval has nothing to match.
"""

from __future__ import annotations

import re

# Chinese term -> English term used in the manual.
TERM_ALIASES = {
    "复用": "mux multiplex",
    "多路复用": "mux multiplex",
    "方向": "direction gpadir",
    "上拉": "pull-up pud",
    "下拉": "pull-down pud",
    "输入限定": "input qualification qsel",
    "采样窗口": "acquisition window acqps",
    "采样周期": "sampling period qualprd",
    "死区": "dead band",
    "时基": "time base tbprd",
    "占空比": "duty cycle cmpa",
    "触发": "trigger soc etsel",
    "序列器": "sequencer",
    "转换结果": "conversion result adcresult",
    "时钟使能": "clock enable pclkcr",
}

GPIO_ENTITY = re.compile(r"(?i)\bgpio\s*([0-9]{1,2})\b")
REGISTER = re.compile(r"\b(GPA|GPB|GPC)(MUX1|MUX2|DIR|DAT|SET|CLEAR|TOGGLE|QSEL1|QSEL2|PUD|CTRL)\b", re.I)


class EntityNormalizer:
    def normalize(self, query: str) -> str:
        text = query
        text = GPIO_ENTITY.sub(lambda m: f"GPIO{m.group(1)}", text)
        text = REGISTER.sub(lambda m: (m.group(1) + m.group(2)).upper(), text)
        return text

    def expand(self, query: str) -> str:
        norm = self.normalize(query)
        extra = [en for zh, en in TERM_ALIASES.items() if zh in norm]
        if not extra:
            return norm
        return norm + " " + " ".join(extra)

    def entities(self, query: str) -> list[str]:
        found = [f"GPIO{m.group(1)}" for m in GPIO_ENTITY.finditer(query)]
        found += [(m.group(1) + m.group(2)).upper() for m in REGISTER.finditer(query)]
        seen, out = set(), []
        for e in found:
            if e not in seen:
                seen.add(e)
                out.append(e)
        return out
