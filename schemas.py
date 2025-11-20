"""
Database Schemas for the TAA MVP

Each Pydantic model corresponds to a MongoDB collection where the
collection name is the lowercase of the class name.
"""
from typing import List, Optional
from pydantic import BaseModel, Field


class Scenario(BaseModel):
    """
    Stress test scenarios created by users
    Collection: "scenario"
    """
    name: str = Field(..., description="Scenario title, e.g., '10y to 6%'")
    description: Optional[str] = Field(None, description="Detailed scenario description")
    assumptions: dict = Field(default_factory=dict, description="Key/value assumptions, e.g., {'us10y': 6.0}")
    created_by: Optional[str] = Field(None, description="User id or email")


class PortfolioHolding(BaseModel):
    symbol: str = Field(..., description="Ticker, e.g., SPY")
    weight: float = Field(..., ge=0.0, le=1.0, description="Weight as 0-1")


class Portfolio(BaseModel):
    """
    Shadow portfolios uploaded by users
    Collection: "portfolio"
    """
    name: str = Field(..., description="Portfolio name")
    owner: Optional[str] = Field(None, description="User id or email")
    holdings: List[PortfolioHolding] = Field(default_factory=list)


class BacktestRun(BaseModel):
    """
    Stores backtest requests to reproduce later
    Collection: "backtestrun"
    """
    start: str = Field(..., description="YYYY-MM-DD")
    end: str = Field(..., description="YYYY-MM-DD")
    benchmark: str = Field("60_40", description="Benchmark key")
    notes: Optional[str] = None
