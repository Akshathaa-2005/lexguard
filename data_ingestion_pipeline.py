import os
import re
import uuid
import torch
import pdfplumber
import docx
import logging

from tqdm import tqdm
from pymongo import MongoClient
from dotenv import load_dotenv
from datetime import datetime
import psycopg2
from psycopg2.extras import execute_batch
from transformers import AutoTokenizer, AutoModel

load_dotenv()

logging.basicConfig(level=logging.INFO)

########################################
# DATABASE CONFIGURATION
########################################

mongo = MongoClient(os.getenv("MONGO_URI"))
mongo_db = mongo[os.getenv("MONGO_DB")]
mongo_collection = mongo_db["docs"]

pg_conn = psycopg2.connect(
    host=os.getenv("SUPABASE_HOST"),
    database=os.getenv("SUPABASE_DB"),
    user=os.getenv("SUPABASE_USER"),
    password=os.getenv("SUPABASE_PASSWORD"),
    port=os.getenv("SUPABASE_PORT")
)

pg_cursor = pg_conn.cursor()

########################################
# LOAD LEGAL BERT
########################################

MODEL_NAME = "nlpaueb/legal-bert-base-uncased"

logging.info("Loading Legal-BERT...")

tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
model = AutoModel.from_pretrained(MODEL_NAME)

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
model.to(device)
model.eval()

logging.info(f"Model running on {device}")

########################################
# TEXT EXTRACTION
########################################

def extract_pdf(path):

    text = ""

    try:
        with pdfplumber.open(path) as pdf:
            for page in pdf.pages:
                t = page.extract_text()
                if t:
                    text += t + "\n"

    except Exception as e:
        logging.error(f"PDF extraction failed {path}: {e}")

    return text


def extract_docx(path):

    text = ""

    try:
        doc = docx.Document(path)

        for para in doc.paragraphs:
            text += para.text + "\n"

    except Exception as e:
        logging.error(f"DOCX extraction failed {path}: {e}")

    return text

########################################
# METADATA
########################################

def extract_publish_date(text):

    match = re.search(r"\b(19|20)\d{2}\b", text)

    if match:
        return datetime(int(match.group()), 1, 1)

    return None

########################################
# LEGAL STRUCTURE DETECTION
########################################

SECTION_PATTERN = r"(Section\s+\d+|Article\s+\d+|Chapter\s+[IVX]+)"


def detect_legal_sections(text):

    return re.search(SECTION_PATTERN, text, re.IGNORECASE) is not None


def split_by_legal_sections(text):

    parts = re.split(SECTION_PATTERN, text)

    sections = []

    for i in range(1, len(parts), 2):

        title = parts[i].strip()
        content = parts[i + 1].strip()

        if len(content) > 100:
            sections.append((title, content))

    return sections


def split_by_paragraphs(text):

    paragraphs = re.split(r"\n\s*\n", text)

    sections = []

    for i, para in enumerate(paragraphs):

        para = para.strip()

        if len(para) < 100:
            continue

        sections.append((f"Paragraph_{i}", para))

    if not sections:
        sections.append(("General", text))

    return sections

########################################
# TOKEN CHUNKING
########################################

def create_token_chunks(text, max_tokens=400, overlap=50):

    tokens = tokenizer.encode(text)

    chunks = []

    step = max_tokens - overlap

    for i in range(0, len(tokens), step):

        chunk_tokens = tokens[i:i + max_tokens]

        chunk_text = tokenizer.decode(chunk_tokens)

        chunks.append(chunk_text)

    return chunks

########################################
# EMBEDDING FUNCTION
########################################

def embed_batch(texts, batch_size=16):

    vectors = []

    for i in range(0, len(texts), batch_size):

        batch = texts[i:i + batch_size]

        inputs = tokenizer(
            batch,
            padding=True,
            truncation=True,
            return_tensors="pt"
        )

        inputs = {k: v.to(device) for k, v in inputs.items()}

        with torch.no_grad():

            outputs = model(**inputs)

        embeddings = outputs.last_hidden_state[:, 0, :].cpu().numpy()

        vectors.extend(embeddings)

    return vectors

########################################
# DOCUMENT STAGING
########################################

def stage_documents(base_folder):

    logging.info("Staging documents...")

    for country in os.listdir(base_folder):

        path = os.path.join(base_folder, country)

        if not os.path.isdir(path):
            continue

        for file in os.listdir(path):

            if mongo_collection.find_one({"filename": file}):
                continue

            file_path = os.path.join(path, file)

            if file.endswith(".pdf"):
                text = extract_pdf(file_path)

            elif file.endswith(".docx"):
                text = extract_docx(file_path)

            else:
                continue

            if not text.strip():
                continue

            publish_date = extract_publish_date(text)

            mongo_collection.insert_one({

                "document_id": str(uuid.uuid4()),
                "country": country,
                "filename": file,
                "publish_date": publish_date,
                "text": text

            })

    logging.info("Mongo staging complete")

########################################
# HIERARCHICAL VECTOR PIPELINE
########################################

def process_country(country):

    logging.info(f"Processing {country}")

    docs = mongo_collection.find({"country": country})

    for doc in tqdm(docs):

        doc_id = doc["document_id"]

        ################################
        # SKIP IF DOCUMENT ALREADY EXISTS
        ################################

        pg_cursor.execute(
            "SELECT 1 FROM legal_documents WHERE document_id = %s LIMIT 1",
            (doc_id,)
        )

        if pg_cursor.fetchone():
            logging.info(f"Skipping already processed doc {doc_id}")
            continue

        ################################
        # DOCUMENT EMBEDDING
        ################################

        doc_vector = embed_batch([doc["text"][:5000]])[0]

        pg_cursor.execute(
            """
            INSERT INTO legal_documents
            (document_id, vector, country, publish_date)
            VALUES (%s,%s,%s,%s)
            """,
            (
                doc_id,
                [float(x) for x in doc_vector],
                doc["country"],
                doc["publish_date"]
            )
        )

        ################################
        # SECTION LEVEL
        ################################

        if detect_legal_sections(doc["text"]):
            sections = split_by_legal_sections(doc["text"])
        else:
            sections = split_by_paragraphs(doc["text"])

        for title, content in sections:

            section_id = str(uuid.uuid4())

            section_vector = embed_batch([content])[0]

            pg_cursor.execute(
                """
                INSERT INTO legal_sections
                (section_id, vector, document_id, section_title)
                VALUES (%s,%s,%s,%s)
                """,
                (
                    section_id,
                    [float(x) for x in section_vector],
                    doc_id,
                    title
                )
            )

            ################################
            # CHUNK LEVEL
            ################################

            chunks = create_token_chunks(content)

            embeddings = embed_batch(chunks)

            rows = []

            for chunk, vector in zip(chunks, embeddings):

                rows.append((
                    str(uuid.uuid4()),
                    [float(x) for x in vector],
                    section_id,
                    doc_id,
                    chunk
                ))

            execute_batch(

                pg_cursor,

                """
                INSERT INTO legal_chunks
                (chunk_id, vector, section_id, document_id, chunk_text)
                VALUES (%s,%s,%s,%s,%s)
                """,

                rows

            )

    pg_conn.commit()

    logging.info(f"Finished {country}")

########################################
# RUN PIPELINE
########################################

def run_pipeline():

    stage_documents("legal_documents")

    countries = mongo_collection.distinct("country")

    for country in countries:

        process_country(country)


if __name__ == "__main__":
    run_pipeline()