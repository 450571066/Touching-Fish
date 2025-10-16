"""Concrete search provider integrations for external travel APIs."""

from __future__ import annotations

import os
import time
from dataclasses import dataclass
from typing import Iterable, Mapping, MutableMapping, Sequence

import requests

from .search import CompositeSearchProvider, FlightSearchProvider, HotelSearchProvider


class ProviderError(RuntimeError):
    """Raised when an upstream provider returns an unexpected response."""


@dataclass(slots=True)
class AmadeusConfig:
    """Configuration required to authenticate with the Amadeus travel APIs."""

    client_id: str
    client_secret: str
    hostname: str = "https://test.api.amadeus.com"
    timeout: float = 10.0

    @classmethod
    def from_env(cls, *, prefix: str = "AMADEUS_") -> "AmadeusConfig":
        """Build a configuration by reading credentials from environment variables.

        Parameters
        ----------
        prefix:
            Optional prefix that will be prepended to the environment variable
            names. By default, the method expects ``AMADEUS_CLIENT_ID`` and
            ``AMADEUS_CLIENT_SECRET`` to be available in the process
            environment. ``AMADEUS_HOSTNAME`` and ``AMADEUS_TIMEOUT`` can also
            be provided to override the default endpoint and timeout.

        Raises
        ------
        ValueError
            If either the client ID or client secret is missing.
        """

        client_id = os.getenv(f"{prefix}CLIENT_ID")
        client_secret = os.getenv(f"{prefix}CLIENT_SECRET")
        missing: list[str] = []
        if not client_id:
            missing.append(f"{prefix}CLIENT_ID")
        if not client_secret:
            missing.append(f"{prefix}CLIENT_SECRET")
        if missing:
            raise ValueError(
                "Missing required Amadeus credentials in environment: "
                + ", ".join(missing)
            )

        hostname = os.getenv(f"{prefix}HOSTNAME") or "https://test.api.amadeus.com"
        timeout_value = os.getenv(f"{prefix}TIMEOUT")
        timeout = float(timeout_value) if timeout_value is not None else 10.0

        return cls(client_id=client_id, client_secret=client_secret, hostname=hostname, timeout=timeout)


