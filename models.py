from datetime import datetime
from typing import List, Optional, Literal
from pydantic import BaseModel, Field

class MenuItem(BaseModel):
    name: str = Field(description="Name of the service or product")
    category: str = Field(default="General", description="Category or treatment type")
    price: float = Field(description="Current price in numerical format")
    currency: str = Field(default="USD", description="Currency code")
    unit: Optional[str] = Field(default="session", description="Billing frequency or unit")
    description: Optional[str] = Field(default=None, description="Short description or scope")

class CompetitorSnapshot(BaseModel):
    competitor_id: str
    competitor_name: str
    url: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    items: List[MenuItem]

class PriceDelta(BaseModel):
    competitor_id: str
    competitor_name: str
    item_name: str
    category: str
    old_price: Optional[float]
    new_price: Optional[float]
    currency: str
    delta_amount: Optional[float]
    delta_percentage: Optional[float]
    change_type: Literal["PRICE_INCREASE", "PRICE_DECREASE", "NEW_ITEM", "DISCONTINUED", "UNCHANGED"]
    detected_at: datetime = Field(default_factory=datetime.utcnow)

class DiffReport(BaseModel):
    competitor_id: str
    competitor_name: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    total_items_scanned: int
    price_increases: List[PriceDelta] = []
    price_decreases: List[PriceDelta] = []
    new_items: List[PriceDelta] = []
    discontinued_items: List[PriceDelta] = []
    unchanged_items: List[PriceDelta] = []
    has_significant_change: bool = False
