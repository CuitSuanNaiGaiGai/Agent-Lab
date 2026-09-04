"""城市天气状态显示应用 (Streamlit)

启动方式:
    pip install -r requirements.txt
    streamlit run app.py

数据来源: Open-Meteo 免费公开接口（无需 API Key）
    - 地理编码: https://geocoding-api.open-meteo.com/v1/search
    - 天气预报: https://api.open-meteo.com/v1/forecast
"""

from __future__ import annotations

import datetime as dt
import time
from typing import Any, Dict, List, Optional, Tuple

import requests
import streamlit as st

# ---------------------------------------------------------------------------
# 常量配置
# ---------------------------------------------------------------------------
GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"

REQUEST_TIMEOUT = 10          # 所有外部网络请求统一超时时间（秒）
GEOCODE_CACHE_TTL = 30 * 60   # 地理编码缓存 30 分钟
WEATHER_CACHE_TTL = 10 * 60   # 天气数据缓存 10 分钟
FORECAST_DAYS = 7             # 展示未来 7 天预报
MIN_FORECAST_DAYS = 5         # 至少要有 5 天预报才算数据完整
DEFAULT_CITY = "北京"

# WMO 天气代码 -> (中文描述, 图标)
WEATHER_CODE_ZH: Dict[int, Tuple[str, str]] = {
    0: ("晴", "☀️"),
    1: ("晴间少云", "🌤️"),
    2: ("局部多云", "⛅"),
    3: ("阴", "☁️"),
    45: ("雾", "🌫️"),
    48: ("雾凇", "🌫️"),
    51: ("小毛毛雨", "🌦️"),
    53: ("毛毛雨", "🌦️"),
    55: ("大毛毛雨", "🌧️"),
    56: ("冻毛毛雨", "🌧️"),
    57: ("冻毛毛雨", "🌧️"),
    61: ("小雨", "🌦️"),
    62: ("中雨", "🌧️"),
    63: ("大雨", "🌧️"),
    64: ("暴雨", "🌧️"),
    65: ("特大暴雨", "🌧️"),
    66: ("冻雨", "🌧️"),
    67: ("强冻雨", "🌧️"),
    71: ("小雪", "🌨️"),
    72: ("中雪", "🌨️"),
    73: ("大雪", "❄️"),
    74: ("暴雪", "❄️"),
    75: ("大暴雪", "❄️"),
    77: ("雪粒", "🌨️"),
    80: ("小阵雨", "🌦️"),
    81: ("阵雨", "🌧️"),
    82: ("强阵雨", "🌧️"),
    85: ("小阵雪", "🌨️"),
    86: ("大阵雪", "❄️"),
    95: ("雷阵雨", "⛈️"),
    96: ("雷阵雨伴冰雹", "⛈️"),
    99: ("强雷阵雨伴冰雹", "⛈️"),
}

WEEKDAY_ZH = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]


class WeatherError(Exception):
    """面向用户的友好业务异常（不暴露原始堆栈）。"""


# ---------------------------------------------------------------------------
# 通用工具
# ---------------------------------------------------------------------------
def describe_weather(code: Any) -> Tuple[str, str]:
    """把 WMO 天气代码转换为中文描述与图标。"""
    try:
        code_int = int(code)
    except (TypeError, ValueError):
        return ("未知", "❔")
    return WEATHER_CODE_ZH.get(code_int, (f"未知天气（代码 {code_int}）", "❔"))


def format_number(value: Any, digits: int = 1, unit: str = "", dash: str = "--") -> str:
    """把可能缺失/非数字的值安全格式化。"""
    if value is None:
        return dash
    try:
        return f"{float(value):.{digits}f}{unit}"
    except (TypeError, ValueError):
        return str(value)


def format_probability(value: Any) -> str:
    """降雨概率格式化。"""
    if value is None:
        return "--"
    try:
        return f"{int(round(float(value)))}%"
    except (TypeError, ValueError):
        return str(value)


def human_time(raw: Optional[str]) -> str:
    """把接口返回的 '2024-05-01T13:45' 转成 '2024-05-01 13:45'。"""
    if not raw:
        return "未知"
    return str(raw).replace("T", " ")


def safe_date_label(raw: Optional[str]) -> str:
    """把 '2024-05-01' 转成 '05-01 周三' 这类易读标签。"""
    if not raw:
        return "未知日期"
    try:
        date_obj = dt.datetime.strptime(str(raw)[:10], "%Y-%m-%d").date()
    except ValueError:
        return str(raw)
    label = f"{date_obj.strftime('%m-%d')} {WEEKDAY_ZH[date_obj.weekday()]}"
    if date_obj == dt.date.today():
        return f"{label}（今天）"
    return label


