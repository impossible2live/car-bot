#!/bin/bash

echo "Ожидание готовности базы данных..."
sleep 5

aerich init -t app.config.TORTOISE_ORM
aerich init-db
aerich upgrade

echo "Запуск бота..."
exec python app/main.py