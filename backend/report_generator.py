
# import logging
# import json
# import re
# from typing import List, Dict
# from groq import Groq

# logger = logging.getLogger(__name__)

# FALLBACK_REPORT = {
#     "executive_summary": (
#         "No relevant legal context was found for this product and region. "
#         "Consider consulting a qualified legal professional."
#     ),
#     "validity_score": 50,
#     "risk_level": "Unknown",
#     "compliance_scores": {
#         "data_privacy": 50,
#         "financial_regulation": 50,
#         "ai_regulation": 50,
#         "consumer_protection": 50,
#     },
#     "policy_relevance_chart": [
#         {"label": "Data Privacy",         "value": 25},
#         {"label": "Financial Regulation", "value": 25},
#         {"label": "AI Regulation",        "value": 25},
#         {"label": "Consumer Law",         "value": 25},
#     ],
#     "policy_relevance": [],
#     "pros": [],
#     "cons": ["Insufficient legal context to perform analysis"],
#     "recommendations": ["Consult a qualified legal professional for this jurisdiction"],
#     "citations": [],
# }


# class ReportGenerator:

#     def __init__(self, groq_client: Groq, model: str):
#         self.client = groq_client
#         self.model  = model

#     def generate(
#         self,
#         product_description: str,
#         country: str,
#         domain: str,
#         contexts: List[Dict],
#     ) -> Dict:

#         if not contexts:
#             logger.warning("No contexts — returning fallback report")
#             return FALLBACK_REPORT

#         context_block = self._build_context_block(contexts)
#         citations     = self._build_citations(contexts)

#         # Build ALL policy cards — one per unique document
#         policy_cards  = self._build_policy_cards(contexts)

#         system_prompt = (
#             "You are a legal analysis API. "
#             "You ONLY output raw JSON. "
#             "No markdown, no code fences, no explanation, no preamble. "
#             "Your entire response must be a single valid JSON object and nothing else."
#         )

#         user_prompt = f"""Analyze the legal feasibility of this product.

# PRODUCT: {product_description[:500]}
# COUNTRY: {country}
# DOMAIN: {domain}

# LEGAL CONTEXTS (ALL are relevant — use all of them):
# {context_block}

# Output ONLY this JSON (fill in real values based on the contexts above):
# {{
#   "executive_summary": "2-3 sentence overview of legal landscape for this product",
#   "validity_score": 72,
#   "risk_level": "Medium",
#   "compliance_scores": {{
#     "data_privacy": 65,
#     "financial_regulation": 70,
#     "ai_regulation": 60,
#     "consumer_protection": 75
#   }},
#   "policy_relevance_chart": [
#     {{"label": "Data Privacy", "value": 40}},
#     {{"label": "Financial Regulation", "value": 25}},
#     {{"label": "AI Regulation", "value": 20}},
#     {{"label": "Consumer Law", "value": 15}}
#   ],
#   "pros": ["advantage 1", "advantage 2"],
#   "cons": ["risk 1", "risk 2"],
#   "recommendations": ["action 1", "action 2"]
# }}

# policy_relevance_chart values must sum to 100."""

#         for attempt in range(3):
#             try:
#                 response = self.client.chat.completions.create(
#                     model=self.model,
#                     messages=[
#                         {"role": "system", "content": system_prompt},
#                         {"role": "user",   "content": user_prompt},
#                     ],
#                     temperature=0.1,
#                     max_tokens=1500,
#                 )

#                 text   = response.choices[0].message.content
#                 report = self._parse_json(text)

#                 if not report:
#                     logger.warning(f"Report parse failed attempt {attempt+1}, raw: {text[:200]}")
#                     continue

#                 report["citations"]              = citations
#                 report["policy_relevance"]       = policy_cards
#                 report["policy_relevance_chart"] = report.get("policy_relevance_chart") or \
#                                                    FALLBACK_REPORT["policy_relevance_chart"]

#                 return self._ensure_schema(report)

#             except Exception as e:
#                 logger.error(f"Report generation error (attempt {attempt+1}): {e}")

#         logger.error("Report generation failed after 3 attempts")
#         fallback = dict(FALLBACK_REPORT)
#         fallback["citations"]        = citations
#         fallback["policy_relevance"] = policy_cards
#         return fallback

#     # ------------------------------------------------------------------

#     def _build_context_block(self, contexts: List[Dict]) -> str:
#         lines = []
#         for i, ctx in enumerate(contexts, 1):
#             summary = ctx.get("law_summary") or ctx.get("chunk_text", "")[:300]
#             doc_name = ctx.get("document_name") or ctx.get("source_section") or "Unknown"
#             lines.append(
#                 f"[{i}] {summary}\n"
#                 f"    Document: {doc_name} | "
#                 f"{ctx.get('country','?')} | "
#                 f"Score: {ctx.get('relevance_score', 0):.2f}"
#             )
#         return "\n\n".join(lines)

