PY ?= python3
export PYTHONPATH := src

.PHONY: data retro app test all
data:
	$(PY) -m sprintlens.generate_data
retro:
	$(PY) -m sprintlens.retro_analyzer
app:
	streamlit run app/streamlit_app.py
test:
	$(PY) -m pytest -q
all: data retro test
