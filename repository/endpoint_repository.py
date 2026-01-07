"""
Endpoint Repository
===================

ApiEndpoint tablosu için veri erişim katmanı.

YAZILIM KALİTE GÜVENCESİ AÇISINDAN:
-----------------------------------
1. Repository Pattern: Veri erişimi iş mantığından ayrılır
2. Dependency Injection: Service katmanına enjekte edilebilir
3. Async/await: Non-blocking veritabanı işlemleri
4. Type hints: Tip güvenliği ve IDE desteği

TEMEL OPERASYONLAR:
-------------------
- get_or_create: Endpoint varsa getir, yoksa oluştur
- get_all: Tüm endpoint'leri listele
- get_by_id: ID ile getir
"""

from typing import Optional, List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert as pg_insert

from models.api_endpoint import ApiEndpoint
from core.logging import get_logger

logger = get_logger(__name__)


class EndpointRepository:
    """
    ApiEndpoint tablosu için repository sınıfı.
    
    Her metod bir AsyncSession alır - bu dependency injection pattern'i
    test sırasında mock session kullanımını mümkün kılar.
    """
    
    async def get_or_create(
        self,
        session: AsyncSession,
        path: str,
        method: str,
        description: Optional[str] = None
    ) -> ApiEndpoint:
        """
        Endpoint'i path ve method'a göre getirir veya yeni oluşturur.
        
        Bu metod, middleware tarafından her request'te çağrılır.
        Upsert (INSERT ON CONFLICT) pattern'i kullanarak atomik işlem sağlar.
        
        Args:
            session: Async database session
            path: API endpoint path (ör: "/users")
            method: HTTP method (GET, POST vb.)
            description: Opsiyonel açıklama
            
        Returns:
            ApiEndpoint: Mevcut veya yeni oluşturulan endpoint
        """
        # PostgreSQL upsert (INSERT ON CONFLICT DO NOTHING)
        stmt = pg_insert(ApiEndpoint).values(
            path=path,
            method=method.upper(),
            description=description
        ).on_conflict_do_nothing(
            index_elements=["path", "method"]
        )
        
        await session.execute(stmt)
        await session.flush()
        
        # Endpoint'i getir
        result = await session.execute(
            select(ApiEndpoint).where(
                ApiEndpoint.path == path,
                ApiEndpoint.method == method.upper()
            )
        )
        endpoint = result.scalar_one()
        
        logger.debug(f"Endpoint get_or_create: {method.upper()} {path}")
        return endpoint
    
    async def get_all(
        self,
        session: AsyncSession,
        skip: int = 0,
        limit: int = 100
    ) -> List[ApiEndpoint]:
        """
        Tüm endpoint'leri listeler.
        
        Pagination desteği ile büyük veri setlerinde performans sağlar.
        
        Args:
            session: Async database session
            skip: Atlanacak kayıt sayısı (offset)
            limit: Maksimum kayıt sayısı
            
        Returns:
            List[ApiEndpoint]: Endpoint listesi
        """
        result = await session.execute(
            select(ApiEndpoint)
            .order_by(ApiEndpoint.path, ApiEndpoint.method)
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())
    
    async def get_by_id(
        self,
        session: AsyncSession,
        endpoint_id: int
    ) -> Optional[ApiEndpoint]:
        """
        ID ile endpoint getirir.
        
        Args:
            session: Async database session
            endpoint_id: Endpoint ID
            
        Returns:
            Optional[ApiEndpoint]: Endpoint veya None
        """
        result = await session.execute(
            select(ApiEndpoint).where(ApiEndpoint.id == endpoint_id)
        )
        return result.scalar_one_or_none()
    
    async def get_by_path_and_method(
        self,
        session: AsyncSession,
        path: str,
        method: str
    ) -> Optional[ApiEndpoint]:
        """
        Path ve method ile endpoint getirir.
        
        Args:
            session: Async database session
            path: API path
            method: HTTP method
            
        Returns:
            Optional[ApiEndpoint]: Endpoint veya None
        """
        result = await session.execute(
            select(ApiEndpoint).where(
                ApiEndpoint.path == path,
                ApiEndpoint.method == method.upper()
            )
        )
        return result.scalar_one_or_none()
    
    async def count(self, session: AsyncSession) -> int:
        """
        Toplam endpoint sayısını döndürür.
        """
        from sqlalchemy import func
        result = await session.execute(
            select(func.count(ApiEndpoint.id))
        )
        return result.scalar_one()


# Singleton instance
endpoint_repository = EndpointRepository()
