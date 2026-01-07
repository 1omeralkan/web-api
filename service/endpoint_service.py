"""
Endpoint Service
================

ApiEndpoint için iş mantığı katmanı.

YAZILIM KALİTE GÜVENCESİ AÇISINDAN:
-----------------------------------
1. Repository'den soyutlama: Veri erişimi değişse bile servis aynı kalır
2. Business logic centralization: Tüm iş kuralları tek yerde
3. Transaction management: Service seviyesinde transaction kontrolü
"""

from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession

from repository.endpoint_repository import endpoint_repository
from models.api_endpoint import ApiEndpoint
from core.logging import get_logger

logger = get_logger(__name__)


class EndpointService:
    """
    ApiEndpoint iş mantığı servisi.
    """
    
    async def get_or_create_endpoint(
        self,
        session: AsyncSession,
        path: str,
        method: str,
        description: Optional[str] = None
    ) -> ApiEndpoint:
        """
        Endpoint'i getirir veya oluşturur.
        
        Middleware tarafından kullanılır.
        """
        return await endpoint_repository.get_or_create(
            session=session,
            path=path,
            method=method,
            description=description
        )
    
    async def list_endpoints(
        self,
        session: AsyncSession,
        skip: int = 0,
        limit: int = 100
    ) -> List[ApiEndpoint]:
        """
        Tüm endpoint'leri listeler.
        """
        return await endpoint_repository.get_all(
            session=session,
            skip=skip,
            limit=limit
        )
    
    async def get_endpoint_by_id(
        self,
        session: AsyncSession,
        endpoint_id: int
    ) -> Optional[ApiEndpoint]:
        """
        ID ile endpoint getirir.
        """
        return await endpoint_repository.get_by_id(
            session=session,
            endpoint_id=endpoint_id
        )
    
    async def get_endpoint_count(self, session: AsyncSession) -> int:
        """
        Toplam endpoint sayısını döndürür.
        """
        return await endpoint_repository.count(session)


# Singleton instance
endpoint_service = EndpointService()
