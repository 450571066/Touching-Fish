"""High level façade that combines itinerary, flight, and hotel workflows."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Sequence

from flights import FlightMonitor
from hotels import HotelMonitor
from itinerary import ItineraryPlanner
from models import (
    FlightOffer,
    FlightPreference,
    HotelOffer,
    HotelPreference,
    Itinerary,
    TripRequest,
)
from search import CompositeSearchProvider


@dataclass(slots=True)
class TravelAgent:
    """Orchestrates itinerary planning and monitoring."""

    planner: ItineraryPlanner
    flight_monitor: FlightMonitor
    hotel_monitor: HotelMonitor

    @classmethod
    def from_provider(cls, provider: CompositeSearchProvider) -> "TravelAgent":
        """Create a travel agent that uses a unified search provider."""

        planner = ItineraryPlanner(provider)
        flight_monitor = FlightMonitor(provider)
        hotel_monitor = HotelMonitor(provider)
        return cls(planner=planner, flight_monitor=flight_monitor, hotel_monitor=hotel_monitor)

    def plan_itinerary(self, request: TripRequest) -> Itinerary:
        return self.planner.plan_trip(request)

    def find_flights(self, request: TripRequest, preference: FlightPreference) -> Sequence[FlightOffer]:
        return self.flight_monitor.find_best_flights(request, preference)

    def find_hotels(self, request: TripRequest, preference: HotelPreference) -> Sequence[HotelOffer]:
        return self.hotel_monitor.find_best_hotels(request, preference)

    async def monitor_flights(
        self,
        request: TripRequest,
        preference: FlightPreference,
        *,
        interval_seconds: int = 3600,
        callback: Callable[[Sequence[FlightOffer]], None] | None = None,
        max_cycles: int | None = None,
    ) -> None:
        await self.flight_monitor.monitor(
            request,
            preference,
            interval_seconds=interval_seconds,
            callback=callback,
            max_cycles=max_cycles,
        )

    async def monitor_hotels(
        self,
        request: TripRequest,
        preference: HotelPreference,
        *,
        interval_seconds: int = 3600,
        callback: Callable[[Sequence[HotelOffer]], None] | None = None,
        max_cycles: int | None = None,
    ) -> None:
        await self.hotel_monitor.monitor(
            request,
            preference,
            interval_seconds=interval_seconds,
            callback=callback,
            max_cycles=max_cycles,
        )
