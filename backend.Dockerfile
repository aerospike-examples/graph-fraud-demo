FROM python:3.12.11-alpine3.22

ENV GRAPH_HOST_ADDRESS="asgraph-service"

RUN mkdir /backend
COPY ./java-backend /backend
WORKDIR /backend

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--root-path", "/api", "--port", "4000", "--loop", "asyncio"]