#     def _build_citations(self, contexts: List[Dict]) -> List[Dict]:
#         seen, citations = set(), []
#         for ctx in contexts:
#             doc_id = ctx.get("source_document") or ctx.get("document_id", "")
#             if doc_id and doc_id not in seen:
#                 seen.add(doc_id)
#                 citations.append({
#                     "document_id":     doc_id,
#                     "document_name":   ctx.get("document_name", ctx.get("source_section", "Unknown")),
#                     "section":         ctx.get("source_section", "Unknown"),
#                     "country":         ctx.get("country", "Unknown"),
#                     "publish_date":    ctx.get("publish_date", "Unknown"),
#                     "relevance_score": round(ctx.get("relevance_score", 0), 3),
#                     "summary":         ctx.get("law_summary", ""),
#                 })
#         return citations

#     def _build_policy_cards(self, contexts: List[Dict]) -> List[Dict]:
#         """
#         Build ALL policy cards — one per unique document_id.
#         Uses LLM-inferred document_name from judge.py.
#         Fields match frontend exactly: document_id, policy_name, country, relevance_score
#         """
#         seen, cards = set(), []
#         for ctx in contexts:
#             doc_id = ctx.get("source_document") or ctx.get("document_id", "")
#             if not doc_id or doc_id in seen:
#                 continue
#             seen.add(doc_id)

#             # Use LLM-inferred document name (set by judge), fall back gracefully
#             policy_name = (
#                 ctx.get("document_name")
#                 or ctx.get("source_section")
#                 or ctx.get("section_title")
#                 or doc_id
#             )

#             cards.append({
#                 "document_id":     doc_id,
#                 "policy_name":     policy_name,
#                 "country":         ctx.get("country", "Unknown"),
#                 "relevance_score": round(ctx.get("relevance_score", 0), 3),
#                 "summary":         ctx.get("law_summary", ""),
#             })

#         # Sort by relevance so most relevant appear first
#         cards.sort(key=lambda x: x["relevance_score"], reverse=True)
#         return cards

#     def _ensure_schema(self, report: Dict) -> Dict:
#         report.setdefault("validity_score",    50)
#         report.setdefault("risk_level",        "Unknown")
#         report.setdefault("executive_summary", "Analysis complete.")
#         report.setdefault("pros",              [])
#         report.setdefault("cons",              [])
#         report.setdefault("recommendations",   [])
#         report.setdefault("citations",         [])
#         report.setdefault("policy_relevance",  [])

#         cs = report.get("compliance_scores", {})
#         if not isinstance(cs, dict):
#             cs = {}
#         for key in ["data_privacy", "financial_regulation", "ai_regulation", "consumer_protection"]:
#             cs.setdefault(key, 50)
#         report["compliance_scores"] = cs

#         prc = report.get("policy_relevance_chart")
#         if not isinstance(prc, list) or not prc:
#             report["policy_relevance_chart"] = FALLBACK_REPORT["policy_relevance_chart"]

#         return report

#     def _parse_json(self, text: str) -> dict:
#         try:
#             match = re.search(r"\{.*\}", text.strip(), re.DOTALL)
#             if not match:
#                 logger.error(f"No JSON in report response: {text[:200]}")
#                 return {}
#             return json.loads(match.group())
#         except Exception as e:
#             logger.error(f"Report JSON parse error: {e} | raw: {text[:200]}")
#             return {}

import logging
import json
import re
from typing import List, Dict
from groq import Groq

logger = logging.getLogger(__name__)

FALLBACK_REPORT = {
    "executive_summary": (
        "No relevant legal context was found for this product and region. "
        "Consider consulting a qualified legal professional."
    ),
    "validity_score": 50,
    "risk_level": "Unknown",
    "compliance_scores": {
        "data_privacy": 50,
        "financial_regulation": 50,
        "ai_regulation": 50,
        "consumer_protection": 50,
    },
    "policy_relevance_chart": [
        {"label": "Data Privacy",         "value": 25},
        {"label": "Financial Regulation", "value": 25},
        {"label": "AI Regulation",        "value": 25},
        {"label": "Consumer Law",         "value": 25},
    ],
    "policy_relevance": [],
    "pros": [],
    "cons": ["Insufficient legal context to perform analysis"],
    "recommendations": ["Consult a qualified legal professional for this jurisdiction"],
    "citations": [],
}


