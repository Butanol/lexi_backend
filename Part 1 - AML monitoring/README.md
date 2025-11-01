# Part 1 - AML Monitoring

project/
 ├─ dags/
 │   └─ mas_aml_ingest_dag.py   ← Airflow DAG goes here
 ├─ workers/
 │   ├─ parser.py               ← Text + rule segmentation logic
 │   └─ fetchers.py             ← PDF crawling/downloading logic
 └─ data/
     └─ mas/                    ← Output JSON snapshots
