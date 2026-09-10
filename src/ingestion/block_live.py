#!/usr/bin/env python3
"""
Block-Level Live Weather Ingestion (SIH PS 26074).

Fetches current block/taluka-level weather data using the Open-Meteo API,
one API call per taluka centroid.  Falls back automatically to a district
bulletin value scaled by a precomputed taluka climatological ratio when the
Open-Meteo call fails.

Architecture
------------
  PRIMARY  : Open-Meteo /forecast endpoint per taluka centroid (free, no key,
             elevation-corrected)
  FALLBACK : district_bulletin_value × taluka_ratio
             (taluka_ratio from data/corrections/taluka_climatology_ratios.json)

Usage
-----
    from src.ingestion.block_live import BlockLiveData

    bld = BlockLiveData(district="Nashik")
    result = bld.fetch_taluka_weather("Igatpuri")
    # → {"rainfall_mm": 38.4, "temp_max_c": 26.1, "temp_min_c": 17.3,
    #    "source": "open_meteo", "taluka": "Igatpuri", ...}

    # Fetch all talukas in the district:
    all_talukas = bld.fetch_all_talukas()
"""

import json
import logging
import time
from datetime import date
from pathlib import Path
from typing import Dict, Optional

import requests

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
RATIOS_PATH = PROJECT_ROOT / "data" / "corrections" / "taluka_climatology_ratios.json"
TALUKAS_GEOJSON = PROJECT_ROOT / "data" / "boundaries" / "maharashtra_talukas.geojson"
BOUNDING_BOXES_PATH = PROJECT_ROOT / "config" / "bounding_boxes.json"

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"
CACHE_TTL_SECONDS = 3600  # 1-hour cache per taluka


