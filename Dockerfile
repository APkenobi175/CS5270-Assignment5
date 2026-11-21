# Docker image for the widget request consumer

# 1. Runtime environment: Python 3.12
FROM python:3.12-slim

# print log lines right away instead of buffering them
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# 2. Install the dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 3. Copy the program into the image
COPY main.py models.py requestSources.py widgetStores.py ./

# 4. Run the consumer. The arguments in CMD are the defaults and can be replaced at docker run time, e.g.
ENTRYPOINT ["python", "main.py"]
CMD ["--storage", "dynamodb", "--request-queue", "cs5270-requests", "--table", "widgets"]
