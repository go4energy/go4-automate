"""Adaptive geographic tiling for Places API coverage.

A GeoTile is an axis-aligned lat/lng rectangle. Saturated tiles (i.e. queries
that returned the maximum result count) are subdivided into 4 quadrant
sub-tiles. This lets the worker crawl dense regions more finely without
wasting calls on sparse ones.

Nearby Search requires a circle, not a rectangle, so we also expose
``inscribed_circle`` which returns the largest circle that fits inside a
tile. Google caps the Nearby radius at 50 km; oversized tiles fall back to
that cap (and accept the resulting under-coverage near the corners).
"""

from __future__ import annotations

import math
from dataclasses import dataclass

# Earth constants (WGS-84 average). Good enough for tile sizing - we do not
# reproject, just approximate.
EARTH_RADIUS_KM = 6371.0088
KM_PER_DEG_LAT = 111.32

# Google Nearby Search radius cap.
NEARBY_MAX_RADIUS_M = 50000.0


@dataclass(frozen=True)
class GeoTile:
    """Axis-aligned lat/lng rectangle."""

    south: float
    west: float
    north: float
    east: float

    def __post_init__(self) -> None:
        if self.south >= self.north:
            raise ValueError(f"south ({self.south}) must be < north ({self.north})")
        if self.west >= self.east:
            raise ValueError(f"west ({self.west}) must be < east ({self.east})")

    @property
    def center(self) -> tuple[float, float]:
        return (
            (self.south + self.north) / 2,
            (self.west + self.east) / 2,
        )

    @property
    def width_km(self) -> float:
        """East-west extent in km at the tile's mean latitude."""
        mean_lat = (self.south + self.north) / 2
        km_per_deg_lng = KM_PER_DEG_LAT * math.cos(math.radians(mean_lat))
        return (self.east - self.west) * km_per_deg_lng

    @property
    def height_km(self) -> float:
        """North-south extent in km (latitude-only, constant)."""
        return (self.north - self.south) * KM_PER_DEG_LAT

    @property
    def area_km2(self) -> float:
        return self.width_km * self.height_km

    def subdivide(self) -> list[GeoTile]:
        """Split into 4 equal quadrants."""
        mid_lat = (self.south + self.north) / 2
        mid_lng = (self.west + self.east) / 2
        return [
            GeoTile(south=self.south, west=self.west, north=mid_lat, east=mid_lng),
            GeoTile(south=self.south, west=mid_lng, north=mid_lat, east=self.east),
            GeoTile(south=mid_lat, west=self.west, north=self.north, east=mid_lng),
            GeoTile(south=mid_lat, west=mid_lng, north=self.north, east=self.east),
        ]

    def contains(self, lat: float, lng: float) -> bool:
        return self.south <= lat <= self.north and self.west <= lng <= self.east

    def to_rectangle_payload(self) -> dict:
        """Shape required by Places API locationRestriction.rectangle."""
        return {
            "rectangle": {
                "low": {"latitude": self.south, "longitude": self.west},
                "high": {"latitude": self.north, "longitude": self.east},
            }
        }

    def inscribed_circle(self) -> tuple[float, float, float]:
        """Largest circle fitting in the tile (center_lat, center_lng, radius_m).

        Radius is capped at Google's Nearby Search maximum of 50 km. Tiles
        larger than that accept partial coverage and rely on subdivision to
        reach the corners.
        """
        cx, cy = self.center
        half_h_km = self.height_km / 2
        half_w_km = self.width_km / 2
        radius_m = min(half_h_km, half_w_km) * 1000
        return cx, cy, min(radius_m, NEARBY_MAX_RADIUS_M)


# --------------------------------------------------------------------------
# Country and state bounding boxes. Values rounded to 3 decimals; they are
# only used as starting tiles, precision beyond that is not meaningful.
# --------------------------------------------------------------------------

GERMANY_BOUNDS = GeoTile(south=47.271, west=5.867, north=55.058, east=15.042)
AUSTRIA_BOUNDS = GeoTile(south=46.372, west=9.531, north=49.021, east=17.160)
SWITZERLAND_BOUNDS = GeoTile(south=45.818, west=5.956, north=47.808, east=10.492)

