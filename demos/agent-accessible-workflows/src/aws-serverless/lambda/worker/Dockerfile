FROM public.ecr.aws/lambda/python:3.12

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    MPLBACKEND=Agg

WORKDIR /var/task

COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r /tmp/requirements.txt

COPY src/worker /var/task/src/worker
COPY src/aws-serverless/lambda/shared /var/task/shared
COPY src/aws-serverless/lambda/worker/handler.py /var/task/handler.py

CMD ["handler.lambda_handler"]
