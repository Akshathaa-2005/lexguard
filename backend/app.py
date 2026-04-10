# import os
# import io
# import time
# import logging
# from datetime import datetime
# from functools import wraps

# from flask import Flask, request, jsonify, send_file
# from flask_cors import CORS
# from dotenv import load_dotenv

# load_dotenv()

# from pymongo import MongoClient
# from pymongo.errors import ConnectionFailure
# import certifi
# import os

# from pipeline import LegalRAGPipeline
# from file_parser import extract_text


# # -----------------------------
# # Logging
# # -----------------------------
# logging.basicConfig(
#     level=logging.INFO,
#     format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
# )
# logger = logging.getLogger("legal-rag-api")


# # -----------------------------
# # Flask App
# # -----------------------------
# app = Flask(__name__)
# CORS(app)


# # -----------------------------
# # MongoDB (policy document store)
# # -----------------------------
# mongo_db = None



# def init_mongo():
#     uri = os.getenv("MONGO_URI")

#     client = MongoClient(
#         uri,
#         tls=True,
#         tlsCAFile=certifi.where(),
#         serverSelectionTimeoutMS=5000
#     )

#     client.admin.command("ping")
#     print("MongoDB connected successfully")

#     return client


# # -----------------------------
# # RAG Pipeline (lazy)
# # -----------------------------
# _pipeline = None

# def get_pipeline() -> LegalRAGPipeline:
#     global _pipeline
#     if _pipeline is None:
#         logger.info("Initializing RAG Pipeline...")
#         _pipeline = LegalRAGPipeline()
#     return _pipeline


# # -----------------------------
# # Retry on rate limit
# # -----------------------------
# def retry_on_rate_limit(max_retries=3, backoff=2):
#     def decorator(func):
#         @wraps(func)
#         def wrapper(*args, **kwargs):
#             for attempt in range(max_retries):
#                 try:
#                     return func(*args, **kwargs)
#                 except Exception as e:
#                     if "rate limit" in str(e).lower() and attempt < max_retries - 1:
#                         wait = backoff ** attempt
#                         logger.warning(f"Rate limit hit. Retrying in {wait}s")
#                         time.sleep(wait)
#                     else:
#                         raise
#         return wrapper
#     return decorator


# # -----------------------------
# # Helpers
# # -----------------------------
# def parse_json_body(*required_fields):
#     data = request.get_json()
#     if not data:
#         return None, "Invalid or missing JSON body"
#     for field in required_fields:
#         if not data.get(field):
#             return None, f"'{field}' is required"
#     return data, None


# # -----------------------------
# # Health
# # -----------------------------
# @app.route("/health", methods=["GET"])
# def health():
#     return jsonify({
#         "status": "healthy",
#         "timestamp": datetime.utcnow().isoformat(),
#     })


# # -----------------------------
# # POST /analyze
# # -----------------------------
# @app.route("/analyze", methods=["POST"])
# @retry_on_rate_limit()
# def analyze():
#     try:
#         data, err = parse_json_body("product_description")
#         if err:
#             return jsonify({"error": err}), 400

#         product_description = data["product_description"]
#         country             = data.get("country", "")
#         domain              = data.get("domain", "")

#         pipeline = get_pipeline()
#         report   = pipeline.generate_report(product_description, country, domain)

#         return jsonify(report)

#     except Exception as e:
#         logger.error(f"/analyze failed: {e}")
#         return jsonify({"error": "Analysis failed", "details": str(e)}), 500


# # -----------------------------
# # POST /upload
# # -----------------------------
# @app.route("/upload", methods=["POST"])
# def upload():
#     try:
#         if "file" not in request.files:
#             return jsonify({"error": "No file provided"}), 400

#         file = request.files["file"]

#         if not file.filename:
#             return jsonify({"error": "Empty filename"}), 400

#         if not (file.filename.endswith(".pdf") or file.filename.endswith(".docx")):
#             return jsonify({"error": "Only PDF and DOCX files are supported"}), 400

