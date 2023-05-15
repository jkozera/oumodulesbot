FROM python:3.11

ADD oumodulesbot /oumodulesbot
ADD poetry.lock pyproject.toml cache.json /

RUN pip install $(grep -E '^requires = \[.poetry.*\]$' pyproject.toml | cut -d'"' -f2)
RUN poetry install

CMD [ "poetry", "run", "python", "-m", "oumodulesbot.oumodulesbot" ]
