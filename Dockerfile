FROM python:3.8

ADD requirements.txt .
RUN pip install -r requirements.txt

ADD oumodulesbot.py /
ADD ou_utils.py /
ADD cache.json /

CMD [ "python", "/oumodulesbot.py" ]