#         text = extract_text(file)

#         return jsonify({
#             "filename":       file.filename,
#             "text_length":    len(text),
#             "extracted_text": text,
#         })

#     except Exception as e:
#         logger.error(f"/upload failed: {e}")
#         return jsonify({"error": "File processing failed", "details": str(e)}), 500


# # -----------------------------
# # GET /policy/<document_id>
# # -----------------------------
# @app.route("/policy/<document_id>", methods=["GET"])
# def get_policy(document_id):
#     try:
#         if mongo_db is None:
#             return jsonify({"error": "Document store unavailable"}), 503

#         collection = mongo_db["docs"]

#         # Try document_id field first, then fall back to _id as ObjectId
#         doc = collection.find_one({"document_id": document_id})

#         if not doc:
#             from bson import ObjectId
#             from bson.errors import InvalidId
#             try:
#                 doc = collection.find_one({"_id": ObjectId(document_id)})
#             except InvalidId:
#                 pass

#         if not doc:
#             # Last resort: try _id as plain string
#             doc = collection.find_one({"_id": document_id})

#         if not doc:
#             logger.warning(f"Policy not found for id: {document_id}")
#             return jsonify({"error": f"Policy not found: {document_id}"}), 404

#         full_text = doc.get("text", "") or doc.get("content", "") or doc.get("body", "")

#         if not full_text:
#             # Dump all string fields as fallback
#             full_text = "\n\n".join(
#                 f"{k}:\n{v}" for k, v in doc.items()
#                 if isinstance(v, str) and k != "_id"
#             )

#         policy_name = next(
#             (line.strip() for line in full_text.split("\n") if line.strip()),
#             document_id,
#         )

#         buffer = io.BytesIO(full_text.encode("utf-8"))
#         buffer.seek(0)

#         return send_file(
#             buffer,
#             as_attachment=True,
#             download_name=f"{policy_name[:60].replace(' ', '_')}.txt",
#             mimetype="text/plain",
#         )

#     except Exception as e:
#         logger.error(f"/policy retrieval failed: {e}")
#         return jsonify({"error": "Policy retrieval failed"}), 500


# # -----------------------------
# # Error handlers
# # -----------------------------
# @app.errorhandler(429)
# def rate_limit_handler(e):
#     return jsonify({"error": "Rate limit exceeded"}), 429

# @app.errorhandler(404)
# def not_found(e):
#     return jsonify({"error": "Endpoint not found"}), 404


# # -----------------------------
# # Start
# # -----------------------------
# if __name__ == "__main__":
#     init_mongo()
#     logger.info("Starting Legal RAG API on :5000")
#     app.run(host="0.0.0.0", port=5000, debug=True)

import os
import io
import time
import logging
from datetime import datetime
from functools import wraps

from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from dotenv import load_dotenv

load_dotenv()

from pymongo import MongoClient
from pymongo.errors import ConnectionFailure

from pipeline import LegalRAGPipeline
from file_parser import extract_text
from groq import Groq


# -----------------------------
# Logging
# -----------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("legal-rag-api")


# -----------------------------
# Flask App
# -----------------------------
app = Flask(__name__)
CORS(app)


# -----------------------------
# MongoDB (policy document store)
# -----------------------------
mongo_db = None

def init_mongo():
    global mongo_db
    try:
        client = MongoClient(
            os.getenv("MONGO_URI"),
            serverSelectionTimeoutMS=5000,
        )
        client.admin.command("ping")
        mongo_db = client[os.getenv("MONGO_DB", "legal_documents")]
        logger.info("MongoDB connected")
    except ConnectionFailure as e:
        logger.error(f"MongoDB connection failed: {e}")
        raise


# -----------------------------
# RAG Pipeline (lazy)
# -----------------------------
_pipeline = None

def get_pipeline() -> LegalRAGPipeline:
    global _pipeline
    if _pipeline is None:
        logger.info("Initializing RAG Pipeline...")
        _pipeline = LegalRAGPipeline()
    return _pipeline


