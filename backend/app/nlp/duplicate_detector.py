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
    Compute semantic cosine similarity between two individual texts.
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
    area: str = "",
    max_distance_meters: float = 500.0
) -> List[Dict[str, Any]]:
    """
    Search active issues using Multi-Signal Matching:
      - Tier 1 (GPS Proximity): dist <= 500m (threshold 0.45)
      - Tier 2 (Same Area Name): matching area name string (threshold 0.55, overrides GPS drift)
      - Tier 3 (Global High Text Similarity): similarity >= 0.85 (overrides location)
    
    Uses batch sentence encoding for high performance.
    """
    query_title_norm = normalize_text(title)
    query_desc_norm = normalize_text(description)
    query_text_norm = f"{query_title_norm} {query_desc_norm}".strip()
    query_area_norm = normalize_text(area)

    if not query_text_norm:
        return []

    # Fetch active candidates from DB
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

    if not candidates:
        return []

    # Pre-process candidate distance & text
    candidate_data = []
    for cand in candidates:
        cand_lat = cand["latitude"]
        cand_lng = cand["longitude"]
        dist = haversine_distance(latitude, longitude, cand_lat, cand_lng)
        
        cand_area = cand.get("area") or ""
        cand_area_norm = normalize_text(cand_area)
        
        same_area = bool(query_area_norm and cand_area_norm and (
            query_area_norm in cand_area_norm or cand_area_norm in query_area_norm
        ))

        cand_title_norm = normalize_text(cand.get("title", ""))
        cand_desc_norm = normalize_text(cand.get("description", ""))
        cand_text_norm = f"{cand_title_norm} {cand_desc_norm}".strip()

        candidate_data.append({
            "db_row": cand,
            "dist": dist,
            "same_area": same_area,
            "cand_text_norm": cand_text_norm
        })

    # Batch compute similarity scores
    model = get_sentence_model()
    similarity_scores = []

    if model is not None and candidate_data:
        try:
            from sentence_transformers import util
            all_texts = [query_text_norm] + [cd["cand_text_norm"] for cd in candidate_data]
            embeddings = model.encode(all_texts, convert_to_tensor=True)
            
            query_emb = embeddings[0]
            candidate_embs = embeddings[1:]
            
            sim_matrix = util.cos_sim(query_emb, candidate_embs)[0]
            similarity_scores = [float(s) for s in sim_matrix]
        except Exception as e:
            logger.error(f"Batch vector encoding failed: {e}. Falling back to token Jaccard.")
            model = None

    if model is None:
        # Fallback to Jaccard token overlap
        words_q = set(query_text_norm.split())
        for cd in candidate_data:
            words_c = set(cd["cand_text_norm"].split())
            if not words_q or not words_c:
                similarity_scores.append(0.0)
            else:
                sim = len(words_q.intersection(words_c)) / len(words_q.union(words_c))
                similarity_scores.append(sim)

    # Multi-Signal Filtering
    duplicates = []
    for i, cd in enumerate(candidate_data):
        sim_score = similarity_scores[i]
        dist = cd["dist"]
        same_area = cd["same_area"]
        cand = cd["db_row"]

        # Determine if candidate qualifies under Multi-Signal tiers
        is_duplicate = False

        if dist <= max_distance_meters and sim_score >= 0.45:
            # Tier 1: Close GPS distance + text similarity
            is_duplicate = True
        elif same_area and sim_score >= 0.55:
            # Tier 2: Same area name + text similarity (handles GPS drift)
            is_duplicate = True
        elif sim_score >= 0.85:
            # Tier 3: Very high text similarity (handles identical complaint across city)
            is_duplicate = True

        if is_duplicate:
            duplicates.append({
                "id": str(cand["id"]),
                "title": cand["title"],
                "description": cand["description"],
                "category": cand["category"],
                "status": cand["status"],
                "image_url": cand.get("image_url"),
                "upvotes": cand.get("upvote_count", 0),
                "downvotes": cand.get("downvote_count", 0),
                "distance_meters": round(dist, 1),
                "similarity_score": round(sim_score * 100, 1),
                "created_at": cand["created_at"].isoformat() if cand.get("created_at") else None
            })

    # Sort by similarity score descending, then distance ascending
    duplicates.sort(key=lambda x: (x["similarity_score"], -x["distance_meters"]), reverse=True)
    logger.info(f"Multi-Signal Duplicate search for '{title}' (Area: '{area}') found {len(duplicates)} duplicate(s).")
    return duplicates
