"""Search provider interfaces used by the travel agent components."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Iterable, Mapping, Sequence


class SearchProvider(ABC):
    """Generic search provider interface."""

    @abstractmethod
    def search(self, query: str, *, filters: Mapping[str, object] | None = None) -> Sequence[Mapping[str, object]]:
        """Execute a generic search query.

        Implementations should call external services (e.g. search APIs or
        vendor specific endpoints) and return a normalized list of result
        dictionaries. Each dictionary should be serializable so the agent can
        store them in state or a vector database if required.
        """


class FlightSearchProvider(ABC):
    """Specialized interface for flight searches."""

    @abstractmethod
    def search_flights(self, *, origin: str, destination: str, departure_date: str, return_date: str | None,
                       travelers: int, cabin: str | None, max_stops: int | None,
                       loyalty_programs: Sequence[str]) -> Sequence[Mapping[str, object]]:
        """Return flight offers including cash and loyalty pricing."""


class HotelSearchProvider(ABC):
    """Specialized interface for hotel searches."""

    @abstractmethod
    def search_hotels(self, *, destination: str, check_in: str, check_out: str,
                      travelers: int, neighborhoods: Sequence[str], amenities: Sequence[str],
                      loyalty_programs: Sequence[str]) -> Sequence[Mapping[str, object]]:
        """Return hotel offers with flexible pricing options."""


class CompositeSearchProvider(SearchProvider, FlightSearchProvider, HotelSearchProvider):
    """Convenience class for providers implementing all search interfaces."""

    pass


class InMemorySearchProvider(CompositeSearchProvider):
    """Simple provider backed by an in-memory dataset.

    This is primarily intended for tests and local development. Production
    implementations should subclass the abstract base classes to connect to
    real APIs such as Amadeus, Skyscanner, Booking.com, or Google Hotels.
    """

    def __init__(self, *, generic_results: Sequence[Mapping[str, object]] | None = None,
                 flight_results: Sequence[Mapping[str, object]] | None = None,
                 hotel_results: Sequence[Mapping[str, object]] | None = None) -> None:
        self._generic = list(generic_results or [])
        self._flights = list(flight_results or [])
        self._hotels = list(hotel_results or [])

    def search(self, query: str, *, filters: Mapping[str, object] | None = None) -> Sequence[Mapping[str, object]]:
        del query, filters
        return tuple(self._generic)

    def search_flights(self, *, origin: str, destination: str, departure_date: str, return_date: str | None,
                       travelers: int, cabin: str | None, max_stops: int | None,
                       loyalty_programs: Sequence[str]) -> Sequence[Mapping[str, object]]:
        del origin, destination, departure_date, return_date, travelers, cabin, max_stops, loyalty_programs
        return tuple(self._flights)

    def search_hotels(self, *, destination: str, check_in: str, check_out: str,
                      travelers: int, neighborhoods: Sequence[str], amenities: Sequence[str],
                      loyalty_programs: Sequence[str]) -> Sequence[Mapping[str, object]]:
        del destination, check_in, check_out, travelers, neighborhoods, amenities, loyalty_programs
        return tuple(self._hotels)
