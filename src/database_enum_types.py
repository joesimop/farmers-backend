from enum import Enum

class TokenType(Enum):
    EBT = "EBT"
    MarketMatch = "MARKET_MATCH"
    ATM = "ATM"
    Custom = "CUSTOM"

class DaysOfWeek(Enum):
    Monday = "MONDAY"
    Tuesday = "TUESDAY"
    Wednesday = "WEDNESDAY"
    Thursday = "THURSDAY"
    Friday = "FRIDAY"
    Saturday = "SATURDAY"
    Sunday = "SUNDAY"

    def from_number(num):
        if num == 0:
            return DaysOfWeek.Monday
        elif num == 1:
            return DaysOfWeek.Tuesday
        elif num == 2:
            return DaysOfWeek.Wednesday
        elif num == 3:
            return DaysOfWeek.Thursday
        elif num == 4:
            return DaysOfWeek.Friday
        elif num == 5:
            return DaysOfWeek.Saturday
        elif num == 6:
            return DaysOfWeek.Sunday

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