def get_field(data: Any, key: str, context: str) -> Any:
    """读取必需字段，缺失时抛出友好的解析错误而不是 KeyError。"""
    if not isinstance(data, dict) or data.get(key) is None:
        raise WeatherError(
            f"天气数据解析失败：缺少{context}（{key}）信息，请稍后重试或更换城市。"
        )
    return data[key]


def http_get_json(url: str, params: Dict[str, Any], service_name: str) -> Dict[str, Any]:
    """统一 GET 请求：超时、断网、HTTP 错误、JSON 解析错误全部转成友好提示。"""
    try:
        response = requests.get(url, params=params, timeout=REQUEST_TIMEOUT)
    except requests.exceptions.Timeout:
        raise WeatherError(f"{service_name}请求超时，请检查网络后稍后重试。")
    except requests.exceptions.ConnectionError:
        raise WeatherError(f"{service_name}网络连接失败，请确认可访问外网后重试。")
    except requests.exceptions.RequestException:
        raise WeatherError(f"{service_name}暂时不可用，请稍后刷新重试。")

    if response.status_code == 429:
        raise WeatherError(f"{service_name}请求过于频繁（已触发限流），请稍后再试。")
    if response.status_code >= 500:
        raise WeatherError(
            f"{service_name}暂时不可用（服务端 {response.status_code}），请稍后刷新重试。"
        )
    if response.status_code >= 400:
        raise WeatherError(f"{service_name}返回异常（HTTP {response.status_code}），请稍后重试。")

    try:
        payload = response.json()
    except Exception:  # JSONDecodeError 等解码问题
        raise WeatherError(f"{service_name}返回内容无法解析，请稍后重试。")

    if not isinstance(payload, dict):
        raise WeatherError(f"{service_name}返回数据格式异常，请稍后重试。")
    return payload


# ---------------------------------------------------------------------------
# 数据获取（带 Streamlit 缓存）
# cache_token 变化 -> 缓存 key 变化 -> 实现「刷新天气」绕过缓存
# ---------------------------------------------------------------------------
@st.cache_data(ttl=GEOCODE_CACHE_TTL, show_spinner=False)
def geocode_city_cached(city: str, cache_token: float) -> Dict[str, Any]:
    """城市名 -> 经纬度 + 展示名称。"""
    params = {"name": city, "count": 5, "language": "zh", "format": "json"}
    payload = http_get_json(GEOCODE_URL, params, f"城市「{city}」的地理编码服务")

    results = payload.get("results")
    if not results or not isinstance(results, list) or not isinstance(results[0], dict):
        raise WeatherError(
            f"未找到城市「{city}」，请检查输入是否正确（可尝试英文名或市级名称）。"
        )

    first = results[0]
    latitude = get_field(first, "latitude", "纬度")
    longitude = get_field(first, "longitude", "经度")
    name = str(first.get("name") or city)
    admin = str(first.get("admin1") or "")
    country = str(first.get("country") or "")

    display = " · ".join([part for part in [name, admin, country] if part]) or name
    return {
        "name": name,
        "display": display,
        "latitude": float(latitude),
        "longitude": float(longitude),
    }


