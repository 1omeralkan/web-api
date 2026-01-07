"""
SQLAlchemy Declarative Base
===========================

Tüm ORM modellerinin miras alacağı temel sınıf.

YAZILIM KALİTE GÜVENCESİ AÇISINDAN:
-----------------------------------
- Merkezi base class ile tutarlı model yapısı
- TimestampMixin ile otomatik created_at/updated_at alanları
- Tüm modellerde ortak davranışlar tek yerden yönetilir
"""

from datetime import datetime
from sqlalchemy import DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """
    Tüm modellerin temel sınıfı.
    SQLAlchemy 2.0 style declarative base.
    """
    pass


class TimestampMixin:
    """
    Zaman damgası alanları için mixin.
    
    Bu mixin'i kullanan modeller otomatik olarak:
    - created_at: Kayıt oluşturulma zamanı
    - updated_at: Son güncelleme zamanı (opsiyonel)
    
    alanlarına sahip olur.
    """
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="Kayıt oluşturulma zamanı"
    )
