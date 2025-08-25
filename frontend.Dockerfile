FROM node:alpine3.22

RUN mkdir /frontend
COPY ./frontend /frontend
WORKDIR /frontend

RUN npm install && npm run build

CMD [ "npm", "run", "start"]