# -----------------------------
# Retry on rate limit
# -----------------------------
def retry_on_rate_limit(max_retries=3, backoff=2):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if "rate limit" in str(e).lower() and attempt < max_retries - 1:
                        wait = backoff ** attempt
                        logger.warning(f"Rate limit hit. Retrying in {wait}s")
                        time.sleep(wait)
                    else:
                        raise
        return wrapper
    return decorator


# -----------------------------
# Helpers
# -----------------------------
def parse_json_body(*required_fields):
    data = request.get_json()
    if not data:
        return None, "Invalid or missing JSON body"
    for field in required_fields:
        if not data.get(field):
            return None, f"'{field}' is required"
    return data, None


# -----------------------------
# Health
# -----------------------------
@app.route("/health", methods=["GET"])
def health():
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
    })


# -----------------------------
# POST /analyze
# -----------------------------
@app.route("/analyze", methods=["POST"])
@retry_on_rate_limit()
def analyze():
    try:
        data, err = parse_json_body("product_description")
        if err:
            return jsonify({"error": err}), 400

        product_description = data["product_description"]
        country             = data.get("country", "")
        domain              = data.get("domain", "")

        pipeline = get_pipeline()
        report   = pipeline.generate_report(product_description, country, domain)

        return jsonify(report)

    except Exception as e:
        logger.error(f"/analyze failed: {e}")
        return jsonify({"error": "Analysis failed", "details": str(e)}), 500


# -----------------------------
# POST /upload
# -----------------------------
@app.route("/upload", methods=["POST"])
def upload():
    try:
        if "file" not in request.files:
            return jsonify({"error": "No file provided"}), 400

        file = request.files["file"]

        if not file.filename:
            return jsonify({"error": "Empty filename"}), 400

        if not (file.filename.endswith(".pdf") or file.filename.endswith(".docx")):
            return jsonify({"error": "Only PDF and DOCX files are supported"}), 400

        text = extract_text(file)

        return jsonify({
            "filename":       file.filename,
            "text_length":    len(text),
            "extracted_text": text,
        })

    except Exception as e:
        logger.error(f"/upload failed: {e}")
        return jsonify({"error": "File processing failed", "details": str(e)}), 500


# -----------------------------
# GET /policy/<document_id>
# -----------------------------
@app.route("/policy/<document_id>", methods=["GET"])
def get_policy(document_id):
    try:
        if mongo_db is None:
            return jsonify({"error": "Document store unavailable"}), 503

        collection = mongo_db["docs"]

        # Try document_id field first, then fall back to _id as ObjectId
        doc = collection.find_one({"document_id": document_id})

        if not doc:
            from bson import ObjectId
            from bson.errors import InvalidId
            try:
                doc = collection.find_one({"_id": ObjectId(document_id)})
            except InvalidId:
                pass

        if not doc:
            # Last resort: try _id as plain string
            doc = collection.find_one({"_id": document_id})

        if not doc:
            logger.warning(f"Policy not found for id: {document_id}")
            return jsonify({"error": f"Policy not found: {document_id}"}), 404

        full_text = doc.get("text", "") or doc.get("content", "") or doc.get("body", "")

        if not full_text:
            # Dump all string fields as fallback
            full_text = "\n\n".join(
                f"{k}:\n{v}" for k, v in doc.items()
                if isinstance(v, str) and k != "_id"
            )

        policy_name = next(
            (line.strip() for line in full_text.split("\n") if line.strip()),
            document_id,
        )

        buffer = io.BytesIO(full_text.encode("utf-8"))
        buffer.seek(0)

        return send_file(
            buffer,
            as_attachment=True,
            download_name=f"{policy_name[:60].replace(' ', '_')}.txt",
            mimetype="text/plain",
        )

    except Exception as e:
        logger.error(f"/policy retrieval failed: {e}")
        return jsonify({"error": "Policy retrieval failed"}), 500


