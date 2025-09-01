FROM node:18-alpine

WORKDIR /app

# Копируем зависимости отдельно для кеширования
COPY package.json .
RUN npm install

# Копируем остальные файлы
COPY . .

CMD ["npm", "start"]