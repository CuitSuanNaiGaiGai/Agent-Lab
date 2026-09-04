import requests

def weather(city: str) -> str:
    """
    一个天气查询工具。输入城市名称（中英文均可），返回当前天气简报。
    使用 Open-Meteo 提供的免费 API（无需 API Key）。
    """
    city = city.strip()
    if not city:
        return "错误: 城市名称为空"

    try:
        # 1. 地理编码：城市名 -> 经纬度
        geo_url = "https://geocoding-api.open-meteo.com/v1/search"
        geo_resp = requests.get(geo_url, params={"name": city, "count": 1, "language": "zh"}, timeout=10)
        geo_resp.raise_for_status()
        geo_data = geo_resp.json()

        if not geo_data.get("results"):
            return f"未找到城市: {city}"

        loc = geo_data["results"][0]
        lat, lon = loc["latitude"], loc["longitude"]
        city_name = loc.get("name", city)
        country = loc.get("country", "")

        # 2. 查询当前天气
        weather_url = "https://api.open-meteo.com/v1/forecast"
        weather_resp = requests.get(
            weather_url,
            params={
                "latitude": lat,
                "longitude": lon,
                "current": "temperature_2m,relative_humidity_2m,wind_speed_10m,weather_code",
                "timezone": "auto",
            },
            timeout=10,
        )
        weather_resp.raise_for_status()
        w_data = weather_resp.json().get("current", {})

        temp = w_data.get("temperature_2m", "未知")
        humidity = w_data.get("relative_humidity_2m", "未知")
        wind = w_data.get("wind_speed_10m", "未知")
        code = w_data.get("weather_code", 0)

        # WMO 天气代码 -> 中文描述
        desc_map = {
            0: "晴", 1: "大致晴朗", 2: "局部多云", 3: "阴",
            45: "雾", 48: "凇雾",
            51: "小毛毛雨", 53: "毛毛雨", 55: "大毛毛雨",
            61: "小雨", 63: "中雨", 65: "大雨",
            71: "小雪", 73: "中雪", 75: "大雪",
            80: "阵雨", 81: "强阵雨", 82: "暴雨",
            95: "雷暴", 96: "雷暴伴小冰雹", 99: "雷暴伴大冰雹",
        }
        desc = desc_map.get(code, f"代码{code}")

        return (
            f"📍 {city_name}{('，' + country) if country else ''}\n"
            f"🌡️ 温度: {temp}°C\n"
            f"💧 湿度: {humidity}%\n"
            f"💨 风速: {wind} km/h\n"
            f"☁️ 天气: {desc}"
        )
    except requests.exceptions.RequestException as e:
        return f"网络请求错误: {e}"
    except Exception as e:
        return f"查询天气时发生错误: {e}"