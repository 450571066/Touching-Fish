"""Itinerary planner that leverages external search providers."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta
from typing import List, Sequence

from models import Activity, Itinerary, ItineraryDay, TripRequest
from search import SearchProvider


class ItineraryPlanner:
    """Plan itineraries with the help of a search provider."""

    def __init__(self, search_provider: SearchProvider) -> None:
        self._search = search_provider

    def plan_trip(self, request: TripRequest) -> Itinerary:
        """Create an itinerary leveraging live search results.

        The planner issues searches for each user interest and assembles a
        structured itinerary. Results are grouped by day to provide a digestible
        plan. The method returns an :class:`Itinerary` that downstream
        components can consume (e.g. for building documents or feeding other
        agents).
        """

        suggestions = self._gather_suggestions(request)
        days = self._build_days(request, suggestions)
        notes = [
            "Generated with live search results; verify availability before booking.",
            "Consider adjusting based on traveler preferences and local events.",
        ]
        return Itinerary(request=request, days=days, notes=notes)

    def _gather_suggestions(self, request: TripRequest) -> Sequence[Activity]:
        queries = [
            f"{request.destination_label} {interest}" for interest in (request.interests or ("top sights",))
        ]
        suggestions: List[Activity] = []
        for query in queries:
            results = self._search.search(query, filters={"locale": "zh-CN"})
            for result in results:
                suggestions.append(
                    Activity(
                        name=result.get("title", ""),
                        description=result.get("snippet", ""),
                        location=result.get("location"),
                        start_time=self._parse_datetime(result.get("start_time")),
                        end_time=self._parse_datetime(result.get("end_time")),
                        booking_url=result.get("url"),
                    )
                )
        return suggestions

    def _build_days(self, request: TripRequest, activities: Sequence[Activity]) -> List[ItineraryDay]:
        grouped: dict[str, List[Activity]] = defaultdict(list)
        current_date = request.start_date
        for activity in activities:
            key = activity.start_time.date().isoformat() if activity.start_time else current_date.isoformat()
            grouped[key].append(activity)
            current_date += timedelta(days=1)
            if current_date > request.end_date:
                current_date = request.start_date

        days: List[ItineraryDay] = []
        day_cursor = request.start_date
        while day_cursor <= request.end_date:
            day_key = day_cursor.isoformat()
            days.append(ItineraryDay(date=day_cursor, activities=grouped.get(day_key, [])))
            day_cursor += timedelta(days=1)
        return days

    @staticmethod
    def _parse_datetime(value: object) -> datetime | None:
        if not value:
            return None
        if isinstance(value, datetime):
            return value
        if isinstance(value, str):
            try:
                return datetime.fromisoformat(value)
            except ValueError:
                return None
        return None
