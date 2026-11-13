ИНСТРУКЦИЯ ПО ЗАПУСКУ TELEGRAM-БОТА

1. В Railway подключите репозиторий GitHub с файлами этого проекта
   (telegram_review_bot.py и requirements.txt).
2. В настройках сервиса Railway добавьте Variables:
   BOT_TOKEN = токен, который выдал @BotFather
   ADMIN_ID = 5035314713
3. В Settings / Deploy добавьте Start Command:
   python telegram_review_bot.py
4. Запустите Deploy.

ВАЖНО:
- Никому не отправляйте BOT_TOKEN. Вводите его только в Variables Railway.
- Администратор должен открыть бота в Telegram и нажать /start.
- Пользователь должен нажать /start перед отправкой фото или видео.
- Бот принимает фото и видео, пересылает их администратору с кнопками
  «Одобрено» и «Отказано», а затем уведомляет отправителя.
- База SQLite хранит состояние заявок. Для постоянного хранения базы
  подключите Railway Volume и задайте DB_PATH на путь внутри Volume.
