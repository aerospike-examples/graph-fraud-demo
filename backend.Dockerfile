FROM python:3.12.11-alpine3.22

ENV GRAPH_HOST_ADDRESS="asgraph-service"

RUN mkdir /backend
COPY ./backend /backend
WORKDIR /backend
RUN pip install -r requirements.txt

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--root-path", "/api", "--port", "4000", "--loop", "asyncio",
    "--timeout-keep-alive", "2", "--limit-concurrency", "64", "--backlog", "64"]