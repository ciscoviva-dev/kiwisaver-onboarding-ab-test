# ---------------------------------------------------------------------------
# One-command reproducibility.  Requires: uv (https://docs.astral.sh/uv/)
#   make data       -> generate the synthetic raw events (seeded, deterministic)
#   make models     -> build dbt models + tests on DuckDB
#   make report     -> figures + results.json (reports/)
#   make notebooks  -> execute notebooks and render to HTML (docs/)
#   make test       -> dbt tests + pytest (effect-recovery test)
#   make all        -> data -> models -> report -> notebooks
# ---------------------------------------------------------------------------
.PHONY: all data models report notebooks test clean

DBT = uv run dbt build --project-dir dbt --profiles-dir dbt
DBT_TEST = uv run dbt test --project-dir dbt --profiles-dir dbt

all: data models report notebooks

data:
	uv run python src/simulate.py

models:
	$(DBT)

report:
	uv run python src/analyze.py

notebooks:
	uv run python src/render_notebooks.py

test:
	$(DBT_TEST)
	uv run pytest -q

clean:
	uv run python -c "import glob,os,shutil; [os.remove(f) for f in glob.glob('data/raw/*.parquet')+glob.glob('*.duckdb')]; [shutil.rmtree(d, ignore_errors=True) for d in ('dbt/target','dbt/logs')]"
