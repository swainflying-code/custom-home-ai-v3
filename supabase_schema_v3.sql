-- ================================================================
-- 成交魔方 V3 - Supabase 数据库初始化脚本
-- ⚠️  说明：V3 表名均带 _v3 后缀，可与 V2 旧表在同一 Supabase 项目中共存
--          V2 旧表（customers / design_requests / logs）保留不动，不影响历史数据
-- 在 Supabase SQL Editor 中执行此脚本
-- ================================================================

-- 启用 UUID 扩展
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ── 用户表（复用 V2 的 users 表，不重复建）────────────────────────
-- 如果 V2 的 users 表已存在，V3 直接复用，无需重建
-- 如果是全新 Supabase 项目（从未建过），取消下面注释执行：
/*
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    username VARCHAR(50) UNIQUE NOT NULL,
    password_hash VARCHAR(200) NOT NULL,
    display_name VARCHAR(100),
    role VARCHAR(20) DEFAULT 'user',
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
*/

-- 兼容 V2 的 users 表：确保 display_name 字段存在
ALTER TABLE users ADD COLUMN IF NOT EXISTS display_name VARCHAR(100);
ALTER TABLE users ADD COLUMN IF NOT EXISTS role VARCHAR(20) DEFAULT 'user';
ALTER TABLE users ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE;
ALTER TABLE users ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT NOW();

-- 创建用户表索引
CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "users_allow_authenticated" ON users;
CREATE POLICY "users_allow_authenticated" ON users
    FOR ALL TO anon, authenticated USING (true) WITH CHECK (true);

-- ── 客户表 V3（核心表）──────────────────────────────────────────────
-- 与 V2 的 customers 表完全独立，字段结构全新
CREATE TABLE IF NOT EXISTS customers_v3 (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- A. 客户画像 & 项目概况
    customer_no         VARCHAR(30) UNIQUE,   -- 自动生成，格式 CUS-20260330-001
    customer_name       VARCHAR(100) NOT NULL,
    contact             VARCHAR(100) NOT NULL, -- 电话或微信
    age_range           VARCHAR(20),           -- 30以下/31-40/41-50/51+/未知
    visit_count         VARCHAR(20),           -- 首次/二次/三次以上
    source_channel      VARCHAR(30),           -- 自然进店/转介绍/线上/渠道合作/社区拓客/老客复购
    source_note         VARCHAR(200),          -- 可选备注（如：抖音/小红书/设计师）
    house_type          VARCHAR(30),           -- 普通住宅/改善型住宅/别墅大宅/公寓商住/自建房/未知
    house_area          VARCHAR(200),          -- 房屋区域（文字描述）
    renovation_type     VARCHAR(30),           -- 新装/全屋翻新/局部改造/已入住换柜/未明确
    renovation_stage    VARCHAR(30),           -- 未开始/设计中/拆改水电/硬装完成/已入住改造
    order_timeline      VARCHAR(30),           -- 1周内/2周内/1个月内/1-3个月/3个月后/不明确
    custom_spaces       TEXT[],                -- 多选：橱柜/餐边柜/厅柜/鞋柜等
    budget_range        VARCHAR(30),           -- 5万以下/5-10万/10-20万/20-30万/30万以上/未透露

    -- B. 决策链 & 跟进路径
    visitor_identity    VARCHAR(50),           -- 主决策人本人/配偶/父母/影响者/使用者/代看/不明确
    decision_maker      VARCHAR(30),           -- 本人/配偶/父母/共同决定/不明确
    companion_type      TEXT[],                -- 多选：配偶/父母/孩子/朋友/设计师等
    next_step           VARCHAR(50),           -- 加微信跟进/邀约二次到店/预约上门测量等
    next_followup_date  DATE,                  -- 下次跟进日期

    -- C. 需求与偏好标签
    style_preference    TEXT[],                -- 最多2个：现代简约/轻奢/新中式/原木自然/极简灰系/其他
    material_preference TEXT[],                -- 最多2个：不锈钢/烤漆/木纹/玻璃/岩板等
    focus_points        TEXT[],                -- 最多3个：颜值设计/收纳实用/环保健康等
    compare_brands      VARCHAR(200),          -- 对比品牌（是/否+填写）
    family_size         VARCHAR(20),           -- 1-2人/3-4人/5人以上

    -- D. 成交判断与状态
    quote_status        VARCHAR(30),           -- 未报价/口头报价/初步报价/详细报价
    price_reaction      VARCHAR(50),           -- 接受/偏高但有意向/明确拒绝/未报价/未表态
    intent_level        VARCHAR(30),           -- 高/中/低
    core_objections     TEXT[],                -- 最多2个：价格/风格/材质/环保等
    departure_status    VARCHAR(30),           -- 正向/负向
    departure_note      VARCHAR(500),          -- 备注
    sales_note          TEXT,                  -- 销售备注
    special_needs       TEXT,                  -- 特殊需求补充

    -- AI 分析结果（缓存，避免重复调用）
    ai_card_result      TEXT,                  -- 主卡分析结果
    ai_detail_result    TEXT,                  -- 详情分析结果

    -- 元数据
    created_by  UUID REFERENCES users(id),
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    updated_at  TIMESTAMPTZ DEFAULT NOW()
);

