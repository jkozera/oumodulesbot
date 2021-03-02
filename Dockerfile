FROM python:3.9

ADD requirements.txt .
RUN pip install -r requirements.txt

ADD oumodulesbot /oumodulesbot
ADD cache.json /

CMD [ "python", "-m", "oumodulesbot.oumodulesbot" ]
