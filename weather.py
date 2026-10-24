"""Read-only weather forecasts from Open-Meteo's public APIs."""
import json
from datetime import datetime, timedelta
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

from campus import parse_day

GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
WEATHER_CODES = {
    0: "晴朗",
    1: "大致晴朗",
    2: "局部多云",
    3: "阴天",
    45: "有雾",
    48: "冻雾",
    51: "毛毛雨",
    53: "中等毛毛雨",
    55: "强毛毛雨",
    56: "冻毛毛雨",
    57: "强冻毛毛雨",
    61: "小雨",
    63: "中雨",
    65: "大雨",
    66: "冻雨",
    67: "强冻雨",
    71: "小雪",
    73: "中雪",
    75: "大雪",
    77: "雪粒",
    80: "阵雨",
    81: "中等阵雨",
    82: "强阵雨",
    85: "阵雪",
    86: "强阵雪",
    95: "雷暴",
    96: "雷暴伴小冰雹",
    99: "雷暴伴强冰雹",
}
RAIN_CODES = {51, 53, 55, 56, 57, 61, 63, 65, 66, 67, 80, 81, 82, 95, 96, 99}
SHANGHAI = ZoneInfo("Asia/Shanghai")


def _get_json(url: str, params: dict) -> dict:
    request = Request(
        f"{url}?{urlencode(params)}",
        headers={"Accept": "application/json", "User-Agent": "campus-helper/1.0"},
    )
    try:
        with urlopen(request, timeout=10) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        raise RuntimeError(f"天气服务返回 HTTP {exc.code}") from exc
    except URLError as exc:
        raise RuntimeError("天气服务暂时不可用，请检查网络后重试") from exc
    except (TimeoutError, OSError) as exc:
        raise RuntimeError("连接天气服务超时或失败，请稍后重试") from exc
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RuntimeError("天气服务返回了无法识别的数据") from exc
    if not isinstance(payload, dict):
        raise RuntimeError("天气服务返回了无效数据")
    return payload


def get_weather_forecast(location: str, day: str) -> dict:
    """查询指定地区和日期的天气预报；仅返回 Open-Meteo 实时联网结果，不支持校园级定位。"""
    place = " ".join(location.split())
    if not place:
        raise ValueError("请提供城市或地区名称")
    if len(place) > 100:
        raise ValueError("地区名称不能超过 100 个字符")
    target = parse_day(day)
    today = datetime.now(SHANGHAI).date()
    if target < today:
        raise ValueError("天气预报只支持今天及未来日期")
    if target > today + timedelta(days=15):
        raise ValueError("天气预报最多支持未来 15 天")

    geocoding = _get_json(
        GEOCODING_URL,
        {"name": place, "count": 5, "language": "zh", "format": "json"},
    )
    matches = geocoding.get("results") or []
    if not matches:
        return {
            "found": False,
            "location_query": place,
            "message": "没有找到该地区。请提供城市或区县名称；天气服务无法定位到具体校园或建筑。",
        }
    if not isinstance(matches, list):
        raise RuntimeError("地点服务返回了无效数据")

    if len(matches) > 1:
        candidates = []
        for item in matches:
            if not isinstance(item, dict):
                continue
            label = ", ".join(
                str(item[key]).strip()
                for key in ("name", "admin1", "country")
                if item.get(key)
            )
            if label and label not in candidates:
                candidates.append(label)
        if len(candidates) > 1:
            return {
                "found": False,
                "location_query": place,
                "candidates": candidates,
                "message": "地点名称有歧义，请从候选地区中确认一个。",
            }

    location_data = matches[0]
    try:
        latitude = float(location_data["latitude"])
        longitude = float(location_data["longitude"])
        label = ", ".join(
            str(location_data[key]).strip()
            for key in ("name", "admin1", "country")
            if location_data.get(key)
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise RuntimeError("地点服务返回了不完整的坐标") from exc

    forecast = _get_json(
        FORECAST_URL,
        {
            "latitude": latitude,
            "longitude": longitude,
            "daily": (
                "weather_code,temperature_2m_max,temperature_2m_min,"
                "precipitation_probability_max,precipitation_sum"
            ),
            "forecast_days": 16,
            "timezone": "Asia/Shanghai",
            "start_date": target.isoformat(),
            "end_date": target.isoformat(),
        },
    )
    daily = forecast.get("daily")
    if not isinstance(daily, dict):
        raise RuntimeError("天气服务未返回该日期的预报")
    try:
        forecast_date = daily["time"][0]
        code = int(daily["weather_code"][0])
        temp_max = float(daily["temperature_2m_max"][0])
        temp_min = float(daily["temperature_2m_min"][0])
        precipitation_probability = daily["precipitation_probability_max"][0]
        precipitation_sum = float(daily["precipitation_sum"][0])
    except (KeyError, IndexError, TypeError, ValueError) as exc:
        raise RuntimeError("天气服务未返回该日期的完整预报") from exc
    if forecast_date != target.isoformat():
        raise RuntimeError("天气服务未返回所请求日期的预报")

    precipitation_probability = (
        int(precipitation_probability)
        if precipitation_probability is not None
        else None
    )
    weather = WEATHER_CODES.get(code, f"天气代码 {code}")
    rain_expected = code in RAIN_CODES or precipitation_sum > 0
    umbrella_recommended = (
        rain_expected
        or (
            precipitation_probability is not None
            and precipitation_probability >= 40
        )
    )
    return {
        "found": True,
        "location": label or place,
        "date": forecast_date,
        "weather": weather,
        "temperature_min_c": temp_min,
        "temperature_max_c": temp_max,
        "precipitation_probability_max_percent": precipitation_probability,
        "precipitation_sum_mm": precipitation_sum,
        "umbrella_recommended": umbrella_recommended,
        "timezone": forecast.get("timezone", "Asia/Shanghai"),
        "source": "Open-Meteo Geocoding API and Forecast API",
        "notice": "这是城市/地区级预报，可能变化；不代表校园微气候或官方预警。",
    }
