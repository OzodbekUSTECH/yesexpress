#!/bin/bash

# Скрипт для развертывания YesExpress БЕЗ Nginx на сервере 89.39.94.187

set -e

echo "🚀 Начинаем развертывание YesExpress (без Nginx)..."

# Проверка наличия .env файла
if [ ! -f .env ]; then
    echo "❌ Файл .env не найден!"
    echo "📋 Скопируйте env.example в .env и настройте переменные:"
    echo "   cp env.example .env"
    echo "   nano .env"
    exit 1
fi

# Создание необходимых директорий
echo "📁 Создаем необходимые директории..."
mkdir -p logs
mkdir -p staticfiles
mkdir -p media

# Остановка существующих контейнеров
echo "🛑 Останавливаем существующие контейнеры..."
docker-compose -f docker-compose.simple.yml down || true

# Сборка образов
echo "🔨 Собираем Docker образы..."
docker-compose -f docker-compose.simple.yml build --no-cache

# Запуск сервисов
echo "🚀 Запускаем сервисы..."
docker-compose -f docker-compose.simple.yml up -d

# Ожидание готовности сервисов
echo "⏳ Ожидаем готовности сервисов..."
sleep 30

# Проверка статуса сервисов
echo "🔍 Проверяем статус сервисов..."
docker-compose -f docker-compose.simple.yml ps

# Проверка логов
echo "📋 Последние логи API сервера:"
docker-compose -f docker-compose.simple.yml logs --tail=20 api

echo "✅ Развертывание завершено!"
echo "🌐 API доступен по адресу: http://89.39.94.187"
echo "🔌 WebSocket доступен по адресу: ws://89.39.94.187:4547"
echo "📊 Мониторинг: docker-compose -f docker-compose.simple.yml logs -f"