class _AmadeusClient:
    """Light-weight helper for handling Amadeus authentication and requests."""

    def __init__(self, config: AmadeusConfig, *, session: requests.Session | None = None) -> None:
        self._config = config
        self._session = session or requests.Session()
        self._token: str | None = None
        self._token_expiry: float = 0.0

    def get(self, path: str, *, params: Mapping[str, object] | None = None) -> Mapping[str, object]:
        return self._request("GET", path, params=params)

    def _request(
        self,
        method: str,
        path: str,
        *,
        params: Mapping[str, object] | None = None,
        retry: bool = True,
    ) -> Mapping[str, object]:
        token = self._ensure_token()
        url = f"{self._config.hostname}{path}"
        headers = {"Authorization": f"Bearer {token}"}
        response = self._session.request(
            method,
            url,
            params={k: v for k, v in (params or {}).items() if v not in (None, "")},
            headers=headers,
            timeout=self._config.timeout,
        )
        if response.status_code == 401 and retry:
            # Token likely expired – refresh and retry once.
            self._token = None
            self._token_expiry = 0.0
            return self._request(method, path, params=params, retry=False)
        response.raise_for_status()
        data = response.json()
        if not isinstance(data, MutableMapping):
            raise ProviderError(f"Unexpected response payload from Amadeus: {data!r}")
        return data

    def _ensure_token(self) -> str:
        now = time.time()
        if self._token and now < self._token_expiry:
            return self._token
        response = self._session.post(
            f"{self._config.hostname}/v1/security/oauth2/token",
            data={
                "grant_type": "client_credentials",
                "client_id": self._config.client_id,
                "client_secret": self._config.client_secret,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=self._config.timeout,
        )
        response.raise_for_status()
        payload = response.json()
        token = payload.get("access_token")
        expires_in = float(payload.get("expires_in", 1800))
        if not token:
            raise ProviderError(f"Unable to obtain Amadeus access token: {payload!r}")
        self._token = str(token)
        # Refresh the token slightly before it expires to avoid race conditions.
        self._token_expiry = now + max(expires_in - 60, 0)
        return self._token


class AmadeusFlightSearchProvider(FlightSearchProvider):
    """Implementation of :class:`FlightSearchProvider` backed by Amadeus APIs."""

    def __init__(
        self,
        config: AmadeusConfig | None = None,
        *,
        session: requests.Session | None = None,
        client: _AmadeusClient | None = None,
    ) -> None:
        if client is not None:
            self._client = client
        elif config is not None:
            self._client = _AmadeusClient(config, session=session)
        else:  # pragma: no cover - defensive branch
            raise ValueError("Either config or client must be provided")

    def search_flights(
        self,
        *,
        origin: str,
        destination: str,
        departure_date: str,
        return_date: str | None,
        travelers: int,
        cabin: str | None,
        max_stops: int | None,
        loyalty_programs: Sequence[str],
    ) -> Sequence[Mapping[str, object]]:
        params: dict[str, object] = {
            "originLocationCode": origin,
            "destinationLocationCode": destination,
            "departureDate": departure_date,
            "adults": travelers,
            "currencyCode": "USD",
        }
        if return_date:
            params["returnDate"] = return_date
        if cabin:
            params["travelClass"] = cabin.upper()
        if max_stops is not None:
            params["max"] = max_stops
        if loyalty_programs:
            params["includedAirlineCodes"] = ",".join(sorted(loyalty_programs))

        response = self._client.get("/v2/shopping/flight-offers", params=params)
        data = response.get("data", [])
        results: list[Mapping[str, object]] = []
        if not isinstance(data, Iterable):
            return results
        for offer in data:
            if not isinstance(offer, MutableMapping):
                continue
            itineraries = offer.get("itineraries") or []
            if not itineraries:
                continue
            first_itinerary = itineraries[0]
            segments = first_itinerary.get("segments") or []
            if not segments:
                continue
            first_segment = segments[0]
            departure = (first_segment.get("departure") or {}).get("at")
            arrival = (first_segment.get("arrival") or {}).get("at")
            carrier = first_segment.get("carrierCode", "")
            number = first_segment.get("number", "")
            price = (offer.get("price") or {}).get("total")
            currency = (offer.get("price") or {}).get("currency")
            links = offer.get("links") or {}
            booking_url = links.get("self") or f"https://www.amadeus.com/travel/{offer.get('id', '')}"

            traveler_pricing = offer.get("travelerPricings") or []
            loyalty_cost = None
            loyalty_program = None
            if traveler_pricing:
                loyalty_program = (
                    (traveler_pricing[0].get("loyaltyProgramme") or {})
                    if isinstance(traveler_pricing[0], MutableMapping)
                    else None
                )
                if isinstance(loyalty_program, MutableMapping):
                    loyalty_cost = loyalty_program.get("points")
                    loyalty_program = loyalty_program.get("program")

            results.append(
                {
                    "price": float(price) if price is not None else 0.0,
                    "currency": currency or "USD",
                    "departure_time": departure,
                    "arrival_time": arrival,
                    "airline": carrier,
                    "flight_number": f"{carrier}{number}".strip(),
                    "booking_url": booking_url,
                    "loyalty_cost": loyalty_cost,
                    "loyalty_program": loyalty_program,
                }
            )
        return tuple(results)


class AmadeusHotelSearchProvider(HotelSearchProvider):
    """Implementation of :class:`HotelSearchProvider` backed by Amadeus APIs."""

    def __init__(
        self,
        config: AmadeusConfig | None = None,
        *,
        session: requests.Session | None = None,
        client: _AmadeusClient | None = None,
    ) -> None:
        if client is not None:
            self._client = client
        elif config is not None:
            self._client = _AmadeusClient(config, session=session)
        else:  # pragma: no cover - defensive branch
            raise ValueError("Either config or client must be provided")

    def search_hotels(
        self,
        *,
        destination: str,
        check_in: str,
        check_out: str,
        travelers: int,
        neighborhoods: Sequence[str],
        amenities: Sequence[str],
        loyalty_programs: Sequence[str],
    ) -> Sequence[Mapping[str, object]]:
        params: dict[str, object] = {
            "cityCode": destination,
            "checkInDate": check_in,
            "checkOutDate": check_out,
            "adults": travelers,
            "roomQuantity": 1,
            "view": "FULL",
        }
        if neighborhoods:
            params["hotelIds"] = ",".join(sorted(neighborhoods))
        if amenities:
            params["amenities"] = ",".join(sorted(amenities))
        if loyalty_programs:
            params["loyaltyProgrammes"] = ",".join(sorted(loyalty_programs))

        response = self._client.get("/v2/shopping/hotel-offers", params=params)
        data = response.get("data", [])
        results: list[Mapping[str, object]] = []
        if not isinstance(data, Iterable):
            return results
        for entry in data:
            if not isinstance(entry, MutableMapping):
                continue
            hotel = entry.get("hotel") or {}
            offers = entry.get("offers") or []
            if not offers:
                continue
            for offer in offers:
                if not isinstance(offer, MutableMapping):
                    continue
                price = (offer.get("price") or {}).get("total")
                currency = (offer.get("price") or {}).get("currency")
                notes: list[str] = []
                if offer.get("boardType"):
                    notes.append(f"Board: {offer['boardType']}")
                if offer.get("room") and isinstance(offer["room"], MutableMapping):
                    room_desc = offer["room"].get("description")
                    if isinstance(room_desc, MutableMapping):
                        text = room_desc.get("text")
                        if text:
                            notes.append(str(text))
                loyalty = offer.get("loyaltyProgramme") or {}
                loyalty_cost = loyalty.get("points") if isinstance(loyalty, MutableMapping) else None
                loyalty_program = loyalty.get("program") if isinstance(loyalty, MutableMapping) else None
                location = None
                if isinstance(hotel, MutableMapping):
                    geo = hotel.get("geoCode")
                    if isinstance(geo, MutableMapping):
                        lat = geo.get("latitude")
                        lng = geo.get("longitude")
                        if lat is not None and lng is not None:
                            location = f"{lat}, {lng}"
                results.append(
                    {
                        "name": hotel.get("name", ""),
                        "price_per_night": float(price) if price is not None else 0.0,
                        "currency": currency or "USD",
                        "check_in": check_in,
                        "check_out": check_out,
                        "rating": hotel.get("rating"),
                        "location": location,
                        "booking_url": offer.get("self") or offer.get("id", ""),
                        "loyalty_cost": loyalty_cost,
                        "loyalty_program": loyalty_program,
                        "notes": tuple(notes),
                    }
                )
        return tuple(results)


class AmadeusSearchProvider(CompositeSearchProvider):
    """Composite provider that reuses the same Amadeus credentials for all searches."""

    def __init__(self, config: AmadeusConfig, *, session: requests.Session | None = None) -> None:
        self._client = _AmadeusClient(config, session=session)
        self._flight = AmadeusFlightSearchProvider(client=self._client)
        self._hotel = AmadeusHotelSearchProvider(client=self._client)

    def search(self, query: str, *, filters: Mapping[str, object] | None = None) -> Sequence[Mapping[str, object]]:
        params = {"keyword": query, "subType": "AIRPORT,CITY"}
        if filters:
            params.update(filters)
        response = self._client.get("/v1/reference-data/locations", params=params)
        data = response.get("data", [])
        if not isinstance(data, Iterable):
            return ()
        return tuple(item for item in data if isinstance(item, Mapping))

    def search_flights(
        self,
        *,
        origin: str,
        destination: str,
        departure_date: str,
        return_date: str | None,
        travelers: int,
        cabin: str | None,
        max_stops: int | None,
        loyalty_programs: Sequence[str],
    ) -> Sequence[Mapping[str, object]]:
        results = self._flight.search_flights(
            origin=origin,
            destination=destination,
            departure_date=departure_date,
            return_date=return_date,
            travelers=travelers,
            cabin=cabin,
            max_stops=max_stops,
            loyalty_programs=loyalty_programs,
        )
        return results

    def search_hotels(
        self,
        *,
        destination: str,
        check_in: str,
        check_out: str,
        travelers: int,
        neighborhoods: Sequence[str],
        amenities: Sequence[str],
        loyalty_programs: Sequence[str],
    ) -> Sequence[Mapping[str, object]]:
        results = self._hotel.search_hotels(
            destination=destination,
            check_in=check_in,
            check_out=check_out,
            travelers=travelers,
            neighborhoods=neighborhoods,
            amenities=amenities,
            loyalty_programs=loyalty_programs,
        )
        return results
