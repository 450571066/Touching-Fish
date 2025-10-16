"""Hotel monitoring utilities."""

from __future__ import annotations

import asyncio
from datetime import date
from typing import Callable, List, Mapping, Sequence

from .models import HotelOffer, HotelPreference, TripRequest
from .search import HotelSearchProvider


class HotelMonitor:
    """Search and monitor hotels for a planned itinerary."""

    def __init__(self, provider: HotelSearchProvider) -> None:
        self._provider = provider

    def find_best_hotels(self, request: TripRequest, preference: HotelPreference) -> List[HotelOffer]:
        results = self._provider.search_hotels(
            destination=request.destination,
            check_in=request.start_date.isoformat(),
            check_out=request.end_date.isoformat(),
            travelers=request.travelers,
            neighborhoods=preference.neighborhoods,
            amenities=preference.amenities,
            loyalty_programs=preference.loyalty_programs,
        )
        return [self._normalize_offer(result) for result in results]

    async def monitor(
        self,
        request: TripRequest,
        preference: HotelPreference,
        *,
        interval_seconds: int = 3600,
        callback: Callable[[Sequence[HotelOffer]], None] | None = None,
        max_cycles: int | None = None,
    ) -> None:
        if not preference.alerts and max_cycles is None:
            return

        cycles = 0
        seen: set[str] = set()
        while preference.alerts or (max_cycles is not None and cycles < max_cycles):
            offers = self.find_best_hotels(request, preference)
            fresh = [offer for offer in offers if offer.booking_url not in seen]
            for offer in fresh:
                seen.add(offer.booking_url)
            if fresh and callback:
                callback(tuple(fresh))
            cycles += 1
            if max_cycles is not None and cycles >= max_cycles:
                break
            await asyncio.sleep(interval_seconds)

    def _normalize_offer(self, raw: Mapping[str, object]) -> HotelOffer:
        return HotelOffer(
            name=str(raw.get("name", "")),
            price_per_night=float(raw.get("price_per_night", 0.0)),
            currency=str(raw.get("currency", "USD")),
            check_in=self._parse_date(raw.get("check_in")),
            check_out=self._parse_date(raw.get("check_out")),
            rating=self._maybe_float(raw.get("rating")),
            location=raw.get("location"),
            booking_url=str(raw.get("booking_url", "")),
            loyalty_cost=self._maybe_int(raw.get("loyalty_cost")),
            loyalty_program=raw.get("loyalty_program"),
            notes=tuple(raw.get("notes", ()) or ()),
        )

    @staticmethod
    def _parse_date(value: object) -> date:
        if isinstance(value, date):
            return value
        if isinstance(value, str):
            return date.fromisoformat(value)
        raise ValueError(f"Unsupported date value: {value!r}")

    @staticmethod
    def _maybe_float(value: object) -> float | None:
        if value is None:
            return None
        return float(value)

    @staticmethod
    def _maybe_int(value: object) -> int | None:
        if value is None:
            return None
        return int(value)
