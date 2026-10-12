# ---------------------------------------------------------------------------
# One-command reproducibility.  Requires: uv (https://docs.astral.sh/uv/)
#   make data    -> generate the synthetic raw events (seeded, deterministic)
#   make models  -> build dbt models + tests on DuckDB
#   make report  -> run the Bayesian analysis notebook -> reports/
#   make test    -> dbt tests + pytest (effect-recovery test)
#   make app     -> launch the Streamlit dashboard
#   make all     -> data -> models -> report
# ---------------------------------------------------------------------------
.PHONY: all data models report test app clean

DBT = uv run dbt build --project-dir dbt --profiles-dir dbt
DBT_TEST = uv run dbt test --project-dir dbt --profiles-dir dbt

all: data models report

data:
	uv run python src/simulate.py

models:
	$(DBT)

report:
	uv run python src/analyze.py

test:
	$(DBT_TEST)
	uv run pytest -q

app:
	uv run streamlit run app/dashboard.py

clean:
	uv run python -c "import glob,os,shutil; [os.remove(f) for f in glob.glob('data/raw/*.parquet')+glob.glob('*.duckdb')]; [shutil.rmtree(d, ignore_errors=True) for d in ('dbt/target','dbt/logs')]"
