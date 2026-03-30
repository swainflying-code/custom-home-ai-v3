# 成交魔方 V3 - README
# 让每一个客户，都走到成交

## 🎯 四大引擎

| 引擎 | 功能 |
|------|------|
| 客户诊断引擎 | 结构化采集需求，输出客户画像、预算敏感度、风格倾向与成交风险 |
| 方案引导引擎 | 基于可交付产品与工艺库，帮助客户快速确认风格、功能、材质和颜色方向 |
| 预算锚定引擎 | 提供可解释的预算区间、方案分级和价格影响因素，减少无效报价和预算错配 |
| 成交推进引擎 | 自动追踪客户阶段、阻塞点和下一步动作，为销售提供个性化跟进建议 |

## 🚀 快速部署

### 1. 数据库（Supabase）
在 Supabase SQL Editor 执行 `supabase_schema_v3.sql`

## 📁 项目结构
```
custom-home-ai-v3/
├── streamlit_app.py        # 主入口
├── requirements.txt
├── supabase_schema_v3.sql  # 建表脚本
├── core/
│   ├── config.py           # 配置管理
│   ├── database.py         # Supabase 操作
│   ├── ai_service.py       # AI 三大 Prompt
│   ├── auth.py             # 认证
│   └── cache.py            # 缓存
├── pages/
│   ├── customer_diagnosis.py  # 客户诊断引擎 ✅
│   ├── solution_guide.py      # 方案引导引擎 🚧
│   ├── budget_anchor.py       # 预算锚定引擎 🚧
│   ├── deal_push.py           # 成交推进引擎 🚧
│   └── statistics.py          # 数据统计+周报 ✅
└── utils/
    └── logger.py
```
