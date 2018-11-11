FROM python:2

RUN pip install disco-py requests pylru

ADD oumodulesbot.py /

CMD [ "python", "/oumodulesbot.py" ]

