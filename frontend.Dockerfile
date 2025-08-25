FROM node:alpine3.22

RUN mkdir /frontend
COPY ./frontend /frontend
WORKDIR /frontend

RUN npm install

CMD [ "sh", "-c", "npm run build && npm run start"]