from enum import Enum

class TokenType(Enum):
    EBT = "EBT"
    MarketMatch = "MARKET_MATCH"
    ATM = "ATM"
    Custom = "CUSTOM"

class FeeType(Enum):
    PercentGross = "PERCENT_GROSS"
    FlatFee = "FLAT_FEE"
    FlatPercentCombo = "FLAT_PERCENT_COMBO"
    MaxOfEither = "MAX_OF_EITHER"
    GovFee = "GOV_FEE"

class VendorType(Enum):
    Procducer = "PRODUCER"
    NonProducer = "NON_PRODUCER"
    Ancillary = "ANCILLARY"

class DocumentType(Enum):
    CPCCert = "CPC_CERT"
    LiabilityCert = "LIABILITY_CERT"
    LoadList = "LOAD_LIST"
