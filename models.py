"""
models.py - The Data Fortress

Pydantic models that validate ALL lottery data at the extraction boundary.
If any number is malformed, the run ABORTS before bad data enters the registry.
"""

from pydantic import BaseModel, Field, field_validator, model_validator
from decimal import Decimal, InvalidOperation
from typing import Optional
import re


class Prize(BaseModel):
    """A single prize row from the lottery website."""
    
    value: Decimal = Field(description="Prize value in dollars (parsed from '$1,000,000')")
    odds: Decimal = Field(description="Odds denominator (parsed from '1 in 1,469,394')")
    total: int = Field(ge=0, description="Total remaining prizes")
    
    # Keep original strings for audit trail
    raw_value: str = Field(description="Original value string from HTML")
    raw_odds: str = Field(description="Original odds string from HTML")
    raw_total: str = Field(description="Original total string from HTML")
    
    @field_validator('value', mode='before')
    @classmethod
    def parse_currency(cls, v):
        """Convert '$1,000,000' to Decimal 1000000"""
        if isinstance(v, (int, float, Decimal)):
            return Decimal(str(v))
        if isinstance(v, str):
            # Remove $, commas, and whitespace
            cleaned = v.replace('$', '').replace(',', '').strip()
            if not cleaned:
                raise ValueError(f"Empty currency value: '{v}'")
            try:
                return Decimal(cleaned)
            except InvalidOperation:
                raise ValueError(f"Cannot parse currency: '{v}'")
        raise ValueError(f"Unexpected type for currency: {type(v)}")
    
    @field_validator('odds', mode='before')
    @classmethod
    def parse_odds(cls, v):
        """Convert '1,469,394' or '1 in 1,469,394' to Decimal"""
        if isinstance(v, (int, float, Decimal)):
            return Decimal(str(v))
        if isinstance(v, str):
            # Remove "1 in " prefix if present
            cleaned = v.replace('1 in ', '').replace(',', '').strip()
            if not cleaned:
                raise ValueError(f"Empty odds value: '{v}'")
            try:
                return Decimal(cleaned)
            except InvalidOperation:
                raise ValueError(f"Cannot parse odds: '{v}'")
        raise ValueError(f"Unexpected type for odds: {type(v)}")
    
    @field_validator('total', mode='before')
    @classmethod
    def parse_total(cls, v):
        """Convert '2,448' to int 2448"""
        if isinstance(v, int):
            return v
        if isinstance(v, str):
            cleaned = v.replace(',', '').strip()
            if not cleaned:
                raise ValueError(f"Empty total value: '{v}'")
            try:
                return int(cleaned)
            except ValueError:
                raise ValueError(f"Cannot parse total as integer: '{v}'")
        raise ValueError(f"Unexpected type for total: {type(v)}")


class GameRaw(BaseModel):
    """A game as extracted from the lottery website (before GUID assignment)."""
    
    game_id: str = Field(min_length=1, description="Game number (e.g., '996')")
    game_name: str = Field(min_length=1, description="Display name of the game")
    url_slug: str = Field(default="unknown", description="URL-friendly slug")
    prizes: list[Prize] = Field(min_length=1, description="Prize breakdown table")
    
    # Derived field for quick access
    ticket_price: Optional[str] = Field(default=None, description="Ticket price if known")
    
    @field_validator('game_id', mode='before')
    @classmethod
    def validate_game_id(cls, v):
        """Ensure game_id is numeric string"""
        if not v:
            raise ValueError("game_id cannot be empty")
        cleaned = str(v).strip()
        if not cleaned.isdigit():
            raise ValueError(f"game_id must be numeric: '{v}'")
        return cleaned
    
    @model_validator(mode='after')
    def validate_prizes_order(self):
        """Sanity check: prizes should generally be in descending value order"""
        if len(self.prizes) >= 2:
            # Log warning if first prize isn't the highest (common pattern)
            if self.prizes[0].value < self.prizes[1].value:
                # This is unusual but not necessarily wrong
                pass  # Could add logging here
        return self
    
    def total_remaining_value(self) -> Decimal:
        """Calculate total prize money remaining for this game."""
        return sum(p.value * p.total for p in self.prizes)


class SensorOutput(BaseModel):
    """Complete output from a sensor run - validates the entire extraction."""
    
    run_id: str = Field(min_length=1, description="Unique run identifier")
    games: list[GameRaw] = Field(min_length=1, description="All extracted games")
    html_path: str = Field(description="Path to saved HTML evidence")
    html_size_kb: float = Field(ge=0, description="Size of captured HTML")
    screenshot_path: str = Field(description="Path to screenshot evidence")
    
    def total_games(self) -> int:
        return len(self.games)
    
    def total_universe_value(self) -> Decimal:
        """Sum of all remaining prize money across all games."""
        return sum(g.total_remaining_value() for g in self.games)


# Helper function for sensor.py
def validate_extracted_prize(value: str, odds: str, total: str) -> Prize:
    """
    Create and validate a Prize from raw strings.
    Raises ValidationError if anything is malformed.
    """
    return Prize(
        value=value,
        odds=odds, 
        total=total,
        raw_value=value,
        raw_odds=odds,
        raw_total=total
    )


def validate_extracted_game(game_id: str, game_name: str, url_slug: str, prizes: list[dict]) -> GameRaw:
    """
    Create and validate a GameRaw from extracted data.
    Raises ValidationError if anything is malformed.
    """
    validated_prizes = [
        validate_extracted_prize(p['value'], p['odds'], p['total'])
        for p in prizes
    ]
    return GameRaw(
        game_id=game_id,
        game_name=game_name,
        url_slug=url_slug,
        prizes=validated_prizes
    )
