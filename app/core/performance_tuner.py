#!/usr/bin/env python3
"""
자동 성능 튜닝 모듈
검색 가중치 등 시스템 파라미터를 동적으로 조정합니다.
"""

import logging
from typing import Optional

from app.core.database import get_db_manager, DatabaseManager

logger = logging.getLogger(__name__)


class PerformanceTuner:
    """시스템 성능 튜너 클래스"""
    
    def __init__(self, db_manager: Optional[DatabaseManager] = None):
        self.db_manager = db_manager or get_db_manager()
        self._initialize_default_weights()
    
    def _initialize_default_weights(self):
        """기본 검색 가중치 설정 (system_settings에 없으면 초기화).
        벡터 검색과 IR 검색의 초기 가중치를 데이터베이스에 저장합니다.
        """
        if self.db_manager.get_setting("vector_weight") is None:
            self.db_manager.set_setting("vector_weight", "0.6", "벡터 검색 가중치")
        if self.db_manager.get_setting("ir_weight") is None:
            self.db_manager.set_setting("ir_weight", "0.4", "IR 검색 가중치")
        logger.info("Default search weights initialized/checked.")

    def get_search_weights(self) -> dict[str, float]:
        """현재 검색 가중치를 조회합니다."""
        vector_weight = float(self.db_manager.get_setting("vector_weight", "0.6"))
        ir_weight = float(self.db_manager.get_setting("ir_weight", "0.4"))
        return {"vector_weight": vector_weight, "ir_weight": ir_weight}

    def set_search_weights(self, vector_weight: float, ir_weight: float):
        """검색 가중치를 설정합니다."""
        self.db_manager.set_setting("vector_weight", str(vector_weight), "벡터 검색 가중치")
        self.db_manager.set_setting("ir_weight", str(ir_weight), "IR 검색 가중치")
        logger.info(f"Search weights updated: vector={vector_weight}, ir={ir_weight}")

    def tune_search_weights(self, strategy: str = "basic_optimization"):
        """검색 가중치를 튜닝합니다 (예시).
        주어진 전략에 따라 벡터 검색과 IR 검색의 가중치를 조정하여 검색 성능을 최적화합니다.
        """
        current_weights = self.get_search_weights()
        logger.info(f"Starting search weight tuning with strategy: {strategy}. Current weights: {current_weights}")

        if strategy == "basic_optimization":
            # 예시: 간단한 규칙 기반 튜닝
            # 실제로는 성능 지표, 피드백 등을 기반으로 복잡한 로직이 들어감
            new_vector_weight = round(current_weights["vector_weight"] * 1.05, 2)
            new_ir_weight = round(current_weights["ir_weight"] * 0.95, 2)
            
            # 합이 1이 되도록 정규화 (선택적, 필요에 따라)
            total = new_vector_weight + new_ir_weight
            if total != 0:
                new_vector_weight = round(new_vector_weight / total, 2)
                new_ir_weight = round(new_ir_weight / total, 2)

            self.set_search_weights(new_vector_weight, new_ir_weight)
            logger.info(f"Tuning complete. New weights: vector={new_vector_weight}, ir={new_ir_weight}")
        else:
            logger.warning(f"Unknown tuning strategy: {strategy}")


# 전역 인스턴스
_performance_tuner: Optional[PerformanceTuner] = None

def get_performance_tuner() -> PerformanceTuner:
    """PerformanceTuner 싱글톤 인스턴스 반환"""
    global _performance_tuner
    if _performance_tuner is None:
        _performance_tuner = PerformanceTuner()
    return _performance_tuner