# -----------------------------
# GET /policies — browse all policies by country/domain
# -----------------------------
@app.route("/policies", methods=["GET"])
def browse_policies():
    try:
        country = request.args.get("country", "").strip()
        domain  = request.args.get("domain",  "").strip()

        if not country and not domain:
            return jsonify({"error": "Provide at least country or domain"}), 400

        pipeline   = get_pipeline()
        pg_cursor  = pipeline.db.cursor

        if not pg_cursor:
            return jsonify({"error": "Database unavailable"}), 503

        if country and domain:
            sql_docs = """
                SELECT DISTINCT d.document_id, d.country, d.publish_date
                FROM legal_documents d
                JOIN legal_chunks c ON d.document_id = c.document_id
                WHERE LOWER(d.country) = LOWER(%s)
                AND LOWER(c.chunk_text) LIKE LOWER(%s)
                ORDER BY d.document_id
            """
            pg_cursor.execute(sql_docs, (country, f"%{domain}%"))
        elif country:
            sql_docs = """
                SELECT DISTINCT document_id, country, publish_date
                FROM legal_documents
                WHERE LOWER(country) = LOWER(%s)
                ORDER BY document_id
            """
            pg_cursor.execute(sql_docs, (country,))
        elif domain:
            sql_docs = """
                SELECT DISTINCT d.document_id, d.country, d.publish_date
                FROM legal_documents d
                JOIN legal_chunks c ON d.document_id = c.document_id
                WHERE LOWER(c.chunk_text) LIKE LOWER(%s)
                ORDER BY d.document_id
            """
            pg_cursor.execute(sql_docs, (f"%{domain}%",))
        else:
            sql_docs = """
                SELECT DISTINCT document_id, country, publish_date
                FROM legal_documents
                ORDER BY document_id
            """
            pg_cursor.execute(sql_docs)

        doc_rows = pg_cursor.fetchall()

        docs = {}
        for doc_id, doc_country, publish_date in doc_rows:
            docs[doc_id] = {
                "document_id": doc_id,
                "country": doc_country or "Unknown",
                "publish_date": str(publish_date) if publish_date else "Unknown",
                "sections": [],
            }

        if docs:
            placeholders = ','.join(['%s'] * len(docs))
            sql_sections = f"""
                SELECT document_id, section_title
                FROM legal_sections
                WHERE document_id IN ({placeholders})
                ORDER BY document_id
            """
            pg_cursor.execute(sql_sections, list(docs.keys()))
            for doc_id, section_title in pg_cursor.fetchall():
                if doc_id in docs and section_title and section_title not in docs[doc_id]["sections"]:
                    docs[doc_id]["sections"].append(section_title)

        result = list(docs.values())

        # Use LLM to infer document names for all docs
        result = _infer_document_names(result)

        return jsonify({"documents": result, "total": len(result)})

    except Exception as e:
        logger.error(f"/policies browse failed: {e}")
        try:
            pipeline.db.conn.rollback()
        except Exception:
            pass
        return jsonify({"error": "Failed to browse policies", "details": str(e)}), 500


def _infer_document_names(docs: list) -> list:
    """Use LLM to infer a human-readable document name from section titles."""
    groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    model       = os.getenv("GROQ_JUDGE_MODEL", "llama-3.1-8b-instant")

    import time, json, re

    for doc in docs:
        sections_preview = ", ".join(doc["sections"][:5]) if doc["sections"] else "Unknown"
        prompt = (
            f"A legal document from {doc['country']} contains these sections: {sections_preview}.\n"
            f"What is the most likely full official name of this law or regulation?\n"
            f'Reply JSON only: {{"document_name": "Full Official Law Name"}}'
        )
        try:
            response = groq_client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=60,
            )
            text  = response.choices[0].message.content.strip()
            match = re.search(r"\{.*\}", text, re.DOTALL)
            if match:
                parsed = json.loads(match.group())
                doc["document_name"] = parsed.get("document_name", doc["document_id"])
            else:
                doc["document_name"] = sections_preview or doc["document_id"]
            time.sleep(0.5)
        except Exception as e:
            logger.warning(f"Name inference failed for {doc['document_id']}: {e}")
            doc["document_name"] = sections_preview or doc["document_id"]

    return docs


