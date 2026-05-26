PRAGMA foreign_keys=ON;

CREATE TABLE IF NOT EXISTS schema_meta (
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS models (
  id INTEGER PRIMARY KEY,
  name TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS reasoning_end_strings (
  id INTEGER PRIMARY KEY,
  transition_text TEXT NOT NULL,
  reasoning_end_str TEXT NOT NULL,
  sha256 TEXT NOT NULL UNIQUE,
  char_length INTEGER NOT NULL,
  created_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS budget_configs (
  id INTEGER PRIMARY KEY,
  thinking_token_budget INTEGER NOT NULL,
  max_tokens INTEGER NOT NULL,
  UNIQUE(thinking_token_budget, max_tokens)
);

CREATE TABLE IF NOT EXISTS eval_runs (
  id INTEGER PRIMARY KEY,
  source_run_id TEXT NOT NULL UNIQUE,
  source_db_path TEXT NOT NULL,
  benchmark TEXT NOT NULL,
  model_id INTEGER NOT NULL REFERENCES models(id),
  string_id INTEGER NOT NULL REFERENCES reasoning_end_strings(id),
  budget_id INTEGER NOT NULL REFERENCES budget_configs(id),
  seed INTEGER,
  decoding_config_hash TEXT,
  notes TEXT NOT NULL DEFAULT '',
  imported_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS attempts (
  id INTEGER PRIMARY KEY,
  run_id INTEGER NOT NULL REFERENCES eval_runs(id) ON DELETE CASCADE,
  item_id TEXT NOT NULL,
  attempt_no INTEGER NOT NULL,
  status TEXT NOT NULL,
  correct INTEGER,
  parsed_answer TEXT,
  target TEXT,
  prompt_tokens INTEGER,
  reasoning_tokens INTEGER NOT NULL,
  output_tokens INTEGER NOT NULL,
  completion_tokens INTEGER,
  total_tokens INTEGER,
  latency_ms INTEGER,
  finish_reason TEXT,
  budget_hit INTEGER NOT NULL,
  reasoning_end_str_seen INTEGER NOT NULL,
  hit_detection_method TEXT NOT NULL,
  raw_reasoning TEXT,
  raw_output TEXT,
  raw_response_json TEXT,
  source_created_at REAL,
  UNIQUE(run_id, item_id, attempt_no)
);

CREATE INDEX IF NOT EXISTS idx_attempts_item ON attempts(item_id);
CREATE INDEX IF NOT EXISTS idx_attempts_correct ON attempts(correct);
CREATE INDEX IF NOT EXISTS idx_attempts_budget_hit ON attempts(budget_hit);

CREATE VIEW IF NOT EXISTS budget_hit_item_summary AS
SELECT
  m.name AS model,
  er.benchmark,
  bc.thinking_token_budget,
  res.sha256 AS string_sha256,
  a.item_id,
  COUNT(*) AS attempts,
  SUM(a.budget_hit) AS budget_hits,
  SUM(CASE WHEN a.correct = 1 THEN 1 ELSE 0 END) AS correct,
  SUM(CASE WHEN a.correct = 0 THEN 1 ELSE 0 END) AS wrong,
  SUM(CASE WHEN a.budget_hit = 1 AND a.correct = 1 THEN 1 ELSE 0 END) AS hit_correct,
  SUM(CASE WHEN a.budget_hit = 1 AND a.correct = 0 THEN 1 ELSE 0 END) AS hit_wrong,
  AVG(a.reasoning_tokens) AS avg_reasoning_tokens,
  AVG(a.output_tokens) AS avg_output_tokens,
  AVG(a.completion_tokens) AS avg_completion_tokens
FROM attempts a
JOIN eval_runs er ON er.id = a.run_id
JOIN models m ON m.id = er.model_id
JOIN budget_configs bc ON bc.id = er.budget_id
JOIN reasoning_end_strings res ON res.id = er.string_id
WHERE a.status = 'completed'
GROUP BY m.name, er.benchmark, bc.thinking_token_budget, res.sha256, a.item_id;

CREATE VIEW IF NOT EXISTS string_eval_summary AS
SELECT
  m.name AS model,
  er.benchmark,
  bc.thinking_token_budget,
  res.sha256 AS string_sha256,
  res.transition_text,
  COUNT(*) AS attempts,
  SUM(CASE WHEN a.correct = 1 THEN 1 ELSE 0 END) AS correct,
  SUM(CASE WHEN a.correct = 0 THEN 1 ELSE 0 END) AS wrong,
  SUM(a.budget_hit) AS budget_hits,
  SUM(CASE WHEN a.budget_hit = 1 AND a.correct = 1 THEN 1 ELSE 0 END) AS hit_correct,
  SUM(CASE WHEN a.budget_hit = 1 AND a.correct = 0 THEN 1 ELSE 0 END) AS hit_wrong,
  SUM(a.prompt_tokens) AS prompt_tokens,
  SUM(a.reasoning_tokens) AS reasoning_tokens,
  SUM(a.output_tokens) AS output_tokens,
  SUM(a.completion_tokens) AS completion_tokens,
  SUM(a.total_tokens) AS total_tokens
FROM attempts a
JOIN eval_runs er ON er.id = a.run_id
JOIN models m ON m.id = er.model_id
JOIN budget_configs bc ON bc.id = er.budget_id
JOIN reasoning_end_strings res ON res.id = er.string_id
WHERE a.status = 'completed'
GROUP BY m.name, er.benchmark, bc.thinking_token_budget, res.sha256, res.transition_text;
