-- AutifyME Database Schema
-- This creates all the tables needed for the cataloging workflow

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "vector";

-- Business profiles table
CREATE TABLE IF NOT EXISTS business_profiles (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    industry VARCHAR(100),
    website VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Product drafts (awaiting approval)
CREATE TABLE IF NOT EXISTS product_drafts (
    id VARCHAR(255) PRIMARY KEY,
    business_id UUID NOT NULL REFERENCES business_profiles(id),
    features JSONB NOT NULL,
    image_urls TEXT[] NOT NULL,
    confidence_score DECIMAL(3,2) CHECK (confidence_score >= 0 AND confidence_score <= 1),
    status VARCHAR(50) DEFAULT 'pending',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Final catalog entries (approved products)
CREATE TABLE IF NOT EXISTS catalog_entries (
    id VARCHAR(255) PRIMARY KEY,
    business_id UUID NOT NULL REFERENCES business_profiles(id),
    product_draft_id VARCHAR(255) REFERENCES product_drafts(id),
    features JSONB NOT NULL,
    image_urls TEXT[] NOT NULL,
    status VARCHAR(50) DEFAULT 'active',
    approved_by VARCHAR(255) NOT NULL,
    approved_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Workflow states
CREATE TABLE IF NOT EXISTS workflow_states (
    workflow_id VARCHAR(255) PRIMARY KEY,
    business_id UUID NOT NULL REFERENCES business_profiles(id),
    workflow_type VARCHAR(100) NOT NULL,
    status VARCHAR(50) NOT NULL,
    current_step VARCHAR(100) NOT NULL,
    data JSONB DEFAULT '{}',
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Approval requests (HITL)
CREATE TABLE IF NOT EXISTS approval_requests (
    id VARCHAR(255) PRIMARY KEY,
    workflow_id VARCHAR(255) NOT NULL REFERENCES workflow_states(workflow_id),
    step_name VARCHAR(100) NOT NULL,
    description TEXT NOT NULL,
    data_to_approve JSONB NOT NULL,
    requested_by VARCHAR(255) NOT NULL,
    requested_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    approved_by VARCHAR(255),
    approved_at TIMESTAMP WITH TIME ZONE,
    status VARCHAR(50) DEFAULT 'pending'
);

-- Audit trail
CREATE TABLE IF NOT EXISTS audit_entries (
    id VARCHAR(255) PRIMARY KEY,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    actor VARCHAR(255) NOT NULL,
    action VARCHAR(100) NOT NULL,
    resource VARCHAR(100) NOT NULL,
    resource_id VARCHAR(255),
    business_id UUID REFERENCES business_profiles(id),
    details JSONB DEFAULT '{}',
    ip_address INET,
    user_agent TEXT
);

-- Cost tracking
CREATE TABLE IF NOT EXISTS cost_entries (
    id VARCHAR(255) PRIMARY KEY,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    business_id UUID NOT NULL REFERENCES business_profiles(id),
    operation_type VARCHAR(100) NOT NULL,
    provider VARCHAR(50) NOT NULL,
    model VARCHAR(100) NOT NULL,
    tokens_used INTEGER NOT NULL,
    cost_usd DECIMAL(10,6) NOT NULL,
    workflow_id VARCHAR(255) REFERENCES workflow_states(workflow_id)
);

-- Performance metrics
CREATE TABLE IF NOT EXISTS performance_metrics (
    id VARCHAR(255) PRIMARY KEY,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    metric_name VARCHAR(100) NOT NULL,
    value DECIMAL(15,6) NOT NULL,
    unit VARCHAR(20) NOT NULL,
    business_id UUID REFERENCES business_profiles(id),
    workflow_id VARCHAR(255) REFERENCES workflow_states(workflow_id),
    additional_data JSONB DEFAULT '{}'
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_product_drafts_business_id ON product_drafts(business_id);
CREATE INDEX IF NOT EXISTS idx_product_drafts_status ON product_drafts(status);
CREATE INDEX IF NOT EXISTS idx_catalog_entries_business_id ON catalog_entries(business_id);
CREATE INDEX IF NOT EXISTS idx_workflow_states_business_id ON workflow_states(business_id);
CREATE INDEX IF NOT EXISTS idx_workflow_states_status ON workflow_states(status);
CREATE INDEX IF NOT EXISTS idx_audit_entries_business_id ON audit_entries(business_id);
CREATE INDEX IF NOT EXISTS idx_audit_entries_timestamp ON audit_entries(timestamp);

-- Row Level Security (RLS) for multi-tenancy
ALTER TABLE business_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE product_drafts ENABLE ROW LEVEL SECURITY;
ALTER TABLE catalog_entries ENABLE ROW LEVEL SECURITY;
ALTER TABLE workflow_states ENABLE ROW LEVEL SECURITY;
ALTER TABLE approval_requests ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_entries ENABLE ROW LEVEL SECURITY;
ALTER TABLE cost_entries ENABLE ROW LEVEL SECURITY;
ALTER TABLE performance_metrics ENABLE ROW LEVEL SECURITY;

-- RLS Policies (users can only see their own business data)
CREATE POLICY "Users can view own business" ON business_profiles
    FOR ALL USING (auth.uid()::text = id::text);

CREATE POLICY "Users can view own product drafts" ON product_drafts
    FOR ALL USING (business_id IN (
        SELECT id FROM business_profiles WHERE auth.uid()::text = id::text
    ));

CREATE POLICY "Users can view own catalog entries" ON catalog_entries
    FOR ALL USING (business_id IN (
        SELECT id FROM business_profiles WHERE auth.uid()::text = id::text
    ));

-- Similar policies for other tables...
-- (In production, we'd add policies for all tables)