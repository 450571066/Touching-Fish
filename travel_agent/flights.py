"""Flight monitoring utilities."""

from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Callable, List, Mapping, Sequence

from models import FlightOffer, FlightPreference, TripRequest
from search import FlightSearchProvider


class FlightMonitor:
    """Search and monitor flights for a planned itinerary."""

    def __init__(self, provider: FlightSearchProvider) -> None:
        self._provider = provider

    def find_best_flights(self, request: TripRequest, preference: FlightPreference) -> List[FlightOffer]:
        """Return the best available flights based on preferences."""

        results = self._provider.search_flights(
            origin=request.origin,
            destination=request.destination,
            departure_date=request.start_date.isoformat(),
            return_date=request.end_date.isoformat(),
            travelers=request.travelers,
            cabin=preference.cabin,
            max_stops=preference.max_stops,
            loyalty_programs=preference.loyalty_programs,
        )
        return [self._normalize_offer(result) for result in results]

    async def monitor(
        self,
        request: TripRequest,
        preference: FlightPreference,
        *,
        interval_seconds: int = 3600,
        callback: Callable[[Sequence[FlightOffer]], None] | None = None,
        max_cycles: int | None = None,
    ) -> None:
        """Continuously poll the provider and invoke *callback* with new offers."""

        if not preference.alerts and max_cycles is None:
            return

        cycles = 0
        seen: set[str] = set()
        while preference.alerts or (max_cycles is not None and cycles < max_cycles):
            offers = self.find_best_flights(request, preference)
            fresh = [offer for offer in offers if offer.booking_url not in seen]
            for offer in fresh:
                seen.add(offer.booking_url)
            if fresh and callback:
                callback(tuple(fresh))
            cycles += 1
            if max_cycles is not None and cycles >= max_cycles:
                break
            await asyncio.sleep(interval_seconds)

    def _normalize_offer(self, raw: Mapping[str, object]) -> FlightOffer:
        return FlightOffer(
            price=float(raw.get("price", 0.0)),
            currency=str(raw.get("currency", "USD")),
            departure_time=self._parse_datetime(raw.get("departure_time")),
            arrival_time=self._parse_datetime(raw.get("arrival_time")),
            airline=str(raw.get("airline", "")),
            flight_number=str(raw.get("flight_number", "")),
            booking_url=str(raw.get("booking_url", "")),
            loyalty_cost=self._maybe_int(raw.get("loyalty_cost")),
            loyalty_program=raw.get("loyalty_program"),
        )

    @staticmethod
    def _parse_datetime(value: object) -> datetime:
        if isinstance(value, datetime):
            return value
        if isinstance(value, str):
            return datetime.fromisoformat(value)
        raise ValueError(f"Unsupported datetime value: {value!r}")

    @staticmethod
    def _maybe_int(value: object) -> int | None:
        if value is None:
            return None
        return int(value)
