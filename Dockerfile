FROM python:3.8

ADD requirements.txt .
RUN pip install -r requirements.txt && pip install git+https://github.com/Rapptz/discord.py@0bc15fa130b8f01fe2d67446a2184d474b0d0ba7

ADD oumodulesbot /oumodulesbot
ADD cache.json /

CMD [ "python", "-m", "oumodulesbot.oumodulesbot" ]
