FROM python:3.9.7-slim-buster

ENV FLYWHEEL="/flywheel/v0"
WORKDIR ${FLYWHEEL}
RUN pip install poetry

# Install main deps
COPY pyproject.toml poetry.lock $FLYWHEEL/
RUN poetry install --no-dev --no-root

COPY run.py manifest.json README.md $FLYWHEEL/
COPY fw_gear_qc_migrate_files ${FLYWHEEL}/fw_gear_qc_migrate_files 

# Installing the current project (most likely to change, above install is cached)
RUN poetry install --no-dev

# Configure entrypoint
RUN chmod a+x $FLYWHEEL/run.py
ENTRYPOINT ["poetry","run","python","/flywheel/v0/run.py"]

