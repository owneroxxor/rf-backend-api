from enum import Enum


class MARKET_TYPE(Enum):
    BOX = 'box'
    FORWARD = 'forward'
    FUTURE = 'future'
    OPTIONS = 'options'
    SWAP = 'swap'
    FIXED_INCOME = 'fixed-income'
    COE = 'coe'
    EQUITIES = 'equities'
    ETF = 'etf'
    INTERNATIONAL_ETF = 'international-etf'
    INVESTMENT_FUNDS = 'investment-funds'
    SECURITIES_LENDING = 'securities-lending'
    TRASURY_BONDS = 'treasury-bonds'
