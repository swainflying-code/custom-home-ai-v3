-- ================================================================
-- 成交魔方 V3 - Supabase 数据库初始化脚本
-- 在 Supabase SQL Editor 中执行此脚本
-- ================================================================

-- 启用 UUID 扩展
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ── 用户表 ──────────────────────────────────────────────────────
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

-- ── 客户表（V3 核心表）──────────────────────────────────────────
CREATE TABLE IF NOT EXISTS customers (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- A. 客户画像 & 项目概况
    customer_no     VARCHAR(30),
    customer_name   VARCHAR(100) NOT NULL,
    contact         VARCHAR(100) NOT NULL,
    age_range       VARCHAR(20),
    visit_count     VARCHAR(20),
    source_channel  VARCHAR(30),
    source_note     VARCHAR(200),
    house_type      VARCHAR(30),
    house_area      VARCHAR(200),
    renovation_type VARCHAR(30),
    renovation_stage VARCHAR(30),
    order_timeline  VARCHAR(30),
    custom_spaces   TEXT[],           -- 多选：数组
    budget_range    VARCHAR(30),

    -- B. 决策链 & 跟进路径
    visitor_identity    VARCHAR(50),
    decision_maker      VARCHAR(30),
    companion_type      TEXT[],
    next_step           VARCHAR(50),
    next_followup_date  DATE,

    -- C. 需求与偏好标签
    style_preference    TEXT[],
    material_preference TEXT[],
    focus_points        TEXT[],
    compare_brands      VARCHAR(200),
    family_size         VARCHAR(20),

    -- D. 成交判断与状态
    quote_status        VARCHAR(30),
    price_reaction      VARCHAR(50),
    intent_level        VARCHAR(30),
    core_objections     TEXT[],
    departure_status    VARCHAR(30),
    departure_note      VARCHAR(500),
    sales_note          TEXT,
    special_needs       TEXT,

    -- AI 分析结果（缓存）
    ai_card_result      TEXT,
    ai_detail_result    TEXT,

    -- 元数据
    created_by  UUID REFERENCES users(id),
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    updated_at  TIMESTAMPTZ DEFAULT NOW()
);

-- ── 跟进记录表 ───────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS follow_up_records (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    customer_id UUID REFERENCES customers(id) ON DELETE CASCADE,
    follow_type VARCHAR(30),   -- 电话/微信/到店/上门
    content     TEXT,
    result      VARCHAR(100),
    next_action VARCHAR(200),
    followed_by UUID REFERENCES users(id),
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- ── 周报记录表 ───────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS weekly_reports (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    week_start      DATE NOT NULL,
    week_end        DATE NOT NULL,
    total_visits    INT DEFAULT 0,
    total_system    INT DEFAULT 0,
    total_deals     INT DEFAULT 0,
    high_intent     INT DEFAULT 0,
    medium_intent   INT DEFAULT 0,
    low_intent      INT DEFAULT 0,
    overdue_count   INT DEFAULT 0,
    report_content  TEXT,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- ── 索引 ─────────────────────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_customers_customer_no  ON customers(customer_no);
CREATE INDEX IF NOT EXISTS idx_customers_intent_level ON customers(intent_level);
CREATE INDEX IF NOT EXISTS idx_customers_created_at   ON customers(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_customers_next_followup ON customers(next_followup_date);
CREATE INDEX IF NOT EXISTS idx_follow_up_customer_id  ON follow_up_records(customer_id);

-- ── Row Level Security ────────────────────────────────────────────
ALTER TABLE customers ENABLE ROW LEVEL SECURITY;
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE follow_up_records ENABLE ROW LEVEL SECURITY;

-- 允许所有已认证用户读写（简单策略，可按需收紧）
CREATE POLICY "allow_all_authenticated" ON customers
    FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "allow_all_authenticated" ON users
    FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "allow_all_authenticated" ON follow_up_records
    FOR ALL USING (true) WITH CHECK (true);

-- ── 默认管理员账号 ────────────────────────────────────────────────
-- 密码：admin123（bcrypt hash）
-- 如果要在 Supabase 中直接插入，先在系统中生成正确的 hash
-- 也可通过应用登录时自动兜底，无需在数据库预置
-- INSERT INTO users (username, password_hash, display_name, role)
-- VALUES ('admin', '$2b$12$...', '系统管理员', 'admin');

-- ── 完成 ──────────────────────────────────────────────────────────
-- 执行完毕后，在 Streamlit Cloud Secrets 中配置：
-- SUPABASE_URL = "https://xxx.supabase.co"
-- SUPABASE_KEY = "your-anon-key"
-- SUPABASE_JWT_SECRET = "your-jwt-secret"
-- MIMO_API_KEY = "your-mimo-key"
-- MIMO_BASE_URL = "https://api.xiaomimimo.com/v1"
-- MIMO_MODEL = "mimo-v2-pro"
-- SECRET_KEY = "any-random-string"
