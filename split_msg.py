import click
from msg_split import split_message, SplitMessageError

@click.command()
@click.option('--max-len', 'max_len', default=4096, help='Максимальный размер одного фрагмента')
@click.argument('html_file', type=click.Path(exists=True))
def main(max_len, html_file):
    """Скрипт чтения HTML-файла и вывода фрагментов."""
    with open(html_file, 'r', encoding='utf-8') as f:
        source_html = f.read()

    try:
        fragments = list(split_message(source_html, max_len=max_len))
    except SplitMessageError as e:
        click.echo(f"ERROR: {e}")
        raise SystemExit(1)

    for i, fr in enumerate(fragments, 1):
        click.echo(f"fragment #{i}: {len(fr)} chars")
        click.echo(fr)

if __name__ == '__main__':
    main()
