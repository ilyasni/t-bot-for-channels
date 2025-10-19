-- Migration: Add evaluation tables for bot quality assessment
-- Created: 2025-10-17
-- Description: Adds tables for golden dataset storage and evaluation runs tracking

-- ============================================================================
-- Golden Dataset Table
-- ============================================================================

CREATE TABLE IF NOT EXISTS evaluation_golden_dataset (
    id SERIAL PRIMARY KEY,
    dataset_name VARCHAR(255) NOT NULL,
    item_id VARCHAR(255) UNIQUE NOT NULL,
    category VARCHAR(100) NOT NULL,
    
    -- Input data for bot
    input_data JSONB NOT NULL,
    query TEXT NOT NULL,
    telegram_context JSONB NOT NULL,
    
    -- Expected output
    expected_output TEXT NOT NULL,
    retrieved_contexts JSONB,
    
    -- Metadata
    metadata JSONB DEFAULT '{}',
    difficulty VARCHAR(20), -- beginner, intermediate, advanced, expert
    tone VARCHAR(20), -- technical, professional, casual, friendly, formal
    requires_multi_source BOOLEAN DEFAULT FALSE,
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ,
    
    -- Constraints
    CONSTRAINT valid_difficulty CHECK (difficulty IN ('beginner', 'intermediate', 'advanced', 'expert')),
    CONSTRAINT valid_tone CHECK (tone IN ('technical', 'professional', 'casual', 'friendly', 'formal'))
);

-- ============================================================================
-- Evaluation Runs Table
-- ============================================================================

CREATE TABLE IF NOT EXISTS evaluation_runs (
    id SERIAL PRIMARY KEY,
    run_name VARCHAR(255) UNIQUE NOT NULL,
    dataset_name VARCHAR(255) NOT NULL,
    model_provider VARCHAR(50) NOT NULL, -- gigachat, openrouter
    model_name VARCHAR(100) NOT NULL,
    
    -- Configuration
    parallel_workers INTEGER DEFAULT 4,
    timeout_seconds INTEGER DEFAULT 300,
    
    -- Status tracking
    status VARCHAR(20) DEFAULT 'pending', -- pending, running, completed, failed, timeout
    progress FLOAT DEFAULT 0.0 CHECK (progress >= 0.0 AND progress <= 1.0),
    
    -- Results
    total_items INTEGER DEFAULT 0,
    processed_items INTEGER DEFAULT 0,
    successful_items INTEGER DEFAULT 0,
    failed_items INTEGER DEFAULT 0,
    
    -- Scores
    avg_score FLOAT,
    scores JSONB, -- Detailed scores per metric
    
    -- Timestamps
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT valid_status CHECK (status IN ('pending', 'running', 'completed', 'failed', 'timeout')),
    CONSTRAINT valid_model_provider CHECK (model_provider IN ('gigachat', 'openrouter', 'openai', 'anthropic'))
);

-- ============================================================================
-- Evaluation Results Table
-- ============================================================================

CREATE TABLE IF NOT EXISTS evaluation_results (
    id SERIAL PRIMARY KEY,
    run_id INTEGER REFERENCES evaluation_runs(id) ON DELETE CASCADE,
    item_id VARCHAR(255) NOT NULL,
    
    -- Input/Output
    query TEXT NOT NULL,
    expected_output TEXT NOT NULL,
    actual_output TEXT NOT NULL,
    retrieved_contexts JSONB,
    
    -- Telegram context
    telegram_context JSONB NOT NULL,
    
    -- Metrics scores
    answer_correctness FLOAT,
    faithfulness FLOAT,
    context_relevance FLOAT,
    factual_correctness FLOAT,
    channel_context_awareness FLOAT,
    group_synthesis_quality FLOAT,
    multi_source_coherence FLOAT,
    tone_appropriateness FLOAT,
    overall_score FLOAT,
    
    -- Evaluation metadata
    evaluation_time FLOAT, -- Seconds
    model_used VARCHAR(100),
    error_message TEXT,
    debug_info JSONB DEFAULT '{}',
    
    -- Timestamps
    evaluated_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT valid_scores CHECK (
        (answer_correctness IS NULL OR (answer_correctness >= 0.0 AND answer_correctness <= 1.0)) AND
        (faithfulness IS NULL OR (faithfulness >= 0.0 AND faithfulness <= 1.0)) AND
        (context_relevance IS NULL OR (context_relevance >= 0.0 AND context_relevance <= 1.0)) AND
        (factual_correctness IS NULL OR (factual_correctness >= 0.0 AND factual_correctness <= 1.0)) AND
        (channel_context_awareness IS NULL OR (channel_context_awareness >= 0.0 AND channel_context_awareness <= 1.0)) AND
        (group_synthesis_quality IS NULL OR (group_synthesis_quality >= 0.0 AND group_synthesis_quality <= 1.0)) AND
        (multi_source_coherence IS NULL OR (multi_source_coherence >= 0.0 AND multi_source_coherence <= 1.0)) AND
        (tone_appropriateness IS NULL OR (tone_appropriateness >= 0.0 AND tone_appropriateness <= 1.0)) AND
        (overall_score IS NULL OR (overall_score >= 0.0 AND overall_score <= 1.0))
    )
);

