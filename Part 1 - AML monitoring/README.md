# Part 1 - AML Monitoring

Source (MAS Website)
↓
Ingestion Job (HTTP + PDF Fetch)
↓
Document Normalization (PDF → Text)
↓
Rule Extraction (Regex + LLM-assisted summarization)
↓
Versioned Data Product (Rules JSON table + metadata)
↓
Change Detection Policy (Triggers Slack/Teams/Email)

To run:
jigsaw schema publish schemas/mas_aml_rules.yaml
jigsaw job deploy jobs/mas_scrape_job.yaml
jigsaw job run mas_aml_ingest
jigsaw policy apply policies/mas_rule_change.yaml
