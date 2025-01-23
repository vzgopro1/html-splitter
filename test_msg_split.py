import unittest

from msg_split import split_message, SplitMessageError

class TestSplitMessage(unittest.TestCase):

    def test_empty_string(self):
        fragments = list(split_message(""))
        self.assertEqual(len(fragments), 0, "Пустая строка не должна давать фрагментов.")

    def test_small_text(self):
        text = "Hello <b>world</b>"
        fragments = list(split_message(text, max_len=50))
        self.assertEqual(len(fragments), 1)
        self.assertIn("<b>world</b>", fragments[0])

    def test_exceeding_text(self):
        text = "A" * 5000
        # Обычный текст, должен быть разбит на 2 (или более) фрагмента
        fragments = list(split_message(text, max_len=4096))
        self.assertGreater(len(fragments), 1)

    def test_huge_tag(self):
        # Тег a, который сам по себе длиннее max_len => исключение
        a_tag = '<a href="https://example.com/">' + ("X" * 5000) + '</a>'
        with self.assertRaises(SplitMessageError):
            list(split_message(a_tag, max_len=4096))

    def test_block_tag_split(self):
        # Проверим, что блочный тег p при превышении лимита правильно "закрывается" и продолжается
        html = "<p>" + "A" * 3000 + "</p><p>" + "B" * 3000 + "</p>"
        # max_len=4096 => первый <p> должен войти в один фрагмент, второй <p> - в другой
        fragments = list(split_message(html, max_len=4096))
        self.assertEqual(len(fragments), 2, "Должны получить 2 фрагмента для двух больших абзацев.")

        # Проверка, что <p> не рвётся внутри, а целиком закрывается
        self.assertTrue(fragments[0].endswith("</p>"), "Первый фрагмент должен корректно закрывать p.")
        self.assertTrue(fragments[1].startswith("<p>"), "Второй фрагмент должен начинаться с <p>.")

if __name__ == '__main__':
    unittest.main()