-- ============================================================================
-- Indexes for Performance
-- ============================================================================

-- Golden Dataset indexes
CREATE INDEX IF NOT EXISTS idx_golden_dataset_name ON evaluation_golden_dataset(dataset_name);
CREATE INDEX IF NOT EXISTS idx_golden_dataset_category ON evaluation_golden_dataset(category);
CREATE INDEX IF NOT EXISTS idx_golden_dataset_created_at ON evaluation_golden_dataset(created_at);
CREATE INDEX IF NOT EXISTS idx_golden_dataset_difficulty ON evaluation_golden_dataset(difficulty);

-- Evaluation Runs indexes
CREATE INDEX IF NOT EXISTS idx_evaluation_runs_name ON evaluation_runs(run_name);
CREATE INDEX IF NOT EXISTS idx_evaluation_runs_dataset ON evaluation_runs(dataset_name);
CREATE INDEX IF NOT EXISTS idx_evaluation_runs_status ON evaluation_runs(status);
CREATE INDEX IF NOT EXISTS idx_evaluation_runs_provider ON evaluation_runs(model_provider);
CREATE INDEX IF NOT EXISTS idx_evaluation_runs_started_at ON evaluation_runs(started_at);
CREATE INDEX IF NOT EXISTS idx_evaluation_runs_created_at ON evaluation_runs(created_at);

-- Evaluation Results indexes
CREATE INDEX IF NOT EXISTS idx_evaluation_results_run_id ON evaluation_results(run_id);
CREATE INDEX IF NOT EXISTS idx_evaluation_results_item_id ON evaluation_results(item_id);
CREATE INDEX IF NOT EXISTS idx_evaluation_results_overall_score ON evaluation_results(overall_score);
CREATE INDEX IF NOT EXISTS idx_evaluation_results_evaluated_at ON evaluation_results(evaluated_at);

-- ============================================================================
-- Triggers for Updated At
-- ============================================================================

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Trigger for golden dataset
DROP TRIGGER IF EXISTS update_golden_dataset_updated_at ON evaluation_golden_dataset;
CREATE TRIGGER update_golden_dataset_updated_at
    BEFORE UPDATE ON evaluation_golden_dataset
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- Sample Data (Optional)
-- ============================================================================

-- Insert sample categories for reference
INSERT INTO evaluation_golden_dataset (
    dataset_name, item_id, category, input_data, query, telegram_context,
    expected_output, metadata, difficulty, tone
) VALUES (
    'sample_dataset', 'sample_001', 'automotive_tech',
    '{"user_id": 123456, "channels": ["@drifting_channel"], "context_type": "single_channel"}',
    'Как настроить дифференциал для дрифта?',
    '{"user_id": 123456, "channels": ["@drifting_channel"], "context_type": "single_channel"}',
    'Для дрифта нужно настроить LSD дифференциал с блокировкой...',
    '{"category": "automotive_tech", "requires_multi_source": false}',
    'advanced',
    'technical'
) ON CONFLICT (item_id) DO NOTHING;

-- ============================================================================
-- Comments for Documentation
-- ============================================================================

COMMENT ON TABLE evaluation_golden_dataset IS 'Golden dataset items for bot evaluation';
COMMENT ON TABLE evaluation_runs IS 'Evaluation runs tracking and configuration';
COMMENT ON TABLE evaluation_results IS 'Detailed results of individual item evaluations';

COMMENT ON COLUMN evaluation_golden_dataset.input_data IS 'JSON input data for bot (query, user_id, channels, etc.)';
COMMENT ON COLUMN evaluation_golden_dataset.telegram_context IS 'Telegram-specific context (channels, groups, context_type)';
COMMENT ON COLUMN evaluation_golden_dataset.retrieved_contexts IS 'Retrieved contexts for RAG evaluation';

COMMENT ON COLUMN evaluation_runs.scores IS 'JSON with detailed scores per metric';
COMMENT ON COLUMN evaluation_runs.progress IS 'Progress from 0.0 to 1.0';

COMMENT ON COLUMN evaluation_results.overall_score IS 'Overall quality score (0.0-1.0)';
COMMENT ON COLUMN evaluation_results.debug_info IS 'JSON with debug information from evaluation';
