from typing import Generator, List, Tuple
from bs4 import BeautifulSoup, NavigableString, Tag

MAX_LEN = 4096

BLOCK_TAGS = {
    'p', 'b', 'strong', 'i', 'ul', 'ol', 'div', 'span'
}

class SplitMessageError(Exception):
    """Исключение, выбрасываемое, если не удаётся уложить фрагмент в max_len."""
    pass


def split_message(source: str, max_len: int = MAX_LEN) -> Generator[str, None, None]:
    """
    Разделяет исходный HTML-текст (source) на фрагменты длиной не более max_len.
    Каждый фрагмент содержит корректную структуру HTML (никакие неблочные теги не рвутся).
    
    Использует BeautifulSoup для парсинга, затем собирает строку частями.
    """

    soup = BeautifulSoup(source, 'html.parser')

    # Чтобы упростить: мы будем обходить дерево рекурсивно и генерировать "элементы" (теги или текст).
    # При превышении max_len - закрываем открытые блочные теги и начинаем новый фрагмент.
    # Если неблочный тег сам по себе больше max_len, кидаем ошибку.

    # Здесь мы храним текущий фрагмент (строку) и структуру вложенных блочных тегов.
    current_fragment = ""
    open_blocks_stack: List[str] = []  # Список имён тегов, которые открыты в текущем фрагменте

    def open_block_tags(tags_stack: List[str]) -> str:
        """Сформировать строку с открывающими тегами из списка."""
        return "".join(f"<{tag}>" for tag in tags_stack)

    def close_block_tags(tags_stack: List[str]) -> str:
        """Сформировать строку с закрывающими тегами из списка (в обратном порядке)."""
        return "".join(f"</{tag}>" for tag in reversed(tags_stack))

    def flush_fragment(fragment: str, close_tags: bool = True) -> str:
        """Закрыть (при необходимости) блоки, вернуть готовую HTML-строку фрагмента."""
        if close_tags:
            return fragment + close_block_tags(open_blocks_stack)
        else:
            return fragment

    def yield_fragment(fragment: str):
        """Отправить фрагмент наружу."""
        nonlocal current_fragment
        if fragment:
            yield fragment

    def safe_append(content: str):
        """Добавить content к текущему фрагменту, проверяя длину."""
        nonlocal current_fragment

        if len(current_fragment) + len(content) > max_len:
            return False
        else:
            current_fragment += content
            return True

    def traverse(node):
        """
        Рекурсивный обход DOM. На каждом узле (Tag или NavigableString) 
        пытаемся добавить его в текущий фрагмент.
        """
        nonlocal current_fragment

        if isinstance(node, NavigableString):
            # Просто текст
            text_str = str(node)
            if not text_str.strip():
                # Если пустой текст - попробуем просто добавить (обычно не влияет на структуру)
                if not safe_append(text_str):
                    # Если даже пробел не влезает - фрагмент переполнен, 
                    # надо завершить и начать новый
                    # Закрываем текущие блоки:
                    frag_to_yield = flush_fragment(current_fragment, close_tags=True)
                    yield frag_to_yield
                    current_fragment = ""
                    # Открываем их заново
                    current_fragment += open_block_tags(open_blocks_stack)
                    # Теперь попробуем снова добавить:
                    if not safe_append(text_str):
                        # Если даже теперь не влезает, значит max_len слишком маленький
                        raise SplitMessageError("Не удаётся добавить даже пустой текст.")
                return

            # Проверяем, умещается ли этот текст целиком
            if isinstance(node, NavigableString):
                text_str = str(node)

                if not text_str:  # или strip(), если совсем пустая
                    return  # ничего добавлять не нужно

                # Здесь — логика разбивки:
                idx = 0
                while idx < len(text_str):
                    # Сколько осталось места в текущем фрагменте?
                    space_in_fragment = max_len - len(current_fragment)
                    if space_in_fragment <= 0:
                        # Текущий фрагмент уже заполнен под завязку
                        # => "закрываем" и начинаем новый
                        frag_to_yield = flush_fragment(current_fragment, close_tags=True)
                        yield frag_to_yield
                        current_fragment = ""
                        current_fragment += open_block_tags(open_blocks_stack)
                        space_in_fragment = max_len  # новый фрагмент свободен

                    # Возьмём кусок текста, который влезает в текущий фрагмент
                    chunk = text_str[idx: idx + space_in_fragment]
                    current_fragment += chunk
                    idx += len(chunk)

                return

            
            if not safe_append(text_str):
                # Не влезает - формируем готовый фрагмент
                frag_to_yield = flush_fragment(current_fragment, close_tags=True)
                yield frag_to_yield
                current_fragment = ""

                # Начинаем новый фрагмент с открытыми блок-тегами
                current_fragment += open_block_tags(open_blocks_stack)
                # Добавляем текст второй попыткой
                if not safe_append(text_str):
                    # Даже в пустой фрагмент не влезает => ошибка
                    raise SplitMessageError("Текстовый узел больше max_len.")
                
        elif isinstance(node, Tag):
            tag_name = node.name.lower()

            # Проверим, является ли тег блочным или нет
            is_block = (tag_name in BLOCK_TAGS)

            # Открывающий тег
            open_tag_str = f"<{tag_name}{format_attributes(node)}>"
            closing_tag_str = f"</{tag_name}>"

            if is_block:
                if not safe_append(open_tag_str):
                    # Не влезает -> завершаем фрагмент
                    frag_to_yield = flush_fragment(current_fragment, close_tags=True)
                    yield frag_to_yield
                    current_fragment = ""
                    # Новый фрагмент
                    current_fragment += open_block_tags(open_blocks_stack)
                    # Теперь добавляем сам блок:
                    if not safe_append(open_tag_str):
                        raise SplitMessageError(f"Тег <{tag_name}> сам по себе больше max_len.")
                
                open_blocks_stack.append(tag_name)

                # Обойдём содержимое тега
                for child in node.children:
                    yield from traverse(child)

                # Закрываем блочный тег
                if not safe_append(closing_tag_str):
                    # Не влезает - значит нужно завершить фрагмент 
                    frag_to_yield = flush_fragment(current_fragment, close_tags=False)
                    yield frag_to_yield
                    current_fragment = ""
                    # У нас ещё открыт текущий тег, но на новом фрагменте надо 
                    # заново открыть все родительские.
                    # Однако сам блочный тег мы можем закрыть целиком в старом фрагменте.
                    # То есть, поскольку этот блочный тег "рвём" на фрагменты:
                    open_blocks_stack.pop()  # удалить текущий
                    
                    # Закрываем именно текущий тег сейчас:
                    leftover = closing_tag_str  # Тег, который не влез
                    # Формируем завершённый фрагмент:
                    if leftover:
                        # Если leftover сам по себе больше max_len - ошибка
                        if len(leftover) > max_len:
                            raise SplitMessageError(f"Не удаётся закрыть <{tag_name}> в пределах max_len.")
                        # Начинаем новый фрагмент
                        current_fragment = open_block_tags(open_blocks_stack)  # те, что выше
                        if not safe_append(leftover):
                            # Если не влезает, снова дробим (редкий случай):
                            raise SplitMessageError(f"Закрывающий тег </{tag_name}> не влезает в пустой фрагмент.")
                    
                    # Теперь считаем, что блочный тег заново "открываем" для дальнейшего содержимого?
                    # Но мы уже обошли содержимое. Значит он полностью закрыт.
                    # Возвращаемся к циклу. 
                else:
                    # Удаляем из стека, так как тег успешно закрыт
                    open_blocks_stack.pop()

            else:
                # Неблочный тег рвать нельзя. Его содержимое должно уместиться целиком.
                full_str = node.prettify(formatter=None)  # или вручную собрать <tag>...</tag>
                # Проверяем длину сразу
                if len(full_str) > max_len:
                    raise SplitMessageError(
                        f"Тег <{tag_name}> с содержимым больше max_len, разорвать нельзя."
                    )

                if not safe_append(full_str):
                    # Не влезает - завершим текущий фрагмент
                    frag_to_yield = flush_fragment(current_fragment, close_tags=True)
                    yield frag_to_yield
                    current_fragment = ""
                    # Новый фрагмент с уже открытыми блоками
                    current_fragment += open_block_tags(open_blocks_stack)
                    # Добавляем тег
                    if not safe_append(full_str):
                        raise SplitMessageError(
                            f"Тег <{tag_name}> всё ещё не влезает в пустой фрагмент (слишком большой)."
                        )

        else:
            # На случай других типов узлов (Комментарии, Doctype, etc.) 
            # Можно либо пропустить, либо обрабатывать аналогично тексту
            pass

    # Запускаем рекурсивный обход
    for child in soup.children:
        yield from traverse(child)

    # В конце, если есть что-то в current_fragment, закрываем открытые теги и возвращаем
    if current_fragment:
        final_fragment = flush_fragment(current_fragment, close_tags=True)
        yield final_fragment


def format_attributes(tag: Tag) -> str:
    """
    Собрать строку атрибутов (например, key="value") из BeautifulSoup-тэга,
    чтобы корректно формировать открывающие теги вручную.
    """
    if not tag.attrs:
        return ""
    parts = []
    for k, v in tag.attrs.items():
        if v is None:
            parts.append(k)  # Например: <option disabled>
        elif isinstance(v, list):
            # Например, class=["btn","btn-primary"]
            parts.append(f'{k}="{" ".join(v)}"')
        else:
            parts.append(f'{k}="{v}"')
    return " " + " ".join(parts) if parts else ""