@st.cache_data(ttl=WEATHER_CACHE_TTL, show_spinner=False)
def fetch_weather_cached(latitude: float, longitude: float, cache_token: float) -> Dict[str, Any]:
    """经纬度 -> 当前天气 + 未来几天预报。"""
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "current": ",".join(
            [
                "temperature_2m",
                "apparent_temperature",
                "relative_humidity_2m",
                "weather_code",
                "wind_speed_10m",
                "precipitation",
            ]
        ),
        "daily": ",".join(
            [
                "weather_code",
                "temperature_2m_max",
                "temperature_2m_min",
                "precipitation_probability_max",
            ]
        ),
        "timezone": "auto",
        "forecast_days": FORECAST_DAYS,
        "temperature_unit": "celsius",
        "wind_speed_unit": "kmh",
    }
    payload = http_get_json(FORECAST_URL, params, "天气服务")

    current = get_field(payload, "current", "当前天气")
    daily = get_field(payload, "daily", "天气预报")
    current_units = payload.get("current_units") or {}
    daily_units = payload.get("daily_units") or {}

    temp_unit = str(current_units.get("temperature_2m") or "°C")
    humidity_unit = str(current_units.get("relative_humidity_2m") or "%")
    wind_unit = str(current_units.get("wind_speed_10m") or "km/h")
    day_temp_unit = str(daily_units.get("temperature_2m_max") or "°C")

    weather_text, weather_icon = describe_weather(current.get("weather_code"))
    current_data = {
        "time": current.get("time"),
        "temperature": get_field(current, "temperature_2m", "当前温度"),
        "apparent_temperature": current.get("apparent_temperature"),
        "humidity": get_field(current, "relative_humidity_2m", "湿度"),
        "wind_speed": get_field(current, "wind_speed_10m", "风速"),
        "precipitation": current.get("precipitation"),
        "weather_text": weather_text,
        "weather_icon": weather_icon,
        "temp_unit": temp_unit,
        "humidity_unit": humidity_unit,
        "wind_unit": wind_unit,
    }

    dates = get_field(daily, "time", "预报日期")
    if not isinstance(dates, list) or len(dates) < MIN_FORECAST_DAYS:
        raise WeatherError("天气数据解析失败：返回的预报天数不足 5 天，请稍后重试。")

    codes = daily.get("weather_code") or []
    highs = daily.get("temperature_2m_max") or []
    lows = daily.get("temperature_2m_min") or []
    probs = daily.get("precipitation_probability_max") or []

    days: List[Dict[str, Any]] = []
    for index, date_str in enumerate(dates[:FORECAST_DAYS]):
        text, icon = describe_weather(codes[index] if index < len(codes) else None)
        high = highs[index] if index < len(highs) else None
        low = lows[index] if index < len(lows) else None
        prob = probs[index] if index < len(probs) else None
        if high is None and low is None:
            raise WeatherError(f"天气数据解析失败：{date_str} 缺少最高/最低气温，请稍后重试。")
        days.append(
            {
                "date_raw": str(date_str),
                "date_label": safe_date_label(date_str),
                "text": text,
                "icon": icon,
                "high": high,
                "low": low,
                "prob": prob,
                "unit": day_temp_unit,
            }
        )

    return {
        "current": current_data,
        "daily": days,
        "timezone": str(payload.get("timezone") or ""),
        "requested_at": dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }


def load_weather(city: str, force_refresh: bool) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """完整查询链路：城市名 -> 地理编码 -> 天气数据。"""
    token = float(st.session_state.get("cache_token", 0.0) or 0.0)
    if force_refresh:
        # 生成新 token，使 st.cache_data 的缓存 key 失效，强制重新请求外部 API
        token = time.time()
        st.session_state["cache_token"] = token

    location = geocode_city_cached(city, token)
    data = fetch_weather_cached(location["latitude"], location["longitude"], token)
    return location, data


# ---------------------------------------------------------------------------
# 页面渲染
# ---------------------------------------------------------------------------
def render_input_area() -> Tuple[str, bool, bool]:
    """渲染标题与输入区域，返回 (城市, 是否点击查询, 是否点击刷新)。"""
    st.title("🌤️ 城市天气状态显示应用")
    st.caption("输入城市名称，查看当前天气状况与未来几天天气预报（数据来源：Open-Meteo）。")

    city = st.text_input(
        "城市名称",
        key="city_input",
        placeholder="例如：北京 / 上海 / Tokyo / London",
        help="支持中文或英文城市名，输入后按回车或点击「查询天气」。",
    )
    city = (city or "").strip()

    query_col, refresh_col, _ = st.columns([1, 1, 4])
    with query_col:
        query_clicked = st.button("🔍 查询天气", type="primary")
    with refresh_col:
        refresh_clicked = st.button("🔄 刷新天气")

    return city, query_clicked, refresh_clicked


def render_current_weather(location: Dict[str, Any], data: Dict[str, Any]) -> None:
    """渲染当前天气卡片。"""
    current = data["current"]

    st.subheader("📍 当前天气")
    line = f"**{location['display']}** ｜ {current['weather_icon']} {current['weather_text']}"
    if data.get("timezone"):
        line += f" ｜ 时区 {data['timezone']}"
    st.markdown(line)

    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.metric("当前温度", format_number(current["temperature"], 1, current["temp_unit"]))
    with m2:
        st.metric(
            "体感温度",
            format_number(current.get("apparent_temperature"), 1, current["temp_unit"]),
        )
    with m3:
        st.metric("相对湿度", format_number(current["humidity"], 0, current["humidity_unit"]))
    with m4:
        st.metric("风速", format_number(current["wind_speed"], 1, f" {current['wind_unit']}"))

    detail_col, time_col = st.columns([3, 2])
    with detail_col:
        st.caption(f"当前降水量：{format_number(current.get('precipitation'), 1, ' mm')}")
    with time_col:
        st.caption(f"天气更新时间：{human_time(current.get('time'))}")

    st.caption(
        "本次数据获取时间："
        + str(data.get("requested_at") or "未知")
        + "（点击「🔄 刷新天气」可绕过缓存重新获取最新数据）"
    )


