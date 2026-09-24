from datetime import date
from typing import Literal
from pydantic import BaseModel, Field, ConfigDict, field_validator

CropName = Literal['Cotton','Wheat','Groundnut','Rice']
Role = Literal['farmer','buyer','fpo']

class Strict(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True, allow_inf_nan=False)

class ProfileIn(Strict):
    name: str = Field(min_length=2,max_length=120)
    role: Role
    location: str = Field(default='Surat',min_length=2,max_length=150)
    language: Literal['en','gu','hi','mr'] = 'en'

class CropIn(Strict):
    name: CropName
    variety: str = Field(min_length=1,max_length=100)
    quantity: float = Field(gt=0,le=1000000)
    grade: Literal['A','B','C']
    parameters: dict[str,float | str] = Field(default_factory=dict)
    location: str = Field(min_length=2,max_length=150)
    sell_date: date
    preferred_market: str = Field(default='',max_length=150)
    notes: str = Field(default='',max_length=2000)
    public: bool = False
    acknowledged: bool

    @field_validator('acknowledged')
    @classmethod
    def consent(cls,v):
        if not v:
            raise ValueError('Confirm your crop details are accurate.')
        return v

    @field_validator('sell_date')
    @classmethod
    def valid_date(cls,v):
        from datetime import datetime
        from zoneinfo import ZoneInfo
        if v < datetime.now(ZoneInfo('Asia/Kolkata')).date():
            raise ValueError('Selling date cannot be in the past.')
        return v

    @field_validator('parameters')
    @classmethod
    def valid_params(cls,v):
        import math
        if len(v)>20:
            raise ValueError('Too many parameters.')
        for key,val in v.items():
            if len(key)>80 or (isinstance(val,str) and len(val)>150):
                raise ValueError('Parameter too long.')
            if isinstance(val,(float,int)) and (not math.isfinite(val) or val<0):
                raise ValueError('Invalid measurement.')
            if key.endswith('_pct') and isinstance(val,(int,float)) and val>100:
                raise ValueError('Percentage must be 0–100.')
        return v

class DemandIn(Strict):
    company: str = Field(min_length=2,max_length=160)
    crop: CropName
    grade: Literal['A','B','C']
    quantity: float = Field(gt=0,le=1000000)
    price: float = Field(gt=0,le=10000000)
    location: str = Field(min_length=2,max_length=150)
    required_by: date
    contact: str = Field(min_length=5,max_length=150)

    @field_validator('required_by')
    @classmethod
    def valid_date(cls,v):
        return CropIn.valid_date(v)

class FPOIn(Strict):
    name: str = Field(min_length=2,max_length=180)
    location: str = Field(min_length=2,max_length=150)
    members: int = Field(ge=0,le=1000000)
    capacity: float = Field(ge=0,le=10000000)
    services: list[Literal['Buy & Sell','Storage','Transportation']] = Field(max_length=3)
    contact: str = Field(min_length=5,max_length=150)

class NetIn(Strict):
    price: float = Field(ge=0,le=10000000)
    transport: float = Field(ge=0,le=10000000)
    storage: float = Field(ge=0,le=10000000)
    charges: float = Field(ge=0,le=10000000)
    quantity: float = Field(gt=0,le=1000000)

class Opportunity(NetIn):
    name: str = Field(min_length=1,max_length=150)

class CompareIn(Strict):
    opportunities: list[Opportunity] = Field(min_length=1,max_length=20)

class InterestIn(Strict):
    message: str = Field(default='',max_length=1000)

class TokenIn(Strict):
    token: str = Field(min_length=20,max_length=500)

class PurchaseIn(Strict):
    crop_id: str = Field(min_length=1,max_length=36)
    quantity: float = Field(gt=0,le=1000000)
    price: float = Field(gt=0,le=10000000)
    buyer_contact: str = Field(min_length=5,max_length=150)
    message: str = Field(default='',max_length=1000)

class PurchaseUpdate(Strict):
    status: Literal['accepted','declined','cancelled','completed']
    seller_contact: str = Field(default='',max_length=150)

class MarketContext(Strict):
    name: CropName
    variety: str = Field(min_length=1,max_length=100)
    grade: Literal['A','B','C']
    quantity: float = Field(gt=0,le=1000000)
    location: str = Field(min_length=2,max_length=150)
    sell_date: date
    parameters: dict[str,float | str] = Field(default_factory=dict,max_length=20)

class MarketOptionsIn(Strict):
    crop: MarketContext
    storage_days: int = Field(default=0,ge=0,le=90)

class MarketSelection(Strict):
    market_id: str = Field(min_length=1,max_length=100)
    transport_id: str | None = Field(default=None,max_length=100)
    storage_id: str | None = Field(default=None,max_length=100)

class MarketCompareIn(Strict):
    snapshot_id: str = Field(min_length=1,max_length=100)
    selections: list[MarketSelection] = Field(min_length=2,max_length=3)

class PreviewCompareIn(MarketCompareIn):
    crop: MarketContext
