# Pfizer License Server

Сервер управления лицензиями для Pfizer Mailer.

## Установка

1. Клонируйте репозиторий
2. Установите зависимости: `npm install`
3. Настройте переменные окружения в `.env`
4. Запустите сервер: `npm start`

## API Endpoints

- `POST /api/licenses` - Активация/проверка лицензии
- `GET /api/licenses/admin` - Получить все ключи
- `POST /api/licenses/admin` - Создать ключ
- `PUT /api/licenses/admin/:id` - Обновить ключ
- `DELETE /api/licenses/admin/:id` - Удалить ключ

## Админ-панель

Доступна по адресу: `/admin`