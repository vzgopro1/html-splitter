# HTML Splitter

Демонстрация решения задачи по разделению HTML на части, чтобы каждая часть:
- не превышала заданного `max_len` символов;
- содержала корректный HTML (никакие неблочные теги не разрываются);
- блочные теги (`<p>`, `<b>`, `<div>`, `<span>` и т.д.) могут "разрываться" между фрагментами,
  но при этом корректно закрываются в одном фрагменте и заново открываются в другом.

## Установка

```bash
git clone https://github.com/vzgopro1/html-splitter.git
cd html-splitter
pip install -r requirements.txt
```

## Использование 

```bash
python split_msg.py --max-len=3000 source.html
```

На экран (stdout) будет выведен результат в виде:

```html
fragment #1: 2990 chars
<html>...</html>
fragment #2: 1502 chars
<html>...</html>
```

## Запуск Тестов

```bash
python -m unittest test_msg_split.py
```

