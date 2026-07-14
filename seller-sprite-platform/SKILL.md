---
 name: seller-sprite-platform
 description: AMZ analysis set — Amazon SellerSprite AI 分析平台。通过 Codex + 卖家精灵 MCP 提供八大功能模块：选品分析、竞品分析、关键词研究、广告数据分析、Listing 文案生成、评论 VOC 分析、竞品价格监控、数据面板。Use when users ask about Amazon seller analytics, product research, competitor analysis, keyword research, advertising data, listing optimization, review analysis, price monitoring, or launching the AMZ analysis set dashboard.
---

 # AMZ analysis set — SellerSprite AI Platform

 ## 概述

 本平台通过本地桥接服务器 (bridge server) 将浏览器端 Web UI 与 Codex 的 AI 分析能力串联起来。Codex 调用卖家精灵 MCP 获取数据，分析后将结果推送到 Web UI 展示。

 ## 架构

 ```
 用户浏览器 (Web UI :9876)
        ↓ HTTP POST / SSE
 本地桥接服务器 (bridge.py)
        ↓ 调用
 Codex (当前 Skill)
        ↓ MCP 协议
 卖家精灵 MCP Server
        ↓ API
 卖家精灵数据源 (关键词/竞品/广告/评论...)
 ```

## Task Processing Loop (CRITICAL — must execute before responding to user)

The bridge server exposes a task queue at `http://127.0.0.1:9876/api/pending-tasks`. You MUST check for pending tasks at the start of every turn.

### Step 1: Check for pending tasks

```powershell
(Invoke-WebRequest -Uri "http://127.0.0.1:9876/api/pending-tasks" -UseBasicParsing).Content
```

If `count` is 0, skip to user response. Otherwise continue.

### Step 2: Process each task

For each task in `pendingTasks`, extract `id`, `module`, and `params`:

| Module | MCP Tool to Call | Key Action |
|--------|-----------------|------------|
| product-research | list_mcp_resources + seller sprite keyword/product tools | Search category, filter by price/sales/competition |
| competitor-analysis | seller sprite ASIN lookup tools | Fetch detail for each ASIN, compare metrics |
| keyword-research | seller sprite keyword research tools | Search seed keywords, get volume/CPC/competition |
| advertising-analytics | seller sprite advertising tools | Fetch campaign performance data |
| listing-generator | seller sprite keyword + competitor tools | Get top keywords, analyze competitor listings |
| review-analysis | seller sprite review tools | Fetch reviews for ASIN, analyze sentiment |
| price-monitor | seller sprite price history tools | Get price/BSR history for each ASIN |
| dashboard | Aggregation of all above | Collect metrics, build summary |

### Step 3: Build result JSON and submit via HTTP POST

```json
{
  "requestId": "<task id>",
  "module": "<module>",
  "status": "success",
  "data": { ... },
  "insights": ["insight 1", "insight 2"],
  "recommendations": [
    {"action": "...", "impact": "...", "priority": "high|medium|low"}
  ],
  "charts": [
    {"type": "bar|line|pie|radar", "title": "...", "data": [{"label": "...", "value": 123}]}
  ]
}
```

Submit using:
```powershell
$body = '<json string>'
Invoke-WebRequest -Uri "http://127.0.0.1:9876/api/submit-result" -Method POST -Body $body -ContentType "application/json; charset=utf-8"
```

