from pydantic import BaseModel
from typing import List, Optional


class CategoryCreate(BaseModel):
    code: str
    name_ko: str
    name_en: str
    sort_order: int = 0
    keywords: List[str] = []


class CategoryUpdate(BaseModel):
    name_ko: Optional[str] = None
    name_en: Optional[str] = None
    sort_order: Optional[int] = None
    keywords: Optional[List[str]] = None
