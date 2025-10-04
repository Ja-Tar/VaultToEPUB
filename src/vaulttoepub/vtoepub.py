import logging
import os
import re
from pathlib import Path 
from rich.logging import RichHandler
from markdown_it import MarkdownIt
from bs4 import BeautifulSoup
from bs4.element import Tag, NavigableString

from .obsidian_classes import BottomFootnote, InlineFootnote

logging.basicConfig(
    level="INFO",
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler(rich_tracebacks=True)]
)

md = MarkdownIt()
log = logging.getLogger("rich")

def get_markdown_from_file(file_path: Path) -> str:
    log.info("Reading Markdown file: %s", file_path)
    with open(file_path, "r", encoding="utf-8") as f:
        return f.read()

class MDConverter:
    def __init__(self, markdown_text: str) -> None:
        self.markdown_text = markdown_text

    def convert_markdown_to_html(self):
        log.debug("Converting Markdown to HTML")
        return md.render(self.markdown_text)
        
    def remove_yaml_frontmatter(self):
        log.debug("Removing YAML frontmatter if present")
        _markdown_text = self.markdown_text
        if _markdown_text.startswith("---"):
            end_idx = _markdown_text.find("---", 3)
            if end_idx != -1:
                self.markdown_text = _markdown_text[end_idx + 3 :].strip()
                return
            
    def get_title(self, file_path: Path):
        log.debug("Getting title from file path: %s", file_path)
        return file_path.stem
    
    def get_markdown(self) -> str:
        return self.markdown_text

class HTMLConverter:
    def __init__(self, converted_html) -> None:
        self.converted_html = converted_html

    def get_converted_html(self) -> str:
        return self.converted_html
    
    def footnotes(self):
        # Convert all footnotes to HTML
        html_input = self.converted_html

        inline_footnotes = re.findall(InlineFootnote.regex, html_input)
        bottom_footnotes = re.findall(BottomFootnote.regex, html_input, re.DOTALL)
        inline_footnotes = [InlineFootnote(footnote) for footnote in inline_footnotes]
        bottom_footnotes = [BottomFootnote(num, footnote) for num, footnote in bottom_footnotes]
        footnotes = inline_footnotes + bottom_footnotes
        log.info("Found %d footnotes", len(footnotes))

        for num, footnote in enumerate(footnotes, start=1):
            if isinstance(footnote, InlineFootnote):
                html_input = footnote.convert_inline_footnotes(html_input, num)
            elif isinstance(footnote, BottomFootnote):
                html_input = footnote.convert_bottom_footnotes(html_input, num)

        self.converted_html = html_input

    def add_obsidian_formatting(self):
        # Convert Obsidian markdown to HTML

        # Functions that modify html as text
        self.footnotes()

        # Functions that modify html as BeautifulSoup object
        bs_conv = self.BSConverter(self.converted_html)
        bs_conv.convert_section_ids()

        self.converted_html = bs_conv.get_converted_html()

    class BSConverter:
        def __init__(self, input_html) -> None:
            self.soup = BeautifulSoup(input_html, "html.parser")

        def get_converted_html(self) -> str:
            return str(self.soup)

        def convert_section_ids(self):
            # Convert section IDs to HTML ("^c1150d" -> '<... id="c1150d">')
            input_soup = self.soup
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
                    log.info("Converted section ID: %s", section_id)

            self.soup = input_soup

def convert_file_to_xhtml(file_path: Path, save_dir: Path | None = None) -> Path:
    md_conv = MDConverter(get_markdown_from_file(file_path))
    title = md_conv.get_title(file_path)
    md_conv.remove_yaml_frontmatter()

    html_conv = HTMLConverter(md_conv.convert_markdown_to_html())
    html_conv.add_obsidian_formatting()
    html_content = html_conv.get_converted_html()

    # create XHTML file
    new_file_path = file_path.with_suffix(".xhtml")
    if save_dir:
        new_file_path = Path(save_dir) / new_file_path.name

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

def convert_directory_to_xhtml(directory_path: Path):
    tempdir: Path = directory_path.parent / f"{directory_path.name}_temp"
    create_temp_directory(tempdir)

    for root, _, files in os.walk(directory_path):
        for file in files:
            if file.endswith(".md"):
                file_path = Path(root) / file
                convert_file_to_xhtml(file_path, save_dir=tempdir)

def create_temp_directory(temp_dir: Path):
    if not os.path.exists(temp_dir):
        os.makedirs(temp_dir)

if __name__ == "__main__":
    convert_directory_to_xhtml(Path("tests/examples/"))
