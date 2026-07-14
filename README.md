# AMZ-analysis-set
AMZ 分析集合

Skill + 轻量Web UI 

1.使用者需要下载codex并配置好卖家精灵MCP，codex用户访问安装这个Skill，并读取内容进行配置

2.平台连接codex

3.打开平台（集成页面UI）

4.coedx反馈结果到页面

架构：
用户浏览器（平台UI）
        ↓ HTTP/WebSocket
本地服务（桥梁/网关）
        ↓ 调用
Codex CLI / App Server
        ↓ 调用
卖家精灵 MCP
        ↓ 返回
竞品数据 → Codex 分析 → 结果返回平台页面


集成页面UI





平台内容

模块	 	           					实现方式								是否需要外部数据源
选品分析						卖家精灵MCP + Codex				卖家精灵MCP
竞品分析						卖家精灵MCP + Codex				卖家精灵MCP
关键词搭建研究				卖家精灵MCP + Codex				卖家精灵MCP
广告数据分析					上传报表 + Codex分析 + 历史文件记忆	无（用户提供报表）
Listing文案生成				Codex直接生成						无
广告Bulk表格生成				Codex生成							无
评论VOC分析					导入评论数据 + Codex分析				无（用户提供数据/爬虫）
竞品价格监控					Codex自动化脚本 + 定时任务		        需要MCP或爬虫
数据面板						数据分析汇总再分析


本地RAG搭建
将过往的竞品分析报告、广告优化案例、Listing文案模板等知识资产存入这个本地RAG库。之后，当你向Codex提问时，它就能检索这些私有知识，给出更精准、更具你个人业务特色的答案，从而构建一个不断自我进化的“运营大脑”。
