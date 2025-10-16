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
