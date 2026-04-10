import os
import logging
from typing import Dict
from dotenv import load_dotenv
from groq import Groq

load_dotenv()

from embeddings import EmbeddingModel
from db import Database
from retriever import Retriever
from judge import LLMJudge
from report_generator import ReportGenerator

logger = logging.getLogger(__name__)


class LegalRAGPipeline:
    """
    Orchestrates the full RAG pipeline:

    Stage 1  — Query Embedding        (embeddings.py)
    Stage 2  — Vector Retrieval       (db.py)
    Stage 3  — Context Assembly       (retriever.py)
    Stage 4  — LLM-as-Judge Filtering (judge.py)   50 → 20 → 10 → 5
    Stage 5  — Report Generation      (report_generator.py)
    """

    def __init__(self):

        logger.info("Initializing Legal RAG Pipeline...")

        # Shared Groq client
        groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))

        judge_model    = os.getenv("GROQ_JUDGE_MODEL",  "llama-3.1-8b-instant")
        analysis_model = os.getenv("GROQ_KIWI_MODEL",   "llama-3.3-70b-versatile")

        # Instantiate modules
        self.embedder   = EmbeddingModel()
        self.db         = Database()
        self.retriever  = Retriever(self.db, self.embedder)
        self.judge      = LLMJudge(groq_client, judge_model)
        self.reporter   = ReportGenerator(groq_client, analysis_model)

        logger.info("RAG Pipeline initialized")

    # ------------------------------------------------------------------
    # Main entry point called by app.py
    # ------------------------------------------------------------------

    def generate_report(
        self,
        product_description: str,
        country: str,
        domain: str,
    ) -> Dict:

        # Stage 1-3: embed + retrieve + assemble (limit=50 per spec)
        contexts = self.retriever.retrieve(
            query=product_description,
            country=country,
            limit=50,
        )

        # Stage 4: 3-pass LLM-as-Judge filtering  50 → 20 → 10 → 5
        filtered = self.judge.filter(
            chunks=contexts,
            product_description=product_description,
            domain=domain,
        )

        # Stage 5: structured report generation
        report = self.reporter.generate(
            product_description=product_description,
            country=country,
            domain=domain,
            contexts=filtered,
        )

        return report

    # ------------------------------------------------------------------
    # Graceful shutdown
    # ------------------------------------------------------------------

    def close(self):
        self.db.close()
