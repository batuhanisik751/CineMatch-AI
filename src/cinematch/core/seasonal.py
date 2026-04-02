"""Month-to-context mapping for seasonal recommendations."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime


@dataclass(frozen=True)
class SeasonalContext:
    """Configuration for a single month's seasonal theme."""

    month: int
    season_name: str
    theme_label: str
    keywords: list[str] = field(default_factory=list)
    genres: list[str] = field(default_factory=list)
    sort_field: str = "popularity"
    min_popularity: float | None = None


SEASONAL_MAP: dict[int, SeasonalContext] = {
    1: SeasonalContext(
        month=1,
        season_name="New Year",
        theme_label="Fresh Starts & New Beginnings",
        keywords=["new year", "resolution", "redemption"],
        genres=["Drama"],
        sort_field="vote_average",
    ),
    2: SeasonalContext(
        month=2,
        season_name="Valentine's",
        theme_label="Love Stories",
        keywords=["love", "relationship", "romance", "wedding"],
        genres=["Romance"],
        sort_field="vote_average",
    ),
    3: SeasonalContext(
        month=3,
        season_name="Women's History",
        theme_label="Trailblazing Women",
        keywords=["woman", "feminist", "female protagonist"],
        genres=["Drama"],
        sort_field="vote_average",
    ),
    4: SeasonalContext(
        month=4,
        season_name="Spring",
        theme_label="Spring Awakening",
        keywords=["nature", "garden", "coming of age"],
        genres=["Drama", "Comedy"],
        sort_field="popularity",
    ),
    5: SeasonalContext(
        month=5,
        season_name="Summer Kickoff",
        theme_label="Blockbuster Season Begins",
        keywords=["superhero", "action hero", "explosion"],
        genres=["Action", "Science Fiction"],
        sort_field="popularity",
        min_popularity=20.0,
    ),
    6: SeasonalContext(
        month=6,
        season_name="Summer",
        theme_label="Summer Blockbusters",
        keywords=["summer", "adventure", "road trip"],
        genres=["Action", "Adventure"],
        sort_field="popularity",
        min_popularity=20.0,
    ),
    7: SeasonalContext(
        month=7,
        season_name="Summer",
        theme_label="Summer Spectacles",
        keywords=["independence", "war", "epic"],
        genres=["Action", "Adventure", "War"],
        sort_field="popularity",
        min_popularity=20.0,
    ),
    8: SeasonalContext(
        month=8,
        season_name="Late Summer",
        theme_label="Last Days of Summer",
        keywords=["vacation", "beach", "coming of age"],
        genres=["Action", "Adventure", "Comedy"],
        sort_field="popularity",
        min_popularity=15.0,
    ),
    9: SeasonalContext(
        month=9,
        season_name="Back to School",
        theme_label="Back to School",
        keywords=["school", "college", "education", "teacher"],
        genres=["Drama", "Comedy"],
        sort_field="vote_average",
    ),
    10: SeasonalContext(
        month=10,
        season_name="Spooky Season",
        theme_label="Halloween Frights",
        keywords=["horror", "halloween", "scary", "ghost", "monster", "zombie"],
        genres=["Horror", "Thriller"],
        sort_field="popularity",
    ),
    11: SeasonalContext(
        month=11,
        season_name="Thanksgiving",
        theme_label="Gratitude & Family",
        keywords=["family", "thanksgiving", "reunion"],
        genres=["Drama", "Family"],
        sort_field="vote_average",
    ),
    12: SeasonalContext(
        month=12,
        season_name="Holiday Season",
        theme_label="Holiday Classics",
        keywords=["christmas", "holiday", "winter", "snow", "santa"],
        genres=["Family", "Animation", "Fantasy"],
        sort_field="vote_average",
    ),
}


def get_seasonal_context(month: int | None = None) -> SeasonalContext:
    """Return the seasonal context for the given month (defaults to current)."""
    resolved = month if month is not None else datetime.now(UTC).month
    return SEASONAL_MAP[resolved]
