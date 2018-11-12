FROM python:2

RUN pip install disco-py requests pylru

ADD oumodulesbot.py /
ADD cache.json /

CMD [ "python", "/oumodulesbot.py" ]