# -----------------------------
# POST /chat — lawyer chat interface
# -----------------------------
@app.route("/chat", methods=["POST"])
def lawyer_chat():
    try:
        data, err = parse_json_body("message", "context")
        if err:
            return jsonify({"error": err}), 400

        user_message      = data["message"]
        context           = data["context"]        # full report + retrieved contexts
        history           = data.get("history", [])  # [{role, content}, ...]
        product_description = data.get("product_description", "")

        groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        model       = os.getenv("GROQ_KIWI_MODEL", "llama-3.3-70b-versatile")

        # Build lawyer system prompt with all context
        legal_contexts_text = ""
        if isinstance(context.get("citations"), list):
            for c in context["citations"]:
                legal_contexts_text += (
                    f"- {c.get('document_name', c.get('section', 'Unknown'))} "
                    f"({c.get('country', '?')}, {c.get('publish_date', '?')}): "
                    f"{c.get('summary', '')}\n"
                )

        recommendations_text = ""
        if isinstance(context.get("recommendations"), list):
            recommendations_text = "\n".join(
                f"{i+1}. {r}" for i, r in enumerate(context["recommendations"])
            )

        system_prompt = f"""You are a senior partner at a top-tier international law firm specializing in technology, AI, fintech, healthcare, and data privacy regulation.

You are advising a startup founder on the legal feasibility of their product.

PRODUCT UNDER REVIEW:
{product_description}

RETRIEVED LEGAL DOCUMENTS (your knowledge base for this session):
{legal_contexts_text or "General legal knowledge applies."}

CURRENT LEGAL ANALYSIS:
- Validity Score: {context.get("validity_score", "N/A")}/100
- Risk Level: {context.get("risk_level", "Unknown")}
- Executive Summary: {context.get("executive_summary", "")}

CURRENT RECOMMENDATIONS ON FILE:
{recommendations_text or "None yet."}

INSTRUCTIONS:
- Answer as a practicing lawyer with deep expertise in the specific laws retrieved above
- Cite specific law names, article numbers, sections, and regulatory bodies when answering
- Be direct, technically precise, and actionable — not generic
- If asked about a specific law or requirement, explain what it means practically for THIS product
- Flag any additional risks the founder should know about
- Do not give disclaimers like "consult a lawyer" — you ARE the lawyer in this session
- Keep responses focused and practical, 2-4 paragraphs unless a detailed breakdown is asked for"""

        # Build conversation messages
        messages = [{"role": "system", "content": system_prompt}]

        # Add conversation history (last 10 turns to stay within context)
        for turn in history[-10:]:
            if turn.get("role") in ("user", "assistant") and turn.get("content"):
                messages.append({"role": turn["role"], "content": turn["content"]})

        # Add current message
        messages.append({"role": "user", "content": user_message})

        response = groq_client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=0.3,
            max_tokens=1000,
        )

        reply = response.choices[0].message.content

        return jsonify({"reply": reply})

    except Exception as e:
        logger.error(f"/chat failed: {e}")
        return jsonify({"error": "Chat failed", "details": str(e)}), 500


# -----------------------------
# Error handlers
# -----------------------------
@app.errorhandler(429)
def rate_limit_handler(e):
    return jsonify({"error": "Rate limit exceeded"}), 429

@app.errorhandler(404)
def not_found(e):
    return jsonify({"error": "Endpoint not found"}), 404


# -----------------------------
# Start
# -----------------------------
if __name__ == "__main__":
    init_mongo()
    logger.info("Starting Legal RAG API on :5000")
    app.run(host="0.0.0.0", port=5000, debug=True)