FROM python:3.9

ADD oumodulesbot /oumodulesbot
ADD poetry.lock pyproject.toml cache.json /

RUN pip install poetry==1.1.10
RUN poetry install

CMD [ "poetry", "run", "python", "-m", "oumodulesbot.oumodulesbot" ]
