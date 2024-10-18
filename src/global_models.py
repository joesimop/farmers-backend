from pydantic import BaseModel
from src.database_enum_types import VendorType, FeeType
from decimal import Decimal
from typing import Optional

class IdConcealer(BaseModel):
    id: int

class MarketVendorFee(BaseModel):
    vendor_type: VendorType
    fee_type: FeeType
    rate: Decimal
    rate_2: Optional[Decimal] = None

    def toJSON(self):
        return {
            "vendor_type": self.vendor_type.value,
            "fee_type": self.fee_type.value,
            "rate": str(self.rate),
            "rate_2": str(self.rate_2) if self.rate_2 is not None else None
        }
