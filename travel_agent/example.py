"""Example usage of the travel agent components."""

from __future__ import annotations

import asyncio
from datetime import date, datetime, timedelta
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
import json
import os
import threading
from typing import Callable, Mapping

from agent import TravelAgent
from models import FlightPreference, HotelPreference, TripRequest
from providers import AmadeusConfig, AmadeusSearchProvider, ProviderError
from search import InMemorySearchProvider


async def main() -> None:
    provider, cleanup = _build_provider()
    agent = TravelAgent.from_provider(provider)

    trip = TripRequest(
        origin="HKG",
        destination="BJS",
        start_date=date.today(),
        end_date=date.today() + timedelta(days=3),
        interests=("文化景点", "当地美食"),
        travelers=2,
        origin_display="Hong Kong",
        destination_display="Beijing",
    )

    itinerary = agent.plan_itinerary(trip)
    flights = agent.find_flights(trip, FlightPreference(cabin="business", loyalty_programs=("PhoenixMiles",)))
    hotels = agent.find_hotels(trip, HotelPreference(neighborhoods=("Chaoyang",)))

    print("Itinerary notes:", itinerary.notes)
    print("Flights:", flights)
    print("Hotels:", hotels)

    try:
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
    finally:
        if cleanup:
            cleanup()


def _build_provider() -> tuple[InMemorySearchProvider | AmadeusSearchProvider, Callable[[], None] | None]:
    """Prefer a live Amadeus provider when a local config file is available."""

    if os.getenv("TRAVEL_AGENT_EXAMPLE_STUB"):
        stub = _StubAmadeusServer()
        stub.start()
        config = AmadeusConfig(
            client_id="stub",
            client_secret="stub",
            hostname=stub.base_url,
            timeout=5.0,
        )
        return AmadeusSearchProvider(config), stub.stop

    config_path = Path(__file__).with_name("amadeus_config.json")
    if config_path.exists():
        try:
            config = AmadeusConfig.from_file(config_path)
            return AmadeusSearchProvider(config), None
        except (ProviderError, ValueError) as exc:  # pragma: no cover - demo fallback path
            print(f"Failed to initialize Amadeus provider: {exc}")

    return InMemorySearchProvider(
        generic_results=[
            {
                "title": "Day trip to the Great Wall",
                "snippet": "Book a private driver to Mutianyu for breathtaking views.",
                "location": "Great Wall, Beijing",
                "start_time": datetime.now().isoformat(),
                "end_time": (datetime.now() + timedelta(hours=6)).isoformat(),
                "url": "https://www.thechinaguide.com/destination/mutianyu-great-wall",
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
                "booking_url": "https://www.airchina.com.cn/en",
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
                "booking_url": "https://www.marriott.com/en-us/hotels/bjsbr-the-st-regis-beijing/overview/",
                "loyalty_cost": 28000,
                "loyalty_program": "Marriott Bonvoy",
            }
        ],
    ), None


class _StubAmadeusServer:
    """Serve canned Amadeus responses for environments without internet access."""

    def __init__(self) -> None:
        self._server = HTTPServer(("127.0.0.1", 0), _StubAmadeusHandler)
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)

    @property
    def base_url(self) -> str:
        host, port = self._server.server_address
        return f"http://{host}:{port}"

    def start(self) -> None:
        self._thread.start()

    def stop(self) -> None:
        self._server.shutdown()
        self._thread.join()


class _StubAmadeusHandler(BaseHTTPRequestHandler):
    """HTTP handler that mimics a subset of the Amadeus API."""

    _TOKEN_RESPONSE = {"access_token": "stub-token", "expires_in": 1800}
    _FLIGHT_RESPONSE = {
        "data": [
            {
                "itineraries": [
                    {
                        "segments": [
                            {
                                "departure": {"at": datetime.now().isoformat(timespec="seconds")},
                                "arrival": {"at": (datetime.now() + timedelta(hours=3)).isoformat(timespec="seconds")},
                                "carrierCode": "ST",
                                "number": "123",
                            }
                        ]
                    }
                ],
                "price": {"total": "199.99", "currency": "USD"},
                "links": {"deeplink": "/bookings/flight/abc"},
                "travelerPricings": [
                    {
                        "loyaltyProgramme": {
                            "program": "Sample Rewards",
                            "points": 15000,
                        }
                    }
                ],
            }
        ]
    }
    _HOTEL_RESPONSE = {
        "data": [
            {
                "hotel": {
                    "name": "Stub Plaza",
                    "rating": 4.5,
                    "geoCode": {"latitude": 39.9042, "longitude": 116.4074},
                },
                "offers": [
                    {
                        "price": {"total": "289.50", "currency": "USD"},
                        "boardType": "Breakfast",
                        "room": {"description": {"text": "City view suite"}},
                        "loyaltyProgramme": {
                            "program": "Stub Rewards",
                            "points": 22000,
                        },
                        "links": {"deeplink": "/bookings/hotel/xyz"},
                    }
                ],
            }
        ]
    }
    _LOCATION_RESPONSE = {
        "data": [
            {
                "type": "location",
                "subType": "CITY",
                "name": "Stub City",
                "iataCode": "STB",
            }
        ]
    }

    def do_POST(self) -> None:  # noqa: N802 - required by BaseHTTPRequestHandler
        if self.path == "/v1/security/oauth2/token":
            self._send_json(self._TOKEN_RESPONSE)
        else:
            self.send_error(404, "Unknown endpoint")

    def do_GET(self) -> None:  # noqa: N802 - required by BaseHTTPRequestHandler
        if self.path.startswith("/v2/shopping/flight-offers"):
            self._send_json(self._FLIGHT_RESPONSE)
        elif self.path.startswith("/v2/shopping/hotel-offers"):
            self._send_json(self._HOTEL_RESPONSE)
        elif self.path.startswith("/v1/reference-data/locations"):
            self._send_json(self._LOCATION_RESPONSE)
        elif self.path.startswith("/bookings/"):
            self._send_json({"status": "ok", "path": self.path})
        else:
            self.send_error(404, "Unknown endpoint")

    def log_message(self, format: str, *args: object) -> None:  # noqa: A003 - signature defined by base class
        # Silence default logging to keep example output focused.
        return

    def _send_json(self, payload: Mapping[str, object]) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


if __name__ == "__main__":
    asyncio.run(main())
