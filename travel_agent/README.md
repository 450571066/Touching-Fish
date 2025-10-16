# 智能行程规划 Agent

该模块提供一个可扩展的 Agent，用于完成以下任务：

1. **行程规划**：根据用户输入的出发地、目的地、日期与兴趣，通过搜索提供商实时拉取活动与景点信息，自动生成每日行程。  
2. **机票监控**：基于行程与用户偏好，搜索并监控最合适的机票，包括最低价格与积分兑换方案。  
3. **酒店监控**：根据行程安排搜索并监控酒店，支持最低价格、位置优选、性价比或积分兑换等策略。

## 核心组件

- `ItineraryPlanner`：调用通用搜索接口，对用户兴趣做搜索并自动排期生成 `Itinerary`。  
- `FlightMonitor`：封装机票搜索与监控逻辑，支持轮询模式触发回调。  
- `HotelMonitor`：封装酒店搜索与监控逻辑。  
- `TravelAgent`：门面类，组合上述三个子组件。

所有组件都依赖抽象的搜索提供商接口 (`SearchProvider`/`FlightSearchProvider`/`HotelSearchProvider`)，方便接入真实的外部 API。

## 快速开始

```python
from datetime import date, timedelta

from travel_agent import TravelAgent, FlightPreference, HotelPreference, TripRequest
from travel_agent.search import InMemorySearchProvider

provider = InMemorySearchProvider(...)
agent = TravelAgent.from_provider(provider)

request = TripRequest(
    origin="SHA",
    destination="SZX",
    start_date=date.today(),
    end_date=date.today() + timedelta(days=2),
)

itinerary = agent.plan_itinerary(request)
flights = agent.find_flights(request, FlightPreference())
hotels = agent.find_hotels(request, HotelPreference())
```

将 `InMemorySearchProvider` 替换为接入真实数据源的实现，即可得到具备实时能力的行程 Agent。

## 接入 Amadeus 机票 & 酒店 API

经过调研，Amadeus 提供统一的 REST API，可同时检索航班报价与酒店价格，并支持测试环境使用。使用方式如下：

1. 注册 [Amadeus for Developers](https://developers.amadeus.com/) 并创建 API Key，获取 `client_id` 与 `client_secret`。
2. 在代码中创建 `AmadeusConfig` 并实例化 `AmadeusSearchProvider`：

    ```python
    from travel_agent import (
        AmadeusConfig,
        AmadeusSearchProvider,
        TravelAgent,
    )

    config = AmadeusConfig(client_id="YOUR_ID", client_secret="YOUR_SECRET")
    provider = AmadeusSearchProvider(config)
    agent = TravelAgent.from_provider(provider)
    ```

3. `AmadeusSearchProvider` 会自动：

    - 通过 `/v1/security/oauth2/token` 交换访问令牌，并缓存至过期；
    - 调用 `/v2/shopping/flight-offers` 获取机票报价，支持舱位、最大中转次数、常旅客计划等筛选；
    - 调用 `/v2/shopping/hotel-offers` 获取酒店报价，解析房型、膳食、积分兑换等信息；
    - 调用 `/v1/reference-data/locations` 实现通用目的地搜索。

4. 如需只使用单一功能，也可以直接实例化 `AmadeusFlightSearchProvider` 或 `AmadeusHotelSearchProvider` 并传入 `FlightMonitor` / `HotelMonitor`。

> **提示**：Amadeus 的测试环境覆盖全球主要航线与酒店数据。生产环境需要申请更高的配额，并遵循 Amadeus 的合规要求。
