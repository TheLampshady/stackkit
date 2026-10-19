-include ../.env
export

.PHONY: lab
lab:
	uv run --package notebooks jupyter lab

# The Vertex AI custom container reads a requirements file, so generate it
# from custom_model/pyproject.toml rather than keeping a hand-written copy.
.PHONY: requirements
requirements:
	uv pip compile custom_model/pyproject.toml --python-version 3.13 --no-header -o custom_model/requirements.txt