class ReportGenerator:

    def __init__(self, groq_client: Groq, model: str):
        self.client = groq_client
        self.model  = model

    def generate(
        self,
        product_description: str,
        country: str,
        domain: str,
        contexts: List[Dict],
    ) -> Dict:

        if not contexts:
            logger.warning("No contexts — returning fallback report")
            return FALLBACK_REPORT

        context_block = self._build_context_block(contexts)
        citations     = self._build_citations(contexts)

        # Build ALL policy cards — one per unique document
        policy_cards  = self._build_policy_cards(contexts)

        system_prompt = (
            "You are a legal analysis API. "
            "You ONLY output raw JSON. "
            "No markdown, no code fences, no explanation, no preamble. "
            "Your entire response must be a single valid JSON object and nothing else."
        )

        user_prompt = f"""You are a senior legal analyst generating a comprehensive feasibility report.

CRITICAL: You MUST calculate actual dynamic scores based on the specific product and legal context. DO NOT use placeholder values or return the same scores for different products. Each analysis must be unique and context-specific.

SCORING INSTRUCTIONS:
- validity_score: Calculate based on overall legal feasibility (0-100). Consider regulatory complexity, compliance costs, market readiness.
- compliance_scores: Calculate each category individually based on relevant laws (0-100). Higher scores mean better compliance.
- policy_relevance_chart: Calculate percentages based on which regulatory areas are most relevant to this specific product. Values must sum to 100.
- risk_level: Determine as "Low", "Medium", or "High" based on potential legal penalties, compliance complexity, and regulatory uncertainty.

EXAMPLE: A fintech product in US might have: financial_regulation: 85, data_privacy: 70, consumer_protection: 75, ai_regulation: 40.

Based on the following product description and legal documents, provide a detailed analysis.

PRODUCT: {product_description[:500]}
COUNTRY: {country}
DOMAIN: {domain}

RETRIEVED LEGAL DOCUMENTS:
{context_block}

Output ONLY this JSON. For recommendations: each must be a specific, technical, legally actionable step — 
cite actual law names, specific articles/sections, precise compliance actions required (e.g. 
"Appoint a Data Protection Officer under GDPR Art. 37(1)(b) given cross-border processing of health data",
"Register as a Money Services Business with FinCEN under 31 U.S.C. § 5330 before launch",
"Conduct a HIPAA Security Risk Analysis under 45 CFR § 164.308(a)(1) covering all ePHI touch points").
Be specific to the exact laws retrieved. No generic advice.

{{
  "executive_summary": "3-4 sentence precise legal overview citing specific laws and their implications",
  "validity_score": ACTUALLY_CALCULATE_A_NUMBER_0_TO_100_BASED_ON_PRODUCT_FEASIBILITY,
  "risk_level": ACTUALLY_DETERMINE_AS_EITHER_"Low"_OR_"Medium"_OR_"High"_BASED_ON_ANALYSIS,
  "compliance_scores": {{
    "data_privacy": ACTUALLY_CALCULATE_A_NUMBER_0_TO_100_FOR_DATA_PRIVACY_COMPLIANCE,
    "financial_regulation": ACTUALLY_CALCULATE_A_NUMBER_0_TO_100_FOR_FINANCIAL_REGULATION_COMPLIANCE,
    "ai_regulation": ACTUALLY_CALCULATE_A_NUMBER_0_TO_100_FOR_AI_REGULATION_COMPLIANCE,
    "consumer_protection": ACTUALLY_CALCULATE_A_NUMBER_0_TO_100_FOR_CONSUMER_PROTECTION_COMPLIANCE
  }},
  "policy_relevance_chart": [
    {{"label": "Data Privacy", "value": ACTUALLY_CALCULATE_PERCENTAGE_0_TO_100}},
    {{"label": "Financial Regulation", "value": ACTUALLY_CALCULATE_PERCENTAGE_0_TO_100}},
    {{"label": "AI Regulation", "value": ACTUALLY_CALCULATE_PERCENTAGE_0_TO_100}},
    {{"label": "Consumer Law", "value": ACTUALLY_CALCULATE_PERCENTAGE_0_TO_100}}
  ],
  "pros": ["advantage 1 citing law", "advantage 2", "advantage 3", "advantage 4", "advantage 5"],
  "cons": ["risk 1 citing law and penalty", "risk 2", "risk 3", "risk 4", "risk 5"],
  "recommendations": [
    "STEP 1 — [Specific Action]: [Exact legal requirement] under [Law Name] [Section]. [How to comply]. Deadline: [if applicable].",
    "STEP 2 — [Specific Action]: ..."
  ]
}}

policy_relevance_chart values must sum to 100. Generate 5-7 detailed recommendations. You MUST return exactly 5 pros and exactly 5 cons. Each must cite a specific law name and section number."""

        for attempt in range(3):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user",   "content": user_prompt},
                    ],
                    temperature=0.1,
                    max_tokens=1500,
                )

                text   = response.choices[0].message.content
                report = self._parse_json(text)

                if not report:
                    logger.warning(f"Report parse failed attempt {attempt+1}, raw: {text[:200]}")
                    continue

                report["citations"]              = citations
                report["policy_relevance"]       = policy_cards
                report["policy_relevance_chart"] = report.get("policy_relevance_chart") or \
                                                   FALLBACK_REPORT["policy_relevance_chart"]

                return self._ensure_schema(report)

            except Exception as e:
                logger.error(f"Report generation error (attempt {attempt+1}): {e}")

        logger.error("Report generation failed after 3 attempts")
        fallback = dict(FALLBACK_REPORT)
        fallback["citations"]        = citations
        fallback["policy_relevance"] = policy_cards
        return fallback

    # ------------------------------------------------------------------

    def _build_context_block(self, contexts: List[Dict]) -> str:
        lines = []
        for i, ctx in enumerate(contexts, 1):
            summary = ctx.get("law_summary") or ctx.get("chunk_text", "")[:300]
            doc_name = ctx.get("document_name") or ctx.get("source_section") or "Unknown"
            lines.append(
                f"[{i}] {summary}\n"
                f"    Document: {doc_name} | "
                f"{ctx.get('country','?')} | "
                f"Score: {ctx.get('relevance_score', 0):.2f}"
            )
        return "\n\n".join(lines)

    def _build_citations(self, contexts: List[Dict]) -> List[Dict]:
        seen, citations = set(), []
        for ctx in contexts:
            doc_id = ctx.get("source_document") or ctx.get("document_id", "")
            if doc_id and doc_id not in seen:
                seen.add(doc_id)
                citations.append({
                    "document_id":     doc_id,
                    "document_name":   ctx.get("document_name", ctx.get("source_section", "Unknown")),
                    "section":         ctx.get("source_section", "Unknown"),
                    "country":         ctx.get("country", "Unknown"),
                    "publish_date":    ctx.get("publish_date", "Unknown"),
                    "relevance_score": round(ctx.get("relevance_score", 0), 3),
                    "summary":         ctx.get("law_summary", ""),
                })
        return citations

    def _build_policy_cards(self, contexts: List[Dict]) -> List[Dict]:
        """
        Build ALL policy cards — one per unique document_id.
        Uses LLM-inferred document_name from judge.py.
        Fields match frontend exactly: document_id, policy_name, country, relevance_score
        """
        seen, cards = set(), []
        for ctx in contexts:
            doc_id = ctx.get("source_document") or ctx.get("document_id", "")
            if not doc_id or doc_id in seen:
                continue
            seen.add(doc_id)

            # Use LLM-inferred document name (set by judge), fall back gracefully
            policy_name = (
                ctx.get("document_name")
                or ctx.get("source_section")
                or ctx.get("section_title")
                or doc_id
            )

            cards.append({
                "document_id":     doc_id,
                "policy_name":     policy_name,
                "country":         ctx.get("country", "Unknown"),
                "relevance_score": round(ctx.get("relevance_score", 0), 3),
                "summary":         ctx.get("law_summary", ""),
            })

        # Sort by relevance so most relevant appear first
        cards.sort(key=lambda x: x["relevance_score"], reverse=True)
        return cards

    def _ensure_schema(self, report: Dict) -> Dict:
        report.setdefault("validity_score",    50)
        report.setdefault("risk_level",        "Unknown")
        report.setdefault("executive_summary", "Analysis complete.")
        report.setdefault("pros",              [])
        report.setdefault("cons",              [])
        report.setdefault("recommendations",   [])
        report.setdefault("citations",         [])
        report.setdefault("policy_relevance",  [])

        cs = report.get("compliance_scores", {})
        if not isinstance(cs, dict):
            cs = {}
        for key in ["data_privacy", "financial_regulation", "ai_regulation", "consumer_protection"]:
            cs.setdefault(key, 50)
        report["compliance_scores"] = cs

        prc = report.get("policy_relevance_chart")
        if not isinstance(prc, list) or not prc:
            report["policy_relevance_chart"] = FALLBACK_REPORT["policy_relevance_chart"]

        return report

    def _parse_json(self, text: str) -> dict:
        try:
            match = re.search(r"\{.*\}", text.strip(), re.DOTALL)
            if not match:
                logger.error(f"No JSON in report response: {text[:200]}")
                return {}
            return json.loads(match.group())
        except Exception as e:
            logger.error(f"Report JSON parse error: {e} | raw: {text[:200]}")
            return {}