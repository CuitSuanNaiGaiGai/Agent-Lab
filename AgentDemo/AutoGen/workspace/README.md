# 城市天气状态显示应用

基于 Streamlit 的轻量级天气查询 Web 应用：输入城市名称即可查看该城市的**当前天气状况**与**未来 7 天天气预报**，并支持一键刷新。

数据来源为免费公开接口 [Open-Meteo](https://open-meteo.com/)，**无需申请 API Key**。

## 功能特性

1. **城市输入**：支持中文 / 英文城市名，回车或点击「🔍 查询天气」即可查询；默认示例城市为「北京」，打开页面即可自动体验。
2. **当前天气**：城市（含省份 / 国家）、天气状况（中文）、当前温度、体感温度、相对湿度、风速、降水量、天气更新时间与数据获取时间。
3. **未来预报**：未来 7 天逐日的日期（含星期）、天气状况、最高温、最低温、降雨概率，并提供可展开的明细表格。
4. **刷新功能**：「🔄 刷新天气」按钮会绕过缓存，强制重新请求天气数据。
5. **加载状态**：所有网络请求期间通过 `st.spinner("正在获取天气数据，请稍候...")` 显示加载提示。
6. **错误处理**：城市为空、城市不存在、网络超时、断网、API 限流（429）、服务端异常（5xx）、返回数据字段缺失或无法解析等情况全部转为友好提示（`st.error` / `st.warning` / `st.info`），页面不会崩溃，也不会暴露 Python 堆栈。
7. **结果缓存**：地理编码缓存 30 分钟，天气数据缓存 10 分钟，减少对外部 API 的重复请求。

## 安装与启动

```bash
pip install -r requirements.txt
streamlit run app.py
```

启动后浏览器访问终端提示的地址（默认 http://localhost:8501）。

## 项目结构

```text
weather-app/
├── app.py            # 唯一入口：页面渲染 + 数据获取 + 缓存 + 错误处理
├── requirements.txt  # 依赖：streamlit、requests
└── README.md         # 本说明文件
```

## 技术说明

- 地理编码接口：`https://geocoding-api.open-meteo.com/v1/search?name={city}&count=5&language=zh&format=json`
- 天气预报接口：`https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=...&daily=...&timezone=auto&forecast_days=7`
- 所有 HTTP 请求统一设置 `timeout=10` 秒，不允许多余的无超时请求。
- 使用 `@st.cache_data(ttl=...)` 缓存；「刷新天气」通过更新 `cache_token` 改变缓存 key，实现强制绕过缓存。
- 温度单位 `°C`、风速单位 `km/h`、湿度单位 `%` 均直接取自接口 `current_units` / `daily_units` 并在界面明确显示。
- WMO 天气代码已映射为中文，例如 `0 → 晴`、`2 → 局部多云`、`61 → 小雨`、`95 → 雷阵雨`。

## 注意事项

- 需要可访问外网的运行环境，否则页面会给出「网络连接失败」提示，而不会白屏或报错堆栈。
- 缓存有效期内重复点击「查询天气」不会重复请求外部 API；需要最新数据请点击「刷新天气」。
- 城市重名时（如输入区县级名称）取地理编码返回的第一个结果，页面会同时显示省份与国家信息便于确认。