# German federal states (Bundeslaender). Used when the user picks "Bundesland"
# as geographic scope. Bounding boxes are loose - they may overlap neighbouring
# states; dedup via google_place_id handles this.
BUNDESLAND_BOUNDS: dict[str, GeoTile] = {
    "baden_wuerttemberg": GeoTile(south=47.533, west=7.512, north=49.791, east=10.495),
    "bayern": GeoTile(south=47.270, west=8.976, north=50.564, east=13.840),
    "berlin": GeoTile(south=52.338, west=13.088, north=52.675, east=13.761),
    "brandenburg": GeoTile(south=51.359, west=11.266, north=53.559, east=14.766),
    "bremen": GeoTile(south=53.011, west=8.481, north=53.607, east=8.991),
    "hamburg": GeoTile(south=53.395, west=9.730, north=53.739, east=10.326),
    "hessen": GeoTile(south=49.395, west=7.771, north=51.656, east=10.236),
    "mecklenburg_vorpommern": GeoTile(
        south=53.115, west=10.594, north=54.683, east=14.412
    ),
    "niedersachsen": GeoTile(south=51.295, west=6.654, north=53.893, east=11.598),
    "nordrhein_westfalen": GeoTile(
        south=50.323, west=5.865, north=52.531, east=9.461
    ),
    "rheinland_pfalz": GeoTile(south=48.966, west=6.113, north=50.941, east=8.509),
    "saarland": GeoTile(south=49.112, west=6.356, north=49.640, east=7.404),
    "sachsen": GeoTile(south=50.171, west=11.872, north=51.685, east=15.042),
    "sachsen_anhalt": GeoTile(south=50.937, west=10.562, north=53.043, east=13.187),
    "schleswig_holstein": GeoTile(
        south=53.359, west=7.867, north=55.058, east=11.314
    ),
    "thueringen": GeoTile(south=50.205, west=9.875, north=51.651, east=12.654),
}


# --------------------------------------------------------------------------
# Adaptive tile queue
# --------------------------------------------------------------------------


@dataclass
class TileProcessingResult:
    """Return value from crawling one tile."""

    tile: GeoTile
    result_count: int
    saturated: bool


def should_subdivide(
    result: TileProcessingResult,
    *,
    min_tile_km: float,
    saturation_threshold: int,
) -> bool:
    """Decide whether a tile should be split into 4 sub-tiles.

    True if:
    - tile returned >= saturation_threshold results (i.e. likely more exist)
    - tile is still larger than min_tile_km on its shorter side
    """
    if result.result_count < saturation_threshold:
        return False
    shorter_km = min(result.tile.width_km, result.tile.height_km)
    return shorter_km > min_tile_km


def build_initial_tiles(
    *,
    scope: str,
    bundesland: str | None = None,
    center_lat: float | None = None,
    center_lng: float | None = None,
    radius_km: float | None = None,
) -> list[GeoTile]:
    """Build the starting tile list from a user-facing scope definition.

    scope:
        - "germany": single Germany bbox
        - "austria" / "switzerland": respective country bbox
        - "bundesland": uses ``bundesland`` key
        - "circle": square bbox around (center_lat, center_lng) with side 2*radius_km
    """
    if scope == "germany":
        return [GERMANY_BOUNDS]
    if scope == "austria":
        return [AUSTRIA_BOUNDS]
    if scope == "switzerland":
        return [SWITZERLAND_BOUNDS]
    if scope == "bundesland":
        if not bundesland or bundesland not in BUNDESLAND_BOUNDS:
            raise ValueError(f"unknown bundesland: {bundesland!r}")
        return [BUNDESLAND_BOUNDS[bundesland]]
    if scope == "circle":
        if center_lat is None or center_lng is None or radius_km is None:
            raise ValueError("circle scope requires center_lat, center_lng, radius_km")
        km_per_deg_lng = KM_PER_DEG_LAT * math.cos(math.radians(center_lat))
        d_lat = radius_km / KM_PER_DEG_LAT
        d_lng = radius_km / max(km_per_deg_lng, 0.001)
        return [
            GeoTile(
                south=center_lat - d_lat,
                north=center_lat + d_lat,
                west=center_lng - d_lng,
                east=center_lng + d_lng,
            )
        ]
    raise ValueError(f"unknown scope: {scope!r}")
