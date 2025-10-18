-- CPT Codes (Procedure codes)
CREATE TABLE IF NOT EXISTS cpt_codes (
    code VARCHAR(10) PRIMARY KEY,
    description TEXT NOT NULL,
    category VARCHAR(50),
    status VARCHAR(20) DEFAULT 'active'
);

-- ICD-10 Procedure Codes
CREATE TABLE IF NOT EXISTS icd10_procedure_codes (
    code VARCHAR(20) PRIMARY KEY,
    description TEXT NOT NULL,
    category VARCHAR(50),
    status VARCHAR(20) DEFAULT 'active'
);

-- ICD-10 Diagnosis Codes
CREATE TABLE IF NOT EXISTS icd10_diagnosis_codes (
    code VARCHAR(20) PRIMARY KEY,
    description TEXT NOT NULL,
    category VARCHAR(50),
    status VARCHAR(20) DEFAULT 'active'
);

-- Policy-Code Mapping
CREATE TABLE IF NOT EXISTS policy_code_mapping (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    policy_id VARCHAR(50) NOT NULL,
    code_type VARCHAR(20) NOT NULL,
    code VARCHAR(20) NOT NULL,
    requirement_type VARCHAR(50) NOT NULL
);

-- Indexes for faster lookups
CREATE INDEX IF NOT EXISTS idx_policy_lookup ON policy_code_mapping(policy_id, code_type);
CREATE INDEX IF NOT EXISTS idx_code_lookup ON policy_code_mapping(code);
CREATE INDEX IF NOT EXISTS idx_cpt_status ON cpt_codes(status);
CREATE INDEX IF NOT EXISTS idx_icd10proc_status ON icd10_procedure_codes(status);
CREATE INDEX IF NOT EXISTS idx_icd10diag_status ON icd10_diagnosis_codes(status);