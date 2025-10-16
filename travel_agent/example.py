"""Example usage of the travel agent components."""

from __future__ import annotations

import asyncio
import os
from datetime import date, datetime, timedelta

from .agent import TravelAgent
from .models import FlightPreference, HotelPreference, TripRequest
from .providers import AmadeusConfig, AmadeusSearchProvider, ProviderError
from .search import InMemorySearchProvider


async def main() -> None:
    provider = _build_provider()
    agent = TravelAgent.from_provider(provider)

    trip = TripRequest(
        origin="HKG",
        destination="Beijing",
        start_date=date.today(),
        end_date=date.today() + timedelta(days=3),
        interests=("文化景点", "当地美食"),
        travelers=2,
    )

    itinerary = agent.plan_itinerary(trip)
    flights = agent.find_flights(trip, FlightPreference(cabin="business", loyalty_programs=("PhoenixMiles",)))
    hotels = agent.find_hotels(trip, HotelPreference(neighborhoods=("Chaoyang",)))

    print("Itinerary notes:", itinerary.notes)
    print("Flights:", flights)
    print("Hotels:", hotels)

    await asyncio.gather(
        agent.monitor_flights(
            trip,
            FlightPreference(alerts=True),
            interval_seconds=1,
            callback=lambda offers: print("Flight update", offers),
            max_cycles=1,
        ),
        agent.monitor_hotels(
            trip,
            HotelPreference(alerts=True),
            interval_seconds=1,
            callback=lambda offers: print("Hotel update", offers),
            max_cycles=1,
        ),
    )


def _build_provider() -> InMemorySearchProvider | AmadeusSearchProvider:
    """Prefer a live Amadeus provider when credentials are present."""

    client_id = os.getenv("AMADEUS_CLIENT_ID")
    client_secret = os.getenv("AMADEUS_CLIENT_SECRET")
    if client_id and client_secret:
        try:
            return AmadeusSearchProvider(AmadeusConfig(client_id=client_id, client_secret=client_secret))
        except ProviderError as exc:  # pragma: no cover - demo fallback path
            print(f"Failed to initialize Amadeus provider: {exc}")

    return InMemorySearchProvider(
        generic_results=[
            {
                "title": "Day trip to the Great Wall",
                "snippet": "Book a private driver to Mutianyu for breathtaking views.",
                "location": "Great Wall, Beijing",
                "start_time": datetime.now().isoformat(),
                "end_time": (datetime.now() + timedelta(hours=6)).isoformat(),
                "url": "https://example.com/great-wall",
            }
        ],
        flight_results=[
            {
                "price": 3200,
                "currency": "CNY",
                "departure_time": datetime.now().isoformat(),
                "arrival_time": (datetime.now() + timedelta(hours=3)).isoformat(),
                "airline": "Air China",
                "flight_number": "CA123",
                "booking_url": "https://example.com/ca123",
                "loyalty_cost": 18000,
                "loyalty_program": "Air China PhoenixMiles",
            }
        ],
        hotel_results=[
            {
                "name": "Grand Beijing Hotel",
                "price_per_night": 980,
                "currency": "CNY",
                "check_in": date.today().isoformat(),
                "check_out": (date.today() + timedelta(days=3)).isoformat(),
                "rating": 4.6,
                "location": "Chaoyang District",
                "booking_url": "https://example.com/grand-beijing",
                "loyalty_cost": 28000,
                "loyalty_program": "Marriott Bonvoy",
            }
        ],
    )


if __name__ == "__main__":
    asyncio.run(main())
