"""Data models shared across the travel agent components."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Callable, Iterable, List, Optional, Sequence


@dataclass(slots=True)
class TripRequest:
    """A high level description of the trip the user wants to take."""

    origin: str
    destination: str
    start_date: date
    end_date: date
    interests: Sequence[str] = field(default_factory=tuple)
    travelers: int = 1
    budget: Optional[float] = None
    origin_display: Optional[str] = None
    destination_display: Optional[str] = None

    @property
    def origin_label(self) -> str:
        """Return a human-friendly label for the origin city or airport."""

        return self.origin_display or self.origin

    @property
    def destination_label(self) -> str:
        """Return a human-friendly label for the destination city or airport."""

        return self.destination_display or self.destination


@dataclass(slots=True)
class Activity:
    """An activity planned for a given portion of the trip."""

    name: str
    description: str
    location: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    booking_url: Optional[str] = None


@dataclass(slots=True)
class ItineraryDay:
    """Activities planned for a single day."""

    date: date
    activities: List[Activity] = field(default_factory=list)


@dataclass(slots=True)
class Itinerary:
    """Full itinerary for the trip."""

    request: TripRequest
    days: List[ItineraryDay]
    notes: List[str] = field(default_factory=list)


@dataclass(slots=True)
class FlightPreference:
    """User preferences for selecting flights."""

    cabin: Optional[str] = None
    max_stops: Optional[int] = None
    preferred_airlines: Sequence[str] = field(default_factory=tuple)
    loyalty_programs: Sequence[str] = field(default_factory=tuple)
    max_price: Optional[float] = None
    alerts: bool = True


@dataclass(slots=True)
class FlightOffer:
    """A concrete flight option returned by a search provider."""

    price: float
    currency: str
    departure_time: datetime
    arrival_time: datetime
    airline: str
    flight_number: str
    booking_url: str
    loyalty_cost: Optional[int] = None
    loyalty_program: Optional[str] = None


@dataclass(slots=True)
class HotelPreference:
    """Preferences for selecting hotels."""

    neighborhoods: Sequence[str] = field(default_factory=tuple)
    loyalty_programs: Sequence[str] = field(default_factory=tuple)
    min_rating: Optional[float] = None
    max_price_per_night: Optional[float] = None
    room_type: Optional[str] = None
    amenities: Sequence[str] = field(default_factory=tuple)
    alerts: bool = True


@dataclass(slots=True)
class HotelOffer:
    """A concrete hotel option returned by a search provider."""

    name: str
    price_per_night: float
    currency: str
    check_in: date
    check_out: date
    rating: Optional[float]
    location: Optional[str]
    booking_url: str
    loyalty_cost: Optional[int] = None
    loyalty_program: Optional[str] = None
    notes: Sequence[str] = field(default_factory=tuple)


Callback = Callable[[Iterable[object]], None]
"""Type alias for monitor callbacks."""
