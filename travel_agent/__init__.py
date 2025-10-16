"""Travel agent package for itinerary planning and monitoring.

This module exposes the primary entrypoints for consumers who want to
instantiate the agent components individually or use the combined
`TravelAgent` façade.
"""

from .agent import TravelAgent
from .itinerary import ItineraryPlanner
from .flights import FlightMonitor
from .hotels import HotelMonitor
from .providers import (
    AmadeusConfig,
    AmadeusFlightSearchProvider,
    AmadeusHotelSearchProvider,
    AmadeusSearchProvider,
    ProviderError,
)
from .models import (
    Activity,
    FlightOffer,
    FlightPreference,
    HotelOffer,
    HotelPreference,
    Itinerary,
    ItineraryDay,
    TripRequest,
)

__all__ = [
    "TravelAgent",
    "ItineraryPlanner",
    "FlightMonitor",
    "HotelMonitor",
    "Activity",
    "FlightOffer",
    "FlightPreference",
    "HotelOffer",
    "HotelPreference",
    "Itinerary",
    "ItineraryDay",
    "TripRequest",
    "AmadeusConfig",
    "AmadeusFlightSearchProvider",
    "AmadeusHotelSearchProvider",
    "AmadeusSearchProvider",
    "ProviderError",
]
