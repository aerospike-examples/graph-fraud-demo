FROM node:alpine3.22

ENV BACKEND_URL="http://asgraph-backend:4000"

RUN mkdir /frontend
COPY ./frontend /frontend
WORKDIR /frontend

RUN npm install

CMD [ "sh", "-c", "wget --post-data='' http://asgraph-backend:4000/bulk-load-csv ; npm run build ; npm run start"]