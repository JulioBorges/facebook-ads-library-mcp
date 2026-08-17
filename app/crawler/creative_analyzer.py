"""Regex-only creative text analyzer (Q30)."""

import re
from typing import Any

CTA_REGEX = re.compile(
    r"(?i)\b(compre agora|comprar agora|compre já|saiba mais|cadastre-se|assine já|"
    r"baixe agora|baixe o app|fale conosco|solicite um orçamento|peça seu orçamento|"
    r"garanta o seu|aproveite|peça já|clique aqui|acesse o link|shop now|learn more|"
    r"sign up|download|contact us|get offer|subscribe|order now|claim now|book now)\b"
)

URGENCY_REGEX = re.compile(
    r"(?i)\b(últimas vagas|últimas unidades|tempo limitado|só hoje|apenas hoje|últimas horas|"
    r"oferta limitada|acaba hoje|corre|não perca|restam poucos|desconto de \d+%|cupom válido|"
    r"urgente|por tempo limitado|limited time|last chance|ends today|hurry|flash sale|ending soon)\b"
)

VALUE_TRIGGERS_REGEX = re.compile(
    r"(?i)\b(exclusivo|grátis|frete grátis|garantia incondicional|garantia de 7 dias|"
    r"garantia|segredo|método|transformação|resultado comprovado|comprovado|fórmula|"
    r"passo a passo|descubra como|revolucionário|inédito|premium|special offer|free shipping|"
    r"proven results|satisfaction guaranteed)\b"
)


def analyze_creative_text(text: str) -> dict[str, Any]:
    """Analyze ad copy and text using deterministic regex patterns (Q30)."""
    if not text:
        return {
            "cta_detected": [],
            "urgency_triggers": [],
            "value_propositions": [],
            "word_count": 0,
            "char_count": 0,
        }

    ctas = sorted({m.group(0).title() for m in CTA_REGEX.finditer(text)})
    urgency = sorted({m.group(0).title() for m in URGENCY_REGEX.finditer(text)})
    value_props = sorted({m.group(0).title() for m in VALUE_TRIGGERS_REGEX.finditer(text)})

    words = text.split()

    return {
        "cta_detected": ctas,
        "urgency_triggers": urgency,
        "value_propositions": value_props,
        "word_count": len(words),
        "char_count": len(text),
    }
