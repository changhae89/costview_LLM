from pydantic import BaseModel
from typing import Optional


class ConsumerItemCreate(BaseModel):
    category_code: str
    name_ko: str
    name_en: Optional[str] = None
    unit: str
    typical_monthly_spend: Optional[float] = None
    weight: Optional[float] = None
    description: Optional[str] = None


class ConsumerItemUpdate(BaseModel):
    category_code: Optional[str] = None
    name_ko: Optional[str] = None
    name_en: Optional[str] = None
    unit: Optional[str] = None
    typical_monthly_spend: Optional[float] = None
    weight: Optional[float] = None
    description: Optional[str] = None
