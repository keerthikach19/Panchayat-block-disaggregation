import unittest

from src.ingestion.imd_live import IMDLiveData


NASHIK_TEXT = """
Weather based Agromet Advisory committee meeting dated 28.08.2026 District: Nashik
Weather Forecast (29.08.2026 to 02.09.2026)
22 23 24 25 26 27 28 Date 29 30 31 01 02
33.8 35.3 10.0 13.5 14.4 1.2 18.4 Rainfall (mm) 6 5 4 4 5
"""

PUNE_TEXT = """
Weather based Agromet Advisory committee meeting dated 28.08.2026 District: Pune
Weather Forecast (28.08.2026 to 01.09.2026)
22 23 24 25 26 27 28 Date 29 30 31 1 2
0.6 1.7 0.5 1.2 1.2 0.5 2.2 Rainfall (mm) 9 10 7 8 9
"""


class IMDAgrometParserTests(unittest.TestCase):
    def test_parses_nashik_daily_forecast_and_selects_target_date(self):
        result = IMDLiveData.parse_bulletin_text(NASHIK_TEXT, "Nashik", "https://example.test", "2026-09-01")
        self.assertEqual(result["selected_forecast_date"], "2026-09-01")
        self.assertEqual(result["selected_rainfall_mm"], 4.0)
        self.assertEqual([item["rainfall_mm"] for item in result["forecast_days"]], [6, 5, 4, 4, 5])

    def test_parses_pune_date_row_when_header_is_one_day_behind(self):
        result = IMDLiveData.parse_bulletin_text(PUNE_TEXT, "Pune", "https://example.test", "2026-09-01")
        self.assertEqual(result["selected_forecast_date"], "2026-09-01")
        self.assertEqual(result["selected_rainfall_mm"], 8.0)

    def test_parses_realized_rainfall_as_secondary_context(self):
        raw = '''"title": "PUNE", "id": "159", "balloonText": "<h6>PUNE<\\/h6> <p><em>Date : 2026-08-31<\\/br>Departure : -89%<\\/br>Actual : 0.6 mm<\\/br>Normal : 5.7 mm<\\/em><\\/p>"'''
        result = IMDLiveData.parse_realized_rainfall_html(raw, "Pune")
        self.assertEqual(result["rainfall_mm"], 0.6)
        self.assertEqual(result["observed_date"], "2026-08-31")


if __name__ == "__main__":
    unittest.main()