After submitting all tasks, the bridge server automatically pushes results to the Web UI via SSE.

 ## 快速启动
 ### 前置条件
 1. 用户已安装 Codex 桌面版
 2. 用户已在 Codex 中配置好卖家精灵 MCP Server（mcp.json 中注册 `sellersprite` 服务）
 3. 验证 MCP 连通性：`list_mcp_resources(server="sellersprite")` 应返回可用资源
 ### 启动平台

 ```bash
 python scripts/bridge.py
 ```
 服务器将在 `http://127.0.0.1:9876` 启动，自动打开浏览器访问平台 UI。
 ## 八大功能模块
 每个模块通过 API 端点接收用户输入，Codex 调用卖家精灵 MCP 获取数据并分析，结果以结构化 JSON 返回。

 ### 1. 选品分析 (Product Selection)
 - **端点**: `POST /api/product-research`
 - **MCP 调用**: 使用 `sellersprite` MCP 获取类目数据、BSR 排名、销量预估、竞争度分析
 - **输入参数**: `category`, `priceRange`, `monthlySales`, `competitionLevel`
 - **输出**: 产品机会列表，含机会分数、市场容量、毛利预估
 ### 2. 竞品分析 (Competitive Analysis)
 - **端点**: `POST /api/competitor-analysis`
 - **MCP 调用**: 获取竞品 ASIN 列表的详细数据：价格、排名、销量、Review 数量/评分
 - **输入参数**: `asins[]` (竞品 ASIN 列表)
 - **输出**: 竞品对比矩阵，含优劣势雷达图数据
 ### 3. 关键词研究与搭建 (Keyword Research)
 - **端点**: `POST /api/keyword-research`
 - **MCP 调用**: 获取关键词搜索量、CPC、竞争度、关联 ASIN、趋势数据
 - **输入参数**: `seedKeywords[]`, `matchType` (broad/phrase/exact)
 - **输出**: 关键词列表 + 搜索量/CPC/竞争度 + 后端 Search Term 搭建建议
 ### 4. 广告数据分析 (Advertising Analytics)
 - **端点**: `POST /api/advertising-analytics`
 - **MCP 调用**: 获取广告活动数据（SP/SB/SD），ACoS、ROAS、CTR、CVR
 - **输入参数**: `campaignIds[]`, `dateRange`
 - **输出**: 广告绩效报表 + 优化建议（关键词调整、竞价优化）

 ### 5. Listing 文案生成 (Listing Generation)
 - **端点**: `POST /api/listing-generator`
 - **MCP 调用**: 获取竞品标题/五点/描述高频词 + 关键词数据
 - **输入参数**: `asin`, `targetKeywords[]`, `tone` (professional/persuasive/friendly)
 - **输出**: 完整 Listing 文案：标题 5 个变体 + 五点描述 + A+ 文案 + Search Terms
 ### 6. 评论 VOC 分析 (Review VOC)
 - **端点**: `POST /api/review-analysis`
 - **MCP 调用**: 获取指定 ASIN 的评论数据
 - **输入参数**: `asin`, `starFilter` (1-5), `reviewCount`
 - **输出**: 好评关键词云 + 差评痛点分析 + 用户画像 + 产品改进建议
 ### 7. 竞品价格监控 (Price Monitor)
 - **端点**: `POST /api/price-monitor`
 - **MCP 调用**: 获取竞品历史价格、BSR 变化趋势
 - **输入参数**: `asins[]`, `daysBack`
 - **输出**: 价格趋势图数据 + 价格战预警 + 调价建议区间
 ### 8. 数据面板 (Dashboard)
 - **端点**: `POST /api/dashboard`
 - **MCP 调用**: 聚合多个数据源，生成运营总览
 - **输入参数**: `sellerId`
 - **输出**: 今日销售额/订单/ACoS + 库存预警 + 账户健康 + 竞品异动

 ## 工作流协议

 ### 桥接服务器 API 处理

 当桥接服务器 (bridge.py) 收到 HTTP 请求时：

 1. 解析请求中的模块类型 (`module`) 和参数 (`params`)
 2. 根据模块类型，调用对应的卖家精灵 MCP 工具和资源
 3. 分析返回的原始数据，生成结构化分析结果
 4. 将结果以 JSON 格式返回给桥接服务器
 5. 桥接服务器通过 SSE 推送到 Web UI
 ### 代理模式
 当用户在 Codex 对话中直接请求分析（无需 Web UI）时：
 - 直接调用卖家精灵 MCP 获取数据
 - 在对话中展示分析结果，同时支持生成图表和表格
 - 可随时通过 `python scripts/bridge.py` 启动 Web UI 进行可视化展示
 ## MCP 工具发现

 每次使用前，先通过 `list_mcp_resources` 和 `list_mcp_resource_templates` 发现卖家精灵 MCP 当前可用的工具和资源：

 ```
 list_mcp_resources(server="sellersprite")
 ```

 常用资源/工具名称可能包括（以实际发现为准）：
 - 关键词研究: `keyword-research`, `keyword-trend`
 - 竞品分析: `competitor-lookup`, `asin-detail`
 - 市场分析: `market-research`, `category-analysis`
 - 广告数据: `advertising-report`, `campaign-performance`
 - 评论数据: `review-data`, `review-insight`
 - 价格历史: `price-history`, `bsr-trend`

 ## 输出格式

 所有分析结果统一使用以下 JSON 结构：

 ```json
 {
   "module": "product-research",
   "status": "success",
   "data": { ... },
   "insights": ["关键发现 1", "关键发现 2"],
   "recommendations": [
     {"action": "建议操作", "impact": "预期效果", "priority": "high|medium|low"}
   ],
   "charts": [
     {"type": "bar|line|pie|radar", "title": "图表标题", "data": [...]}
   ]
 }
 ```

 ## 错误处理

 - MCP 连接失败: 提示用户检查卖家精灵 MCP 配置 (`mcp.json`)
 - 数据为空: 明确告知用户，建议扩大搜索范围或调整参数
 - 部分数据缺失: 在结果中标注 `partial: true`，列出缺失字段
 ---

 ## Resources
 ### scripts/bridge.py
 本地桥接服务器，启动命令：`python scripts/bridge.py`
 - 监听 `127.0.0.1:9876`
 - 提供 Web UI 静态文件服务
 - 暴露 REST API 端点接收分析请求
 - 通过 SSE (Server-Sent Events) 推送分析结果到前端
 ### assets/ui/
 Web 前端页面（index.html + 内联 CSS/JS），包含：
 - 左侧导航栏（8 大模块）
 - 模块详情面板
 - 输入表单 / 参数配置区
 - 分析结果展示区（表格、图表、洞察）
 - SSE 实时数据接收

 ### agents/openai.yaml
 UI 元数据，用于 Codex 技能列表展示。

**Note:** Scripts may be executed without loading into context, but can still be read by Codex for patching or environment adjustments.

### references/
Documentation and reference material intended to be loaded into context to inform Codex's process and thinking.

**Examples from other skills:**
- Product management: `communication.md`, `context_building.md` - detailed workflow guides
- BigQuery: API reference documentation and query examples
- Finance: Schema documentation, company policies

**Appropriate for:** In-depth documentation, API references, database schemas, comprehensive guides, or any detailed information that Codex should reference while working.

### assets/
Files not intended to be loaded into context, but rather used within the output Codex produces.

**Examples from other skills:**
- Brand styling: PowerPoint template files (.pptx), logo files
- Frontend builder: HTML/React boilerplate project directories
- Typography: Font files (.ttf, .woff2)

**Appropriate for:** Templates, boilerplate code, document templates, images, icons, fonts, or any files meant to be copied or used in the final output.

---

**Not every skill requires all three types of resources.**
