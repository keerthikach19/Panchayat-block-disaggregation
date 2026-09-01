"""Public IMD forecast and realized-rainfall adapters.

The agromet bulletin is the predictive input to downscaling. Mausam's
24-hour feed is intentionally separate: it describes what has already
happened and is exposed only as recent-condition context.
"""

from __future__ import annotations

import html
import io
import json
import re
import ssl
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urlencode
from urllib.request import Request, urlopen


PROJECT_ROOT = Path(__file__).resolve().parents[2]
CACHE_DIR = PROJECT_ROOT / "data" / "cache"
AGROMET_BULLETIN_URL = "https://imdagrimet.gov.in/Services/DistrictBulletin.php"
MAUSAM_REALIZED_URL = "https://mausam.imd.gov.in/responsive/rainfallinformation.php?msg=D"
HEADERS = {"User-Agent": "IMD-DAMU-Downscaling/1.0 (+public-data-use)"}
DISTRICT_STATES = {"nashik": "Maharashtra", "pune": "Maharashtra"}


class LiveDataUnavailable(RuntimeError):
    """Raised when IMD is unavailable and no locally cached result exists."""


class IMDLiveData:
    """Fetch, parse, and cache IMD public feeds without using credentials."""

    def __init__(self, cache_dir: Path = CACHE_DIR, timeout_seconds: int = 30):
        self.cache_dir = Path(cache_dir)
        self.timeout_seconds = timeout_seconds

    def fetch_forecast(self, district: str, target_date: Optional[str] = None) -> Dict[str, Any]:
        """Return the current five-day district forecast and its selected day."""
        district_name = self._district_name(district)
        state = DISTRICT_STATES.get(district_name.lower())
        if not state:
            raise LiveDataUnavailable(f"No IMD agromet state mapping configured for {district_name}.")

        params = urlencode({"state": state, "district": district_name, "language": "English"})
        source_url = f"{AGROMET_BULLETIN_URL}?{params}"
        try:
            bulletin = self._get_bytes(source_url)
            parsed = self.parse_bulletin_pdf(bulletin, district_name, source_url, target_date)
            parsed["status"] = "LIVE_OK"
            parsed["fetched_at"] = self._now_iso()
            self._write_cache("agromet", district_name, parsed)
            return parsed
        except Exception as exc:
            cached = self._read_cache("agromet", district_name)
            if cached:
                cached["status"] = "LIVE_CACHED"
                cached["live_error"] = str(exc)
                return cached
            raise LiveDataUnavailable(f"Unable to obtain a live IMD forecast for {district_name}: {exc}") from exc

    def fetch_recent_observation(self, district: str) -> Dict[str, Any]:
        """Return realized 24-hour rainfall only for advisory context, never forecasting."""
        district_name = self._district_name(district)
        try:
            raw = self._get_bytes(MAUSAM_REALIZED_URL).decode("utf-8", errors="replace")
            parsed = self.parse_realized_rainfall_html(raw, district_name)
            parsed.update({
                "source": "IMD Mausam realized 24-hour district rainfall",
                "source_url": MAUSAM_REALIZED_URL,
                "status": "LIVE_OK",
                "fetched_at": self._now_iso(),
            })
            self._write_cache("observed", district_name, parsed)
            return parsed
        except Exception as exc:
            cached = self._read_cache("observed", district_name)
            if cached:
                cached["status"] = "LIVE_CACHED"
                cached["live_error"] = str(exc)
                return cached
            return {"status": "UNAVAILABLE", "source": "IMD Mausam realized 24-hour district rainfall", "source_url": MAUSAM_REALIZED_URL, "error": str(exc)}

    @classmethod
    def parse_bulletin_pdf(cls, pdf_bytes: bytes, district: str, source_url: str, target_date: Optional[str] = None) -> Dict[str, Any]:
        try:
            from pypdf import PdfReader
            reader = PdfReader(io.BytesIO(pdf_bytes))
            text = "\n".join(page.extract_text() or "" for page in reader.pages)
        except ImportError:
            # The project environment currently includes pdfplumber; retain a
            # pypdf fast path for the bundled runtime and deployments using it.
            try:
                import pdfplumber
            except ImportError as exc:
                raise RuntimeError("Install pypdf or pdfplumber to read IMD agromet bulletin PDFs") from exc
            with pdfplumber.open(io.BytesIO(pdf_bytes)) as bulletin:
                text = "\n".join(page.extract_text() or "" for page in bulletin.pages)
        return cls.parse_bulletin_text(text, district, source_url, target_date)

    @classmethod
    def parse_bulletin_text(cls, text: str, district: str, source_url: str, target_date: Optional[str] = None) -> Dict[str, Any]:
        """Parse the five forecast dates and rainfall values from IMD PDF text."""
        normalized = re.sub(r"[\u00a0\t]+", " ", text)
        values_match = re.search(r"Rainfall\s*\(\s*mm\s*\)\s*((?:\d+(?:\.\d+)?\s+){4,8})", normalized, flags=re.IGNORECASE)
        if not values_match:
            raise ValueError("Could not find the Weather Forecast rainfall row in the IMD bulletin.")
        rainfall_values = [float(value) for value in re.findall(r"\d+(?:\.\d+)?", values_match.group(1))[:5]]
        if len(rainfall_values) != 5:
            raise ValueError("The IMD bulletin did not contain five daily rainfall values.")

        issue_match = re.search(r"(?:meeting dated|Date\s*:)\s*(\d{1,2}\.\d{1,2}\.\d{4})", normalized, re.IGNORECASE)
        issued_date = cls._parse_dot_date(issue_match.group(1)) if issue_match else None
        period_match = re.search(r"Weather\s+Forecast\s*\(\s*(\d{1,2}\.\d{1,2}\.\d{4})\s*to\s*(\d{1,2}\.\d{1,2}\.\d{4})\s*\)", normalized, re.IGNORECASE)
        date_row_match = re.search(r"\bDate\s+((?:\d{1,2}\s+){4}\d{1,2})\b", normalized, re.IGNORECASE)
        if date_row_match and period_match:
            forecast_dates = cls._dates_from_row(date_row_match.group(1), cls._parse_dot_date(period_match.group(1)))
        elif issued_date:
            forecast_dates = [issued_date + timedelta(days=offset) for offset in range(1, 6)]
        else:
            raise ValueError("Could not determine the forecast-valid dates from the IMD bulletin.")

        daily = [{"date": forecast_day.isoformat(), "rainfall_mm": rainfall} for forecast_day, rainfall in zip(forecast_dates, rainfall_values)]
        requested = date.fromisoformat(target_date) if target_date else date.today()
        selected = next((entry for entry in daily if date.fromisoformat(entry["date"]) >= requested), None)
        if selected is None:
            raise ValueError(f"The latest IMD bulletin ends on {daily[-1]['date']}; no forecast is available for {requested.isoformat()}.")
        return {"district": district, "source": "IMD GKMS district agromet advisory forecast", "source_url": source_url, "issued_date": issued_date.isoformat() if issued_date else None, "forecast_days": daily, "selected_forecast_date": selected["date"], "selected_rainfall_mm": selected["rainfall_mm"]}

    @staticmethod
    def parse_realized_rainfall_html(raw_html: str, district: str) -> Dict[str, Any]:
        """Extract a district's observed 24-hour value from the page's map data."""
        target = district.upper()
        item_pattern = re.compile(r'"title"\s*:\s*"(?P<title>[^"]+)".*?"balloonText"\s*:\s*"(?P<balloon>(?:\\.|[^"\\])*)"', re.DOTALL)
        for match in item_pattern.finditer(raw_html):
            if match.group("title").strip().upper() != target:
                continue
            balloon = html.unescape(match.group("balloon").replace("\\/", "/"))
            actual = re.search(r"Actual\s*:\s*([\d.]+)\s*mm", balloon, re.IGNORECASE)
            observed_date = re.search(r"Date\s*:\s*(\d{4}-\d{2}-\d{2})", balloon, re.IGNORECASE)
            departure = re.search(r"Departure\s*:\s*([^<\\]+)", balloon, re.IGNORECASE)
            normal = re.search(r"Normal\s*:\s*([\d.]+)\s*mm", balloon, re.IGNORECASE)
            if actual and observed_date:
                return {"district": district, "observed_date": observed_date.group(1), "rainfall_mm": float(actual.group(1)), "normal_mm": float(normal.group(1)) if normal else None, "departure": departure.group(1).strip() if departure else None}
        raise ValueError(f"Could not find a realized-rainfall entry for {district}.")

    @staticmethod
    def _dates_from_row(date_row: str, period_start: date) -> List[date]:
        labels = [int(value) for value in date_row.split()]
        results: List[date] = []
        year, month, previous_day = period_start.year, period_start.month, period_start.day
        for day in labels[:5]:
            if day < previous_day:
                month += 1
                if month == 13:
                    year, month = year + 1, 1
            results.append(date(year, month, day))
            previous_day = day
        return results

    @staticmethod
    def _parse_dot_date(value: str) -> date:
        return datetime.strptime(value, "%d.%m.%Y").date()

    @staticmethod
    def _district_name(district: str) -> str:
        return district.strip().title()

    def _get_bytes(self, url: str) -> bytes:
        request = Request(url, headers=HEADERS)
        with urlopen(request, timeout=self.timeout_seconds, context=ssl.create_default_context()) as response:
            if response.status != 200:
                raise RuntimeError(f"IMD returned HTTP {response.status}")
            return response.read()

    def _cache_path(self, feed_name: str, district: str) -> Path:
        return self.cache_dir / f"{feed_name}_{district.lower()}.json"

    def _write_cache(self, feed_name: str, district: str, payload: Dict[str, Any]) -> None:
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._cache_path(feed_name, district).write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def _read_cache(self, feed_name: str, district: str) -> Optional[Dict[str, Any]]:
        path = self._cache_path(feed_name, district)
        return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None

    @staticmethod
    def _now_iso() -> str:
        return datetime.now(timezone.utc).isoformat()
