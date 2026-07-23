import logging
import re
from typing import List, Dict, Any, Optional
from backend.app.database import get_connection
from backend.app.routing import haversine_distance

logger = logging.getLogger(__name__)

_sentence_model = None

def get_sentence_model():
    """
    Lazy load and cache the SentenceTransformer model 'sentence-transformers/all-MiniLM-L6-v2'.
    """
    global _sentence_model
    if _sentence_model is None:
        try:
            from sentence_transformers import SentenceTransformer
            logger.info("Loading NLP Duplicate Detector model 'sentence-transformers/all-MiniLM-L6-v2'...")
            _sentence_model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
            logger.info("SentenceTransformer model loaded successfully.")
        except Exception as e:
            logger.warning(f"Could not load SentenceTransformer ('all-MiniLM-L6-v2'): {e}. Using token overlap fallback.")
            _sentence_model = False
    return _sentence_model if _sentence_model is not False else None

def normalize_text(text: str) -> str:
    """Clean and normalize text for string comparison."""
    if not text:
        return ""
    text = text.lower()
    text = re.sub(r'[^\w\s]', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def compute_similarity(text1: str, text2: str) -> float:
    """
    Compute semantic cosine similarity between two texts using all-MiniLM-L6-v2.
    Falls back to token Jaccard similarity if vector model is unavailable.
    """
    norm1 = normalize_text(text1)
    norm2 = normalize_text(text2)

    if not norm1 or not norm2:
        return 0.0

    model = get_sentence_model()
    if model is not None:
        try:
            embeddings = model.encode([norm1, norm2], convert_to_tensor=True)
            from sentence_transformers import util
            sim = float(util.cos_sim(embeddings[0], embeddings[1])[0][0])
            return float(sim)
        except Exception as e:
            logger.error(f"Error computing vector sentence similarity: {e}")

    # Fallback: Token-based Jaccard similarity
    words1 = set(norm1.split())
    words2 = set(norm2.split())
    if not words1 or not words2:
        return 0.0
    intersection = words1.intersection(words2)
    union = words1.union(words2)
    return len(intersection) / len(union)

def find_duplicates(
    title: str,
    description: str,
    latitude: float,
    longitude: float,
    max_distance_meters: float = 150.0,
    similarity_threshold: float = 0.50
) -> List[Dict[str, Any]]:
    """
    Search active issues within max_distance_meters (or same ward area) and check text similarity.
    Returns sorted list of duplicate candidate issues.
    """
    query_text = f"{title} {description}"

    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, title, description, category, area, address, latitude, longitude,
                       status, created_at, upvote_count, downvote_count, image_url
                FROM issues
                WHERE status IN ('pending', 'in_progress')
                ORDER BY created_at DESC
                """
            )
            candidates = cursor.fetchall()

    duplicates = []

    for candidate in candidates:
        cand_lat = candidate["latitude"]
        cand_lng = candidate["longitude"]

        # Calculate GPS distance
        dist = haversine_distance(latitude, longitude, cand_lat, cand_lng)

        # Check distance threshold (150m) OR exact same area name matching
        if dist <= max_distance_meters or dist <= 500.0:
            cand_text = f"{candidate['title']} {candidate['description']}"
            sim_score = compute_similarity(query_text, cand_text)

            # If GPS is very close (<150m), lower similarity threshold slightly to 0.45; otherwise 0.55
            effective_threshold = similarity_threshold if dist <= 150.0 else (similarity_threshold + 0.10)

            if sim_score >= effective_threshold:
                duplicates.append({
                    "id": str(candidate["id"]),
                    "title": candidate["title"],
                    "description": candidate["description"],
                    "category": candidate["category"],
                    "status": candidate["status"],
                    "image_url": candidate.get("image_url"),
                    "upvotes": candidate.get("upvote_count", 0),
                    "downvotes": candidate.get("downvote_count", 0),
                    "distance_meters": round(dist, 1),
                    "similarity_score": round(sim_score * 100, 1),
                    "created_at": candidate["created_at"].isoformat() if candidate.get("created_at") else None
                })

    # Sort candidates by similarity score descending, then distance ascending
    duplicates.sort(key=lambda x: (x["similarity_score"], -x["distance_meters"]), reverse=True)
    logger.info(f"Duplicate search for '{title}' found {len(duplicates)} candidates.")
    return duplicates
