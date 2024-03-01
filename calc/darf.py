from re import S
from typing import List
from app.models import User, Movements, Movement
from app.api.routers.b3_router import get_movements
import pandas as pd

class Darf:
    """Darf class."""
    def __init__(
        self,
        markets: List[str],
        year: int,
        month: int,
        user: User
    ):
        self.markets: List[str] = markets
        self.year: int = year
        self.month: int = month
        self.user: User = user
    
    @property
    def start_date(self) -> str:
        return f'{self.year}-{self.month}-01'
    
    @property
    def end_date(self) -> str:
        return str(pd.Period(self.start_date, freq='M').end_time.date())
    
    async def calculate(self):
        for market in self.markets:
            mvmts: Movements = await get_movements(self.user, market_type=market, start_date=self.start_date, end_date=self.end_date)
            getattr(self, f'_calculate_{market}')(movements=mvmts.movements)

    def _calculate_equities(self, mvmts: List[Movement]):
        



#---------------- helpers ----------------
async def generate_darf(
    markets: List[str],
    year: int,
    month: int,
    user: User
):
    darf = Darf(markets=markets, year=year, month=month, user=user)
    await darf.calculate()
    return darf.export()