"""
Suggestion Repository
=====================

OptimizationSuggestion tablosu için veri erişim katmanı.

YAZILIM KALİTE GÜVENCESİ AÇISINDAN:
-----------------------------------
1. Upsert pattern: Aynı öneri tekrar oluşturulmaz
2. Severity bazlı sıralama: Kritik öneriler önce görülür
3. Bulk operations: Analiz sonrası toplu öneri ekleme
"""

from typing import Optional, List
from sqlalchemy import select, and_, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import selectinload

from models.optimization_suggestion import OptimizationSuggestion, ProblemType, Severity
from models.api_endpoint import ApiEndpoint
from core.logging import get_logger

logger = get_logger(__name__)


class SuggestionRepository:
    """
    OptimizationSuggestion tablosu için repository sınıfı.
    """
    
    async def create_or_update(
        self,
        session: AsyncSession,
        endpoint_id: int,
        problem_type: ProblemType,
        suggestion: str,
        severity: Severity,
        avg_response_time_ms: Optional[float] = None,
        error_rate_percent: Optional[float] = None
    ) -> OptimizationSuggestion:
        """
        Yeni öneri oluşturur veya mevcutu günceller.
        
        Aynı endpoint + problem_type kombinasyonu için:
        - Mevcut öneri varsa güncellenir
        - Yoksa yeni oluşturulur
        
        Args:
            session: Async database session
            endpoint_id: İlişkili endpoint ID
            problem_type: Problem tipi
            suggestion: Öneri metni
            severity: Önem seviyesi
            avg_response_time_ms: Ortalama response süresi
            error_rate_percent: Hata oranı
            
        Returns:
            OptimizationSuggestion: Oluşturulan/güncellenen öneri
        """
        # Mevcut öneriyi kontrol et
        existing = await session.execute(
            select(OptimizationSuggestion).where(
                and_(
                    OptimizationSuggestion.endpoint_id == endpoint_id,
                    OptimizationSuggestion.problem_type == problem_type
                )
            )
        )
        existing_suggestion = existing.scalar_one_or_none()
        
        if existing_suggestion:
            # Güncelle
            existing_suggestion.suggestion = suggestion
            existing_suggestion.severity = severity
            existing_suggestion.avg_response_time_ms = avg_response_time_ms
            existing_suggestion.error_rate_percent = error_rate_percent
            await session.flush()
            logger.debug(f"Öneri güncellendi: endpoint_id={endpoint_id}, type={problem_type.value}")
            return existing_suggestion
        else:
            # Yeni oluştur
            new_suggestion = OptimizationSuggestion(
                endpoint_id=endpoint_id,
                problem_type=problem_type,
                suggestion=suggestion,
                severity=severity,
                avg_response_time_ms=avg_response_time_ms,
                error_rate_percent=error_rate_percent
            )
            session.add(new_suggestion)
            await session.flush()
            logger.debug(f"Yeni öneri oluşturuldu: endpoint_id={endpoint_id}, type={problem_type.value}")
            return new_suggestion
    
    async def get_all(
        self,
        session: AsyncSession,
        skip: int = 0,
        limit: int = 100,
        severity: Optional[Severity] = None,
        problem_type: Optional[ProblemType] = None
    ) -> List[OptimizationSuggestion]:
        """
        Önerileri listeler.
        
        Sıralama: Kritik öneriler önce (severity desc)
        
        Args:
            session: Async database session
            skip: Offset
            limit: Maksimum kayıt
            severity: Opsiyonel severity filtresi
            problem_type: Opsiyonel problem type filtresi
            
        Returns:
            List[OptimizationSuggestion]: Öneri listesi
        """
        query = select(OptimizationSuggestion).options(selectinload(OptimizationSuggestion.endpoint))
        
        conditions = []
        if severity:
            conditions.append(OptimizationSuggestion.severity == severity)
        if problem_type:
            conditions.append(OptimizationSuggestion.problem_type == problem_type)
        
        if conditions:
            query = query.where(and_(*conditions))
        
        # Severity'ye göre sırala (CRITICAL > HIGH > MEDIUM > LOW)
        query = query.order_by(
            desc(OptimizationSuggestion.severity),
            desc(OptimizationSuggestion.created_at)
        ).offset(skip).limit(limit)
        
        result = await session.execute(query)
        return list(result.scalars().all())
    
    async def get_by_endpoint(
        self,
        session: AsyncSession,
        endpoint_id: int
    ) -> List[OptimizationSuggestion]:
        """
        Endpoint bazlı önerileri getirir.
        """
        result = await session.execute(
            select(OptimizationSuggestion)
            .where(OptimizationSuggestion.endpoint_id == endpoint_id)
            .order_by(desc(OptimizationSuggestion.severity))
        )
        return list(result.scalars().all())
    
    async def delete_by_endpoint_and_type(
        self,
        session: AsyncSession,
        endpoint_id: int,
        problem_type: ProblemType
    ) -> bool:
        """
        Belirli endpoint ve problem tipi için öneriyi siler.
        
        Kullanım: Problem çözüldüğünde öneriyi kaldırmak için.
        
        Returns:
            bool: Silme başarılı mı
        """
        result = await session.execute(
            select(OptimizationSuggestion).where(
                and_(
                    OptimizationSuggestion.endpoint_id == endpoint_id,
                    OptimizationSuggestion.problem_type == problem_type
                )
            )
        )
        suggestion = result.scalar_one_or_none()
        
        if suggestion:
            await session.delete(suggestion)
            await session.flush()
            logger.debug(f"Öneri silindi: endpoint_id={endpoint_id}, type={problem_type.value}")
            return True
        return False
    
    async def count(
        self,
        session: AsyncSession,
        severity: Optional[Severity] = None
    ) -> int:
        """
        Toplam öneri sayısını döndürür.
        """
        from sqlalchemy import func
        
        query = select(func.count(OptimizationSuggestion.id))
        if severity:
            query = query.where(OptimizationSuggestion.severity == severity)
        
        result = await session.execute(query)
        return result.scalar_one()


# Singleton instance
suggestion_repository = SuggestionRepository()