-- ── 跟进记录表 V3 ────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS follow_up_records_v3 (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    customer_id UUID REFERENCES customers_v3(id) ON DELETE CASCADE,
    follow_type VARCHAR(30),   -- 电话/微信/到店/上门
    content     TEXT,
    result      VARCHAR(100),
    next_action VARCHAR(200),
    followed_by UUID REFERENCES users(id),
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- ── 周报记录表 V3 ────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS weekly_reports_v3 (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    week_start      DATE NOT NULL,
    week_end        DATE NOT NULL,
    total_visits    INT DEFAULT 0,    -- 进店总数（手工填入）
    total_system    INT DEFAULT 0,    -- 系统记录数（自动统计）
    total_deals     INT DEFAULT 0,    -- 成交数（手工填入）
    high_intent     INT DEFAULT 0,    -- 高意向客户数
    medium_intent   INT DEFAULT 0,    -- 中意向客户数
    low_intent      INT DEFAULT 0,    -- 低意向客户数
    overdue_count   INT DEFAULT 0,    -- 超3天未跟进数
    report_content  TEXT,             -- AI 生成的周报内容
    created_by      UUID REFERENCES users(id),
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- ── 索引 ──────────────────────────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_customers_v3_no         ON customers_v3(customer_no);
CREATE INDEX IF NOT EXISTS idx_customers_v3_intent     ON customers_v3(intent_level);
CREATE INDEX IF NOT EXISTS idx_customers_v3_created    ON customers_v3(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_customers_v3_followup   ON customers_v3(next_followup_date);
CREATE INDEX IF NOT EXISTS idx_follow_up_v3_customer   ON follow_up_records_v3(customer_id);

-- ── Row Level Security ────────────────────────────────────────────────
ALTER TABLE customers_v3        ENABLE ROW LEVEL SECURITY;
ALTER TABLE follow_up_records_v3 ENABLE ROW LEVEL SECURITY;
ALTER TABLE weekly_reports_v3   ENABLE ROW LEVEL SECURITY;

-- 允许所有已认证用户读写（简单策略）
DROP POLICY IF EXISTS "v3_allow_authenticated" ON customers_v3;
CREATE POLICY "v3_allow_authenticated" ON customers_v3
    FOR ALL USING (true) WITH CHECK (true);
DROP POLICY IF EXISTS "v3_allow_authenticated" ON follow_up_records_v3;
CREATE POLICY "v3_allow_authenticated" ON follow_up_records_v3
    FOR ALL USING (true) WITH CHECK (true);
DROP POLICY IF EXISTS "v3_allow_authenticated" ON weekly_reports_v3;
CREATE POLICY "v3_allow_authenticated" ON weekly_reports_v3
    FOR ALL USING (true) WITH CHECK (true);

-- ── 自动更新 updated_at 触发器 ───────────────────────────────────────
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_customers_v3_updated_at
    BEFORE UPDATE ON customers_v3
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ── 报价记录表 V3（预算锚定 C 模块输出） ───────────────────────────
CREATE TABLE IF NOT EXISTS quotes_v3 (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    customer_id     UUID REFERENCES customers_v3(id) ON DELETE SET NULL,
    customer_name   VARCHAR(100),
    budget_range    VARCHAR(30),
    tier            VARCHAR(20),        -- 经济款/品质款/旗舰款
    total_amount    NUMERIC(12, 2),     -- 报价总额
    quote_detail    TEXT,               -- JSON：各品类计算明细
    report_text     TEXT,               -- 报价单文字版
    created_by      UUID REFERENCES users(id),
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_quotes_v3_customer ON quotes_v3(customer_id);
CREATE INDEX IF NOT EXISTS idx_quotes_v3_created  ON quotes_v3(created_at DESC);

ALTER TABLE quotes_v3 ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "v3_allow_authenticated" ON quotes_v3;
CREATE POLICY "v3_allow_authenticated" ON quotes_v3
    FOR ALL USING (true) WITH CHECK (true);

-- ── 完成 ──────────────────────────────────────────────────────────────
-- 执行完毕提示：
-- ✅ customers_v3    - 客户诊断主表（V3 四板块，33字段）
-- ✅ follow_up_records_v3 - 跟进记录
-- ✅ weekly_reports_v3    - 老板周报存档
-- ✅ quotes_v3            - 预算锚定报价记录（C 模块）
-- ⚠️  users 表：V2已有则复用；全新项目取消上方注释执行
--
-- Streamlit Cloud Secrets 配置：
-- SUPABASE_URL = "https://xxx.supabase.co"
-- SUPABASE_KEY = "your-anon-key"
-- SUPABASE_JWT_SECRET = "your-jwt-secret"
-- MIMO_API_KEY = "your-mimo-key"
-- MIMO_BASE_URL = "https://api.xiaomimimo.com/v1"
-- MIMO_MODEL = "mimo-v2-pro"
-- SECRET_KEY = "any-random-string"
