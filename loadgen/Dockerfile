FROM python:3

COPY requirements.txt .

RUN pip install -r requirements.txt

COPY . /loadgen

ENTRYPOINT ["python", "loadgen/generate_load.py"]
