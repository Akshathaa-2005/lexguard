import os
import logging
import psycopg2
import numpy as np
from typing import List, Dict

logger = logging.getLogger(__name__)


class Database:

    def __init__(self):

        try:
            self.conn = psycopg2.connect(
                host=os.getenv("SUPABASE_HOST"),
                database=os.getenv("SUPABASE_DB"),
                user=os.getenv("SUPABASE_USER"),
                password=os.getenv("SUPABASE_PASSWORD"),
                port=os.getenv("SUPABASE_PORT"),
            )
            self.cursor = self.conn.cursor()
            logger.info("PostgreSQL connection established")

        except Exception as e:
            logger.error(f"PostgreSQL connection failed: {e}")
            self.conn = None
            self.cursor = None

    def is_connected(self) -> bool:
        return self.cursor is not None

    def vector_search(
        self,
        query_embedding: np.ndarray,
        country: str = "",
        limit: int = 50,
    ) -> List[Dict]:
        """
        Retrieve top-N chunks by cosine similarity, enriched with
        section_title, country, and publish_date per spec.
        Falls back to no country filter if zero results returned.
        """
        if not self.is_connected():
            logger.error("PostgreSQL unavailable")
            return []

        vector = [float(x) for x in query_embedding]

        results = self._run_search(vector, country, limit)

        # Fallback: retry without country filter if no results
        if not results and country:
            logger.warning(
                f"No chunks for country='{country}', retrying without filter"
            )
            results = self._run_search(vector, "", limit)

        return results

    def _run_search(
        self, vector: list, country: str, limit: int
    ) -> List[Dict]:

        try:
            if country:
                sql = """
                    SELECT
                        c.chunk_text,
                        c.document_id,
                        c.section_id,
                        s.section_title,
                        d.country,
                        d.publish_date,
                        c.vector <=> %s::vector AS distance
                    FROM legal_chunks c
                    LEFT JOIN legal_sections s
                        ON c.section_id = s.section_id
                    JOIN legal_documents d
                        ON c.document_id = d.document_id
                    WHERE d.country = %s
                    ORDER BY c.vector <=> %s::vector
                    LIMIT %s
                """
                self.cursor.execute(sql, (vector, country, vector, limit))

            else:
                sql = """
                    SELECT
                        c.chunk_text,
                        c.document_id,
                        c.section_id,
                        s.section_title,
                        d.country,
                        d.publish_date,
                        c.vector <=> %s::vector AS distance
                    FROM legal_chunks c
                    LEFT JOIN legal_sections s
                        ON c.section_id = s.section_id
                    LEFT JOIN legal_documents d
                        ON c.document_id = d.document_id
                    ORDER BY c.vector <=> %s::vector
                    LIMIT %s
                """
                self.cursor.execute(sql, (vector, vector, limit))

            rows = self.cursor.fetchall()

        except Exception as e:
            logger.error(f"Vector search query failed: {e}")
            # Reconnect cursor on error
            try:
                self.conn.rollback()
            except Exception:
                pass
            return []

        results = []
        for row in rows:
            chunk_text, doc_id, section_id, section_title, country_val, publish_date, distance = row
            results.append({
                "chunk_text": chunk_text,
                "document_id": doc_id,
                "section_id": section_id,
                "section_title": section_title or "Unknown Section",
                "country": country_val or "Unknown",
                "publish_date": str(publish_date) if publish_date else "Unknown",
                "similarity_score": max(0.0, 1.0 - distance),
            })

        return results

    def close(self):
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()
