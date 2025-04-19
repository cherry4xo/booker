FROM python:3.13-slim

WORKDIR /code

COPY ./requirements.txt /code/requirements.txt

RUN pip install --upgrade pip
RUN pip install setuptools
RUN python3.13 -m pip install --no-cache-dir -r /code/requirements.txt

COPY ./app /code/
COPY ./bot.py keyboards.py values.py ./

CMD ["python3.13", "-u", "bot.py"]
