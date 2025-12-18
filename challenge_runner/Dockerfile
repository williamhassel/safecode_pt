FROM python:3.12-slim

WORKDIR /work
COPY requirements.txt /work/requirements.txt
RUN pip install --no-cache-dir -r /work/requirements.txt

COPY runner.py /work/runner.py
ENTRYPOINT ["python", "/work/runner.py"]