def _load_json(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(f"Required file not found: {path}")
    with open(path) as f:
        return json.load(f)


class BlockLiveData:
    """
    Manages live block/taluka-level weather data for a given district.

    Parameters
    ----------
    district : str
        Target district name (e.g. 'Nashik', 'Pune').
    cache_dir : Path | None
        Directory for caching Open-Meteo responses. Defaults to
        data/cache/block_live/.
    """

    def __init__(self, district: str = "Nashik", cache_dir: Optional[Path] = None):
        self.district = district
        self.cache_dir = cache_dir or (PROJECT_ROOT / "data" / "cache" / "block_live")
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # Load supporting data
        self._ratios: Dict[str, float] = {}
        self._centroids: Dict[str, Dict] = {}  # taluka → {lat, lon}
        self._load_ratios()
        self._load_centroids()

    # ------------------------------------------------------------------
    # Initialisation helpers
    # ------------------------------------------------------------------

    def _load_ratios(self):
        """Load taluka climatology ratios from JSON."""
        try:
            self._ratios = _load_json(RATIOS_PATH)
            logger.debug("Loaded %d taluka climatology ratios.", len(self._ratios))
        except FileNotFoundError:
            logger.warning("taluka_climatology_ratios.json not found; fallback scaling disabled.")

    def _load_centroids(self):
        """Extract taluka centroid coordinates from bounding_boxes.json.

        Expected structure::

            {
              "talukas": {
                "Igatpuri": {
                  "district": "Nashik",
                  "centroid": {"lat": 19.697, "lon": 73.563},
                  "bbox": {...}
                },
                ...
              }
            }
        """
        try:
            bboxes = _load_json(BOUNDING_BOXES_PATH)
            talukas_section = bboxes.get("talukas", {})
            for taluka, val in talukas_section.items():
                if not isinstance(val, dict):
                    continue
                # Filter by district when info available
                taluka_district = val.get("district", "")
                if taluka_district and taluka_district.lower() != self.district.lower():
                    continue
                centroid = val.get("centroid", {})
                lat = centroid.get("lat") or val.get("centroid_lat")
                lon = centroid.get("lon") or val.get("centroid_lon")
                if lat is not None and lon is not None:
                    self._centroids[taluka] = {"lat": float(lat), "lon": float(lon)}
            logger.debug(
                "Loaded %d taluka centroids for district '%s'.",
                len(self._centroids), self.district,
            )
        except (FileNotFoundError, KeyError) as exc:
            logger.warning("Could not load taluka centroids: %s", exc)

    # ------------------------------------------------------------------
    # Caching
    # ------------------------------------------------------------------

    def _cache_path(self, taluka: str) -> Path:
        return self.cache_dir / f"{self.district}__{taluka}_{date.today()}.json"

    def _read_cache(self, taluka: str) -> Optional[dict]:
        p = self._cache_path(taluka)
        if not p.exists():
            return None
        age = time.time() - p.stat().st_mtime
        if age > CACHE_TTL_SECONDS:
            return None
        try:
            with open(p) as f:
                return json.load(f)
        except Exception:
            return None

    def _write_cache(self, taluka: str, data: dict):
        p = self._cache_path(taluka)
        try:
            with open(p, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as exc:
            logger.warning("Cache write failed for %s: %s", taluka, exc)

    # ------------------------------------------------------------------
    # Open-Meteo fetch
    # ------------------------------------------------------------------

    def _fetch_open_meteo(self, lat: float, lon: float) -> dict:
        """
        Call Open-Meteo /forecast for today's daily values at (lat, lon).

        Returns dict with rainfall_mm, temp_max_c, temp_min_c, temp_mean_c.
        Raises requests.RequestException on network failure.
        """
        params = {
            "latitude": round(lat, 4),
            "longitude": round(lon, 4),
            "daily": "precipitation_sum,temperature_2m_max,temperature_2m_min",
            "forecast_days": 1,
            "timezone": "Asia/Kolkata",
        }
        resp = requests.get(OPEN_METEO_URL, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()

        daily = data.get("daily", {})
        rain = (daily.get("precipitation_sum") or [None])[0]
        tmax = (daily.get("temperature_2m_max") or [None])[0]
        tmin = (daily.get("temperature_2m_min") or [None])[0]

        return {
            "rainfall_mm": round(float(rain), 2) if rain is not None else 0.0,
            "temp_max_c":  round(float(tmax), 1) if tmax is not None else None,
            "temp_min_c":  round(float(tmin), 1) if tmin is not None else None,
            "temp_mean_c": round((float(tmax) + float(tmin)) / 2, 1) if (tmax and tmin) else None,
        }

    # ------------------------------------------------------------------
    # Fallback
    # ------------------------------------------------------------------

    def _apply_ratio_fallback(
        self,
        taluka: str,
        district_rainfall: float,
        district_tmax: Optional[float] = None,
        district_tmin: Optional[float] = None,
    ) -> dict:
        """Scale district bulletin value by taluka climatological ratio."""
        ratio = self._ratios.get(taluka, 1.0)
        scaled_rain = round(district_rainfall * ratio, 2)
        return {
            "rainfall_mm": scaled_rain,
            "temp_max_c": district_tmax,
            "temp_min_c": district_tmin,
            "temp_mean_c": round((district_tmax + district_tmin) / 2, 1)
                           if (district_tmax and district_tmin) else None,
            "source": "district_bulletin_ratio_fallback",
            "taluka_ratio": ratio,
        }

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def fetch_taluka_weather(
        self,
        taluka: str,
        district_bulletin: Optional[dict] = None,
    ) -> dict:
        """
        Fetch live weather for a single taluka.

        Tries Open-Meteo first (cache → network → fallback).

        Parameters
        ----------
        taluka : str
            Taluka name matching a key in bounding_boxes.json.
        district_bulletin : dict | None
            Optional fallback dict with keys: rainfall_mm, temp_max_c, temp_min_c.
            Used when Open-Meteo is unavailable.

        Returns
        -------
        dict
            {rainfall_mm, temp_max_c, temp_min_c, temp_mean_c,
             source, taluka, district, date}
        """
        # 1. Cache hit
        cached = self._read_cache(taluka)
        if cached:
            logger.debug("Cache hit for taluka '%s'.", taluka)
            return cached

        result = None
        centroid = self._centroids.get(taluka)

        # 2. Open-Meteo
        if centroid:
            try:
                om_data = self._fetch_open_meteo(centroid["lat"], centroid["lon"])
                result = {
                    **om_data,
                    "source": "open_meteo",
                    "taluka": taluka,
                    "district": self.district,
                    "date": str(date.today()),
                    "centroid_lat": centroid["lat"],
                    "centroid_lon": centroid["lon"],
                }
                logger.info(
                    "Open-Meteo ✓ | %s / %s | rain=%.1f mm | tmax=%.1f°C",
                    self.district, taluka,
                    result["rainfall_mm"], result["temp_max_c"] or -99,
                )
                self._write_cache(taluka, result)
                return result
            except Exception as exc:
                logger.warning(
                    "Open-Meteo failed for %s / %s: %s — trying fallback.",
                    self.district, taluka, exc,
                )
        else:
            logger.warning(
                "No centroid found for taluka '%s' in district '%s'. Trying fallback.",
                taluka, self.district,
            )

        # 3. District bulletin ratio fallback
        if district_bulletin:
            result = {
                **self._apply_ratio_fallback(
                    taluka,
                    district_bulletin.get("rainfall_mm", 0.0),
                    district_bulletin.get("temp_max_c"),
                    district_bulletin.get("temp_min_c"),
                ),
                "taluka": taluka,
                "district": self.district,
                "date": str(date.today()),
            }
            logger.info(
                "Fallback ratio ✓ | %s / %s | rain=%.1f mm (ratio=%.3f)",
                self.district, taluka,
                result["rainfall_mm"], result.get("taluka_ratio", 1.0),
            )
            self._write_cache(taluka, result)
            return result

        # 4. No data available
        logger.error(
            "No weather data available for taluka '%s' / district '%s'.",
            taluka, self.district,
        )
        return {
            "rainfall_mm": None,
            "temp_max_c": None,
            "temp_min_c": None,
            "temp_mean_c": None,
            "source": "unavailable",
            "taluka": taluka,
            "district": self.district,
            "date": str(date.today()),
        }

    def fetch_all_talukas(self, district_bulletin: Optional[dict] = None) -> Dict[str, dict]:
        """
        Fetch live weather for all known talukas in the district.

        Parameters
        ----------
        district_bulletin : dict | None
            Fallback district-level values.

        Returns
        -------
        dict
            {taluka_name: weather_dict}
        """
        results = {}
        talukas = list(self._centroids.keys())
        if not talukas:
            logger.warning(
                "No taluka centroids loaded for district '%s'. "
                "Check bounding_boxes.json.",
                self.district,
            )
            return results

        logger.info(
            "Fetching live block weather for %d talukas in %s …",
            len(talukas), self.district,
        )
        for taluka in talukas:
            results[taluka] = self.fetch_taluka_weather(taluka, district_bulletin)

        logger.info(
            "Fetched block weather for %d / %d talukas in %s.",
            sum(1 for v in results.values() if v.get("rainfall_mm") is not None),
            len(talukas),
            self.district,
        )
        return results
