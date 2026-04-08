-- =============================================
-- [重复新闻清理脚本]
-- 用途：标记或删除重复/无效的新闻记录
-- 执行前请备份数据库！
-- =============================================

-- 步骤1：查找可能的重复新闻（基于相同的title或link）
-- 按重复程度排序，优先处理高重复度的
SELECT
    title,
    link,
    COUNT(*) as duplicate_count,
    MIN(pub_date) as first_seen,
    MAX(pub_date) as last_seen,
    GROUP_CONCAT(id, ', ') as duplicate_ids
FROM news
GROUP BY title, link
HAVING COUNT(*) > 1
ORDER BY duplicate_count DESC, first_seen DESC
LIMIT 100;

-- 步骤2：查看今日凌晨04:00至今的新闻数量统计
SELECT
    DATE(pub_date) as date,
    COUNT(*) as total_count,
    COUNT(DISTINCT title) as unique_titles,
    COUNT(DISTINCT link) as unique_links
FROM news
WHERE pub_date >= datetime('now', 'start of day', '+4 hours')
GROUP BY DATE(pub_date)
ORDER BY date DESC;

-- 步骤3：查找24小时内发布的重复新闻（可能由任务中断导致）
WITH recent_news AS (
    SELECT
        id,
        title,
        link,
        news_id,
        pub_date,
        ROW_NUMBER() OVER (PARTITION BY news_id ORDER BY created_at DESC) as rn
    FROM news
    WHERE pub_date >= datetime('now', '-24 hours')
)
SELECT * FROM recent_news WHERE rn > 1;

-- 步骤4（可选）：标记重复新闻为已处理（软删除）
-- 保留最新的一条，将其他重复项标记为已处理
-- UPDATE processed_news
-- SET processed_at = datetime('now')
-- WHERE news_id IN (
--     SELECT news_id FROM (
--         SELECT news_id,
--                ROW_NUMBER() OVER (PARTITION BY title, link ORDER BY created_at DESC) as rn
--         FROM news
--         WHERE pub_date >= datetime('now', '-24 hours')
--     ) WHERE rn > 1
-- );

-- 步骤5（可选）：清理raw_news表中已处理但未被标记的记录
-- 这些记录可能导致重复采集
UPDATE raw_news
SET processed = 1
WHERE news_id IN (
    SELECT news_id FROM processed_news
)
AND processed = 0;

-- 步骤6：验证清理结果
SELECT
    'total_news' as metric,
    COUNT(*) as value
FROM news
UNION ALL
SELECT
    'processed_news',
    COUNT(*)
FROM processed_news
UNION ALL
SELECT
    'raw_news_unprocessed',
    COUNT(*)
FROM raw_news
WHERE processed = 0;

-- =============================================
-- 索引优化建议（如未创建）
-- =============================================
-- CREATE INDEX IF NOT EXISTS idx_news_title ON news(title);
-- CREATE INDEX IF NOT EXISTS idx_news_link ON news(link);
-- CREATE INDEX IF NOT EXISTS idx_news_news_id ON news(news_id);
