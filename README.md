# c14-chat_list

## Как это работает

При нажатии кнопки «Нажми меня» в центре окна появляется фраза «Минимальная программа на Python».

Интерфейс оформлен в тёмной теме:

заголовок и подсказка
карточка для вывода сообщения
синяя кнопка с эффектом при наведении

## Сборка

```bash
cd \c14-chat_list
pyinstaller minimal_program.spec
```

Или

```bash
pyinstaller --onefile --windowed --name minimal_program --collect-all PyQt6 main.py
```
