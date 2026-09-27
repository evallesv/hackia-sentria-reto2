.PHONY: setup dev format check test eval contracts lock tools-pdf
setup:
	uv sync --locked --all-groups
dev:
	uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
format:
	uv run ruff check --fix .
	uv run ruff format .
check:
	uv run ruff check .
	uv run ruff format --check .
	uv run pytest -q
	uv run python -m scripts.evaluate
test:
	uv run pytest -q
eval:
	uv run python -m scripts.evaluate
contracts:
	uv run python -m scripts.export_contracts
lock:
	uv lock
	uv export --no-header --frozen --no-dev --no-emit-project --output-file requirements.txt
tools-pdf:
	uv run --group documents python -m scripts.build_tools_pdf
