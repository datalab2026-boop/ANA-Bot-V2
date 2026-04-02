#!/bin/bash
while true
do
    echo "Запуск бота через Анти-краш..."
    python3 main.py
    echo "Бот упал или был убит вочдогом. Перезапуск через 5 секунд..."
    sleep 5
done
