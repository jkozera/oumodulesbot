FROM python:3.8

ADD requirements.txt .
RUN pip install -r requirements.txt

ADD oumodulesbot /oumodulesbot
ADD cache.json /

CMD [ "python", "/oumodulesbot/oumodulesbot.py" ]
