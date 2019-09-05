FROM python:3.6

RUN pip install -r requirements.txt

ADD oumodulesbot.py /
ADD cache.json /

CMD [ "python", "/oumodulesbot.py" ]

