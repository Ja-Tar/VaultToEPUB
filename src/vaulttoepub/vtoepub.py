import logging
import os
import re
from rich.logging import RichHandler
from markdown_it import MarkdownIt
from bs4 import BeautifulSoup
from bs4.element import Tag, NavigableString

logging.basicConfig(
    level="NOTSET",
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler(rich_tracebacks=True)]
)

md = MarkdownIt()
log = logging.getLogger("rich")

def convert_markdown_to_html(markdown_text):
    log.debug("Converting Markdown to HTML")
    return md.render(markdown_text)


def get_markdown_from_file(file_path):
    log.debug(f"Reading Markdown file: {file_path}")
    with open(file_path, "r", encoding="utf-8") as f:
        return f.read()


def remove_yaml_frontmatter(markdown_text):
    log.debug("Removing YAML frontmatter if present")
    if markdown_text.startswith("---"):
        end_idx = markdown_text.find("---", 3)
        if end_idx != -1:
            return markdown_text[end_idx + 3 :].strip()
    return markdown_text


def get_title(file_path):
    log.debug(f"Getting title from file path: {file_path}")
    return os.path.splitext(os.path.basename(file_path))[0]


def in_line_footnotes(html_input):
    # Convert inline footnotes to HTML (" ^[This is inline footnote] ")
    footnote_pattern = r"\^\[(.+?)\]"
    footnote_texts = re.findall(footnote_pattern, html_input)

    for i, footnote in enumerate(footnote_texts, start=1):
        # Replace inline footnotes with EPUB 3-compliant footnote markup
        footnote_id = f"fn{i}"
        ref_id = f"fnref{i}"
        # Replace the inline footnote marker with a superscripted link
        html_input = html_input.replace(
            f"^[{footnote}]",
            f'<sup id="{ref_id}"><a href="#{footnote_id}" epub:type="noteref">{i}</a></sup>',
        )
        # Append the footnote at the end of the document (EPUB 3 standard)
        insert_pos = html_input.rfind("</body>")
        html_input = (
            html_input[:insert_pos]
            + f'<aside id="{footnote_id}" epub:type="footnote"><p>{footnote}</p></aside>\n'
            + html_input[insert_pos:]
        )

    return html_input

def convert_section_ids(input_soup: BeautifulSoup):
    # Convert section IDs to HTML ("^c1150d" -> '<... id="c1150d">')
    section_pattern = r"\^(\w*)$"

    # add to parent ID
    for text_node in input_soup.find_all(string=re.compile(section_pattern)):
        match = re.search(section_pattern, str(text_node))
        if match:
            section_id = match.group(1)
            parent = text_node.parent
            if parent:
                parent['id'] = section_id
            text_node.replace_with(NavigableString(re.sub(section_pattern, '', str(text_node))))

    return input_soup

def add_obsidian_formatting(html_input):
    # Convert Obsidian markdown to HTML
    # ADD support for Obsidian-specific syntax
    soup = BeautifulSoup(html_input, "html.parser")

    soup = convert_section_ids(soup)

    return str(soup)


def convert_file_to_xhtml(file_path):
    markdown_text = get_markdown_from_file(file_path)
    markdown_text = remove_yaml_frontmatter(markdown_text)
    title = get_title(file_path)
    html_content = convert_markdown_to_html(markdown_text)
    html_content = add_obsidian_formatting(html_content)
    html_content = in_line_footnotes(html_content)

    # create XHTML file
    new_file_path = file_path.replace(".md", ".xhtml")

    xhtml_content = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        "<!DOCTYPE html>\n"
        '<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops">\n'
        "<head>\n"
        '  <meta charset="utf-8"/>\n'
        f"  <title>{title}</title>\n"
        "</head>\n"
        "<body>\n"
        f"  <h1>{title}</h1>\n"
        f"{html_content}\n"
        "</body>\n"
        "</html>"
    )

    with open(new_file_path, "w", encoding="utf-8") as f:
        f.write(xhtml_content)

    return new_file_path


if __name__ == "__main__":
    convert_file_to_xhtml("tests/examples/one.md")
