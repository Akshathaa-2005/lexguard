import os
import logging
import numpy as np
import torch
from transformers import AutoTokenizer, AutoModel

logger = logging.getLogger(__name__)

# Must match the model used during ingestion
EMBEDDING_MODEL = "nlpaueb/legal-bert-base-uncased"
EMBEDDING_DIM = 768


class EmbeddingModel:

    def __init__(self):

        self.device = torch.device(
            "cuda" if torch.cuda.is_available() else "cpu"
        )

        logger.info(f"Loading embedding model: {EMBEDDING_MODEL}")

        self.tokenizer = AutoTokenizer.from_pretrained(EMBEDDING_MODEL)
        self.model = AutoModel.from_pretrained(EMBEDDING_MODEL)
        self.model.to(self.device)
        self.model.eval()

        logger.info(f"Embedding model loaded on {self.device}")

    def embed(self, text: str) -> np.ndarray:
        """
        Generate a 768-dim embedding using CLS token,
        identical to how ingestion generated stored vectors.
        """
        inputs = self.tokenizer(
            text,
            padding=True,
            truncation=True,
            max_length=512,
            return_tensors="pt",
        )

        inputs = {k: v.to(self.device) for k, v in inputs.items()}

        with torch.no_grad():
            outputs = self.model(**inputs)

        # CLS token embedding — same as ingestion pipeline
        embedding = outputs.last_hidden_state[:, 0, :]

        return embedding.cpu().numpy()[0]
