FROM mirror.gcr.io/library/node:18-alpine

WORKDIR /app

COPY package.json .
RUN npm install

COPY . .

CMD ["npm", "start"]