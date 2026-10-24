import json
import unittest
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import patch
from urllib.parse import parse_qs, urlparse

import weather


class FakeResponse:
    def __init__(self, payload):
        self.payload = json.dumps(payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return self.payload


class WeatherTests(unittest.TestCase):
    def setUp(self):
        self.clock = patch.object(
            weather,
            "datetime",
            SimpleNamespace(now=lambda tz: datetime(2026, 10, 24, tzinfo=tz)),
        )
        self.clock.start()
        self.addCleanup(self.clock.stop)

    @staticmethod
    def forecast_data(code=61, probability=70, amount=2.5):
        return {
            "timezone": "Asia/Shanghai",
            "daily": {
                "time": ["2026-10-25"],
                "weather_code": [code],
                "temperature_2m_max": [19.2],
                "temperature_2m_min": [12.1],
                "precipitation_probability_max": [probability],
                "precipitation_sum": [amount],
            },
        }

    def test_forecast_returns_weather_and_umbrella_recommendation(self):
        responses = [
            FakeResponse({"results": [{
                "name": "上海市", "admin1": "上海市", "country": "中国",
                "latitude": 31.23, "longitude": 121.47,
            }]}),
            FakeResponse(self.forecast_data()),
        ]
        with patch.object(weather, "urlopen", side_effect=responses) as urlopen:
            result = weather.get_weather_forecast("上海", "2026-10-25")

        self.assertTrue(result["found"])
        self.assertEqual(result["weather"], "小雨")
        self.assertEqual(result["temperature_min_c"], 12.1)
        self.assertTrue(result["umbrella_recommended"])
        self.assertEqual(urlopen.call_count, 2)
        forecast_url = urlparse(urlopen.call_args_list[1].args[0].full_url)
        self.assertEqual(parse_qs(forecast_url.query)["timezone"], ["Asia/Shanghai"])

    def test_ambiguous_location_returns_candidates_without_forecast_request(self):
        response = FakeResponse({"results": [
            {"name": "朝阳区", "admin1": "北京市", "country": "中国", "latitude": 39.9, "longitude": 116.4},
            {"name": "朝阳区", "admin1": "辽宁省", "country": "中国", "latitude": 41.6, "longitude": 120.4},
        ]})
        with patch.object(weather, "urlopen", return_value=response) as urlopen:
            result = weather.get_weather_forecast("朝阳区", "2026-10-25")

        self.assertFalse(result["found"])
        self.assertEqual(len(result["candidates"]), 2)
        urlopen.assert_called_once()

    def test_no_location_result_is_clear(self):
        with patch.object(weather, "urlopen", return_value=FakeResponse({"results": None})):
            result = weather.get_weather_forecast("不存在的地方", "2026-10-25")

        self.assertFalse(result["found"])
        self.assertIn("没有找到", result["message"])

    def test_invalid_or_out_of_range_dates_are_rejected_before_network(self):
        with patch.object(weather, "urlopen") as urlopen:
            for day in ("2026-10-23", "2026-11-09", "2026-02-30"):
                with self.subTest(day=day), self.assertRaises(ValueError):
                    weather.get_weather_forecast("上海", day)
        urlopen.assert_not_called()

    def test_clear_weather_does_not_recommend_umbrella(self):
        responses = [
            FakeResponse({"results": [{
                "name": "上海市", "country": "中国", "latitude": 31.23, "longitude": 121.47,
            }]}),
            FakeResponse(self.forecast_data(code=0, probability=0, amount=0)),
        ]
        with patch.object(weather, "urlopen", side_effect=responses):
            result = weather.get_weather_forecast("上海市", "2026-10-25")

        self.assertEqual(result["weather"], "晴朗")
        self.assertFalse(result["umbrella_recommended"])


if __name__ == "__main__":
    unittest.main()