def render_forecast_table(rows: List[List[str]]) -> None:
    """优先使用 st.dataframe 展示明细表格，参数不兼容时退化为 Markdown 表格。"""
    header = ["日期", "星期", "天气状况", "最高温", "最低温", "降雨概率"]
    try:
        st.dataframe(rows, columns=header, hide_index=True, use_container_width=True)
    except Exception:  # 兼容不同 Streamlit 版本，保证页面不崩
        lines = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
        lines += ["| " + " | ".join(row) + " |" for row in rows]
        st.markdown("\n".join(lines))


def render_forecast(days: List[Dict[str, Any]]) -> None:
    """渲染未来几天天气预报。"""
    st.subheader(f"📅 未来 {len(days)} 天天气预报")

    columns = st.columns(len(days))
    for column, day in zip(columns, days):
        with column:
            st.markdown(f"**{day['date_label']}**")
            st.markdown(f"{day['icon']} {day['text']}")
            st.markdown(
                f"最高 {format_number(day['high'], 1, day['unit'])} ｜ "
                f"最低 {format_number(day['low'], 1, day['unit'])}"
            )
            st.caption(f"降雨概率 {format_probability(day.get('prob'))}")

    with st.expander("查看预报明细表格"):
        rows: List[List[str]] = []
        for day in days:
            rows.append(
                [
                    day["date_raw"],
                    day["date_label"],
                    f"{day['icon']} {day['text']}",
                    format_number(day["high"], 1, day["unit"]),
                    format_number(day["low"], 1, day["unit"]),
                    format_probability(day.get("prob")),
                ]
            )
        render_forecast_table(rows)


def handle_error(exc: Exception) -> None:
    """统一错误处理：转成友好文案并持久化，不输出原始 traceback。"""
    if isinstance(exc, WeatherError):
        st.session_state["error"] = str(exc)
    else:
        st.session_state["error"] = "处理天气数据时出现未知异常，请稍后重试或更换城市查询。"
    st.session_state["result"] = None


def ensure_session_state() -> None:
    """初始化会话状态（不依赖 dict.setdefault，兼容各版本 Streamlit）。"""
    defaults: Dict[str, Any] = {
        "cache_token": 0.0,
        "submitted_city": None,
        "result": None,
        "error": None,
        "city_input": DEFAULT_CITY,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


# ---------------------------------------------------------------------------
# 入口
# ---------------------------------------------------------------------------
def main() -> None:
    st.set_page_config(page_title="城市天气状态显示应用", page_icon="🌤️", layout="wide")
    ensure_session_state()

    city, query_clicked, refresh_clicked = render_input_area()

    # 固定位置的提示区（错误 / 警告 / 引导信息），避免重复渲染
    status_slot = st.empty()

    # 1) 城市为空：不请求任何外部接口，只做友好提示
    if not city:
        st.session_state["submitted_city"] = None
        st.session_state["result"] = None
        st.session_state["error"] = None
        status_slot.warning("请输入城市名称后再查询。")
        return

    # 2) 触发条件：点击查询 / 点击刷新 / 输入了新的城市（回车即查询）
    entered_by_typing = city != st.session_state.get("submitted_city")
    should_query = bool(query_clicked or refresh_clicked or entered_by_typing)

    if should_query:
        st.session_state["submitted_city"] = city
        st.session_state["error"] = None
        try:
            with st.spinner("正在获取天气数据，请稍候..."):
                location, data = load_weather(city, force_refresh=bool(refresh_clicked))
            st.session_state["result"] = {"city": city, "location": location, "data": data}
        except Exception as exc:  # noqa: BLE001 - 统一兜底，保证页面不崩溃
            handle_error(exc)

    error = st.session_state.get("error")
    if error:
        status_slot.error(f"⚠️ {error}")

    result = st.session_state.get("result")
    st.divider()
    if result and result.get("city") == city and result.get("data"):
        render_current_weather(result["location"], result["data"])
        st.divider()
        render_forecast(result["data"]["daily"])
    elif not error:
        status_slot.info("请输入城市名称后点击「🔍 查询天气」。")


if __name__ == "__main__":
    main()
