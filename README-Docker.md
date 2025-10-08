# 🐳 YesExpress Docker Deployment

Полная инструкция по развертыванию YesExpress через Docker Compose на сервере Ubuntu.

## 📋 Требования

- Ubuntu Server 20.04+
- Docker 20.10+
- Docker Compose 2.0+
- Минимум 4GB RAM
- 20GB свободного места

## 🚀 Быстрый старт

### 1. Подготовка сервера

```bash
# Обновление системы
sudo apt update && sudo apt upgrade -y

# Установка Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Установка Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Перезагрузка для применения изменений
sudo reboot
```

### 2. Клонирование проекта

```bash
# Клонирование репозитория
git clone <your-repo-url> /app/yesexpress
cd /app/yesexpress

# Копирование и настройка переменных окружения
cp env.example .env
nano .env
```

### 3. Настройка .env файла

Отредактируйте `.env` файл с вашими настройками:

```bash
# Обязательные настройки
DB_PASSWORD=your_secure_password_here
SECRET_KEY=your_secret_key_here
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here

# IP сервера
ALLOWED_HOSTS=89.39.94.187,api.yesexpress.uz,yesexpress.uz,localhost
```

### 4. Запуск приложения

```bash
# Запуск всех сервисов
./deploy.sh

# Или вручную
docker-compose -f docker-compose.prod.yml up -d
```

## 🏗️ Архитектура

### Сервисы

| Сервис | Порт | Описание |
|--------|------|----------|
| `api` | 4546 | Основной API сервер (Gunicorn) |
| `websocket` | 4547 | WebSocket сервер (Daphne) |
| `consumers` | - | Django Channels consumers |
| `telegram_bot` | - | Telegram Bot |
| `celery_worker` | - | Celery Worker |
| `celery_beat` | - | Celery Scheduler |
| `postgis` | 5432 | PostgreSQL + PostGIS |
| `redis` | 6379 | Redis для кеша и Celery |
| `nginx` | 80/443 | Reverse Proxy |

### Сеть

- **Внешний доступ**: `89.39.94.187:80` → Nginx
- **API**: `http://89.39.94.187/` → Gunicorn
- **WebSocket**: `ws://89.39.94.187/webs/` → Daphne
- **Статика**: `http://89.39.94.187/static/` → Nginx
- **Медиа**: `http://89.39.94.187/media/` → Nginx

## 🔧 Управление

### Основные команды

```bash
# Запуск всех сервисов
docker-compose -f docker-compose.prod.yml up -d

# Остановка всех сервисов
docker-compose -f docker-compose.prod.yml down

# Перезапуск конкретного сервиса
docker-compose -f docker-compose.prod.yml restart api

# Просмотр логов
docker-compose -f docker-compose.prod.yml logs -f api
docker-compose -f docker-compose.prod.yml logs -f websocket

# Просмотр статуса
docker-compose -f docker-compose.prod.yml ps
```

### Обновление приложения

```bash
# Остановка сервисов
docker-compose -f docker-compose.prod.yml down

# Обновление кода
git pull origin main

# Пересборка и запуск
docker-compose -f docker-compose.prod.yml build --no-cache
docker-compose -f docker-compose.prod.yml up -d
```

## 📊 Мониторинг

### Проверка здоровья сервисов

```bash
# Проверка API
curl http://89.39.94.187/health/

# Проверка WebSocket
curl -i -N -H "Connection: Upgrade" -H "Upgrade: websocket" -H "Sec-WebSocket-Key: test" -H "Sec-WebSocket-Version: 13" http://89.39.94.187/webs/

# Статус контейнеров
docker-compose -f docker-compose.prod.yml ps
```

### Логи

```bash
# Все логи
docker-compose -f docker-compose.prod.yml logs -f

# Конкретный сервис
docker-compose -f docker-compose.prod.yml logs -f api
docker-compose -f docker-compose.prod.yml logs -f websocket
docker-compose -f docker-compose.prod.yml logs -f telegram_bot
docker-compose -f docker-compose.prod.yml logs -f celery_worker
```

## 🔒 Безопасность

### Настройка SSL (Let's Encrypt)

```bash
# Установка Certbot
sudo apt install certbot python3-certbot-nginx -y

# Получение сертификата
sudo certbot --nginx -d api.yesexpress.uz -d yesexpress.uz

# Автоматическое обновление
sudo crontab -e
# Добавить: 0 12 * * * /usr/bin/certbot renew --quiet
```

### Firewall

```bash
# Настройка UFW
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
```

## 🐛 Отладка

### Частые проблемы

1. **Ошибка подключения к БД**
   ```bash
   # Проверка статуса PostgreSQL
   docker-compose -f docker-compose.prod.yml logs postgis
   ```

2. **Ошибка Redis**
   ```bash
   # Проверка Redis
   docker-compose -f docker-compose.prod.yml logs redis
   ```

3. **Проблемы с WebSocket**
   ```bash
   # Проверка Nginx конфигурации
   docker-compose -f docker-compose.prod.yml logs nginx
   ```

### Вход в контейнер

```bash
# Вход в API контейнер
docker-compose -f docker-compose.prod.yml exec api bash

# Выполнение Django команд
docker-compose -f docker-compose.prod.yml exec api uv run manage.py shell
docker-compose -f docker-compose.prod.yml exec api uv run manage.py migrate
```

## 📈 Масштабирование

### Горизонтальное масштабирование

```bash
# Увеличение количества API воркеров
docker-compose -f docker-compose.prod.yml up -d --scale api=3

# Увеличение количества Celery воркеров
docker-compose -f docker-compose.prod.yml up -d --scale celery_worker=3
```

## 🔄 Backup и восстановление

### Backup базы данных

```bash
# Создание backup
docker-compose -f docker-compose.prod.yml exec postgis pg_dump -U postgres yesexpress > backup_$(date +%Y%m%d_%H%M%S).sql

# Восстановление
docker-compose -f docker-compose.prod.yml exec -T postgis psql -U postgres yesexpress < backup_file.sql
```

## 📞 Поддержка

При возникновении проблем:

1. Проверьте логи: `docker-compose -f docker-compose.prod.yml logs -f`
2. Проверьте статус: `docker-compose -f docker-compose.prod.yml ps`
3. Проверьте ресурсы: `docker stats`
4. Перезапустите сервисы: `docker-compose -f docker-compose.prod.yml restart`
