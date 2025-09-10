import logging
from dataclasses import dataclass
from typing import Optional, Dict, Any

from app.core.performance_tuner import get_performance_tuner, PerformanceTuner

logger = logging.getLogger(__name__)


@dataclass
class SearchPlan:
    """Decisions about which search engines to use and how to weight them."""
    use_ir: bool
    use_vector: bool
    use_recommendation: bool
    vector_weight: float
    ir_weight: float
    recommendation_weight: float


class SearchPlanner:
    """Heuristic planner that selects search strategy for a query."""

    def __init__(self, performance_tuner: Optional[PerformanceTuner] = None):
        self.performance_tuner = performance_tuner or get_performance_tuner()

    def plan(self, query: str, filters: Optional[Dict[str, Any]] = None) -> SearchPlan:
        """Return a search plan based on the query and optional filters."""
        filters = filters or {}
        text = (query or "").strip().lower()

        base_weights = self.performance_tuner.get_search_weights()
        vector_weight = base_weights["vector_weight"]
        ir_weight = base_weights["ir_weight"]
        recommendation_weight = 0.2  # default contribution when recommendations are used

        tokens = text.split()
        token_len = len(tokens)

        # Determine which engines to use
        use_ir = token_len > 0
        use_vector = token_len > 1  # very short queries tend not to benefit from vectors
        use_recommendation = any(k in text for k in ["recommend", "추천", "similar"]) or \
            bool(filters.get("document_id") or filters.get("user_id"))

        # Adjust weights heuristically
        if token_len <= 2:
            ir_weight += 0.2
            vector_weight -= 0.2
        elif token_len >= 8:
            vector_weight += 0.2
            ir_weight -= 0.2

        # Clamp and normalize
        vector_weight = max(0.0, vector_weight)
        ir_weight = max(0.0, ir_weight)
        total = vector_weight + ir_weight
        if total > 0:
            vector_weight /= total
            ir_weight /= total

        plan = SearchPlan(
            use_ir=use_ir,
            use_vector=use_vector,
            use_recommendation=use_recommendation,
            vector_weight=vector_weight,
            ir_weight=ir_weight,
            recommendation_weight=recommendation_weight,
        )

        logger.info("SearchPlanner decision for query '%s': %s", query, plan)
        return plan


# Singleton access -----------------------------------------------------------
_search_planner: Optional[SearchPlanner] = None


def get_search_planner() -> SearchPlanner:
    """Return a singleton instance of SearchPlanner."""
    global _search_planner
    if _search_planner is None:
        _search_planner = SearchPlanner()
    return _search_planner
