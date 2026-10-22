-- ============================================
-- AI Content System — Supabase SQL Schema
-- Run this in Supabase SQL Editor
-- ============================================

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ─────────────────────────────────────────
-- TABLE 1: Topics (Research results)
-- ─────────────────────────────────────────
CREATE TABLE IF NOT EXISTS topics (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    topic TEXT NOT NULL,
    source VARCHAR(50) NOT NULL,  -- google_trends, rss, youtube, evergreen
    category VARCHAR(50),          -- technology, finance, lifestyle, etc.
    score FLOAT DEFAULT 0.5,
    date DATE NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Index for fast date queries
CREATE INDEX IF NOT EXISTS idx_topics_date ON topics(date);
CREATE INDEX IF NOT EXISTS idx_topics_topic ON topics(topic);

-- ─────────────────────────────────────────
-- TABLE 2: Content Items
-- ─────────────────────────────────────────
CREATE TABLE IF NOT EXISTS content_items (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    topic_id TEXT,
    content_type VARCHAR(50) NOT NULL,  -- youtube_short, youtube_long, reel, post
    title TEXT NOT NULL,
    script TEXT,
    description TEXT,
    hashtags TEXT[],
    metadata JSONB DEFAULT '{}',
    file_paths JSONB DEFAULT '{}',
    status VARCHAR(30) DEFAULT 'generated',
    -- Status values: generated → ready_to_publish → published / failed
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_content_status ON content_items(status);
CREATE INDEX IF NOT EXISTS idx_content_created ON content_items(created_at);

-- ─────────────────────────────────────────
-- TABLE 3: Published Posts
-- ─────────────────────────────────────────
CREATE TABLE IF NOT EXISTS posts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    content_id UUID REFERENCES content_items(id),
    platform VARCHAR(50) NOT NULL,  -- youtube, instagram, facebook, telegram
    post_url TEXT,
    post_id TEXT,
    status VARCHAR(20) DEFAULT 'success',
    views INTEGER DEFAULT 0,
    likes INTEGER DEFAULT 0,
    comments INTEGER DEFAULT 0,
    published_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_posts_platform ON posts(platform);
CREATE INDEX IF NOT EXISTS idx_posts_published ON posts(published_at);

-- ─────────────────────────────────────────
-- TABLE 4: Daily Stats (Analytics)
-- ─────────────────────────────────────────
CREATE TABLE IF NOT EXISTS daily_stats (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    date DATE NOT NULL UNIQUE,
    topics_researched INTEGER DEFAULT 0,
    content_generated INTEGER DEFAULT 0,
    posts_published INTEGER DEFAULT 0,
    platforms_used TEXT[],
    total_views INTEGER DEFAULT 0,
    total_likes INTEGER DEFAULT 0,
    pipeline_duration_seconds INTEGER,
    notes TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_stats_date ON daily_stats(date);

-- ─────────────────────────────────────────
-- TABLE 5: System Logs (Error tracking)
-- ─────────────────────────────────────────
CREATE TABLE IF NOT EXISTS system_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    level VARCHAR(10) NOT NULL,  -- INFO, WARNING, ERROR, SUCCESS
    module VARCHAR(50),
    message TEXT,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW()
);

-- Keep only last 30 days of logs
CREATE INDEX IF NOT EXISTS idx_logs_created ON system_logs(created_at);

-- ─────────────────────────────────────────
-- ROW LEVEL SECURITY (Keep data safe)
-- ─────────────────────────────────────────
ALTER TABLE topics ENABLE ROW LEVEL SECURITY;
ALTER TABLE content_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE posts ENABLE ROW LEVEL SECURITY;
ALTER TABLE daily_stats ENABLE ROW LEVEL SECURITY;
ALTER TABLE system_logs ENABLE ROW LEVEL SECURITY;

-- Service role can do everything (our backend uses service key)
CREATE POLICY "service_role_all" ON topics FOR ALL USING (true);
CREATE POLICY "service_role_all" ON content_items FOR ALL USING (true);
CREATE POLICY "service_role_all" ON posts FOR ALL USING (true);
CREATE POLICY "service_role_all" ON daily_stats FOR ALL USING (true);
CREATE POLICY "service_role_all" ON system_logs FOR ALL USING (true);

-- ─────────────────────────────────────────
-- VIEWS (Easy reporting)
-- ─────────────────────────────────────────

-- Today's overview
CREATE OR REPLACE VIEW today_overview AS
SELECT 
    COUNT(DISTINCT t.id) as topics_today,
    COUNT(DISTINCT c.id) as content_created,
    COUNT(DISTINCT p.id) as posts_published,
    COUNT(DISTINCT p.platform) as platforms_used
FROM topics t
LEFT JOIN content_items c ON DATE(c.created_at) = CURRENT_DATE
LEFT JOIN posts p ON DATE(p.published_at) = CURRENT_DATE
WHERE t.date = CURRENT_DATE;

-- Weekly performance
CREATE OR REPLACE VIEW weekly_performance AS
SELECT 
    DATE(published_at) as date,
    platform,
    COUNT(*) as posts_count,
    SUM(views) as total_views,
    SUM(likes) as total_likes
FROM posts
WHERE published_at >= NOW() - INTERVAL '7 days'
GROUP BY DATE(published_at), platform
ORDER BY date DESC, posts_count DESC;

-- ─────────────────────────────────────────
-- DONE! Schema created successfully.
-- ─────────────────────────────────────────
SELECT 'Schema created successfully! 🎉' as status;
