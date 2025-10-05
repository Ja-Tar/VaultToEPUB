import re
import logging
from enum import Enum, auto
from bs4.element import Tag, NavigableString

log = logging.getLogger("rich")

def normalize_text(text: str) -> str:
    # Normalize text to be used as an ID (lowercase, replace spaces with hyphens, remove special characters)
    text = text.lower()
    text = re.sub(r"\s+", "-", text)
    text = re.sub(r"[^a-z0-9\-]", "", text)
    return text

class InlineFootnote:
    regex = r"\^\[(.+?)\]"

    def __init__(self, footnote: str) -> None:
        self.footnote = footnote

    def __str__(self) -> str:
        return self.footnote
    
    def convert_inline_footnotes(self, html_input: str, num: int) -> str:
        # Replace inline footnotes with EPUB 3-compliant footnote markup
        footnote_id = f"fn{num}"
        ref_id = f"ref_fn{num}"

        # Replace the inline footnote marker with a superscripted link
        html_input = html_input.replace(
            f"^[{self.footnote}]",
            f'<sup id="{ref_id}"><a href="#{footnote_id}" epub:type="noteref" role="doc-noteref" aria-label="To footnote {num}">{num}</a></sup>',
        )

        # Append the footnote at the end of the document (EPUB 3 standard)
        insert_pos = html_input.rfind("</body>")
        html_input = (
            html_input[:insert_pos]
            + f'\n<aside id="{footnote_id}" epub:type="footnote">'
            + f'<p><a href="#{ref_id}" epub:type="backlink" role="doc-backlink">[{num}]</a>: {self.footnote}</p></aside>'
            + html_input[insert_pos:]
        )

        return html_input

class BottomFootnote:
    regex = r"\[\^(\d+)\]: (.+?)(?=<)"

    def __init__(self, connected_to: str, footnote: str) -> None:
        self.connected_to = connected_to
        self.footnote = footnote

    def __str__(self) -> str:
        return self.footnote
    
    def convert_bottom_footnotes(self, html_input: str, num: int) -> str:
        # Replace inline footnotes with EPUB 3-compliant footnote markup
        footnote_id = f"fn{num}"
        ref_id = f"fnref{num}"

        # Replace the inline footnote marker with a superscripted link
        inline_regex = r"\[\^" + re.escape(self.connected_to) + r"\](?!:)"
        html_input = re.sub(
            inline_regex,
            f'<sup id="{ref_id}"><a href="#{footnote_id}" epub:type="noteref" role="doc-noteref" aria-label="To footnote {num}">{num}</a></sup>',
            html_input
        )

        # Append the footnote at the end of the document (EPUB 3 standard)
        insert_pos = html_input.rfind("</body>")
        html_input = (
            html_input[:insert_pos]
            + f'\n<aside id="{footnote_id}" epub:type="footnote">'
            + f'<p><a href="#{ref_id}" epub:type="backlink" role="doc-backlink">[{num}]</a>: {self.footnote}</p></aside>'
            + html_input[insert_pos:]
        )

        remove_regex = r"<\w+>\[\^" + re.escape(self.connected_to) + r"\]: " + re.escape(self.footnote) + r"</\w+>"
        html_input = re.sub(remove_regex, '', html_input)

        return html_input
    
class SectionID:
    regex = r" *\^(\w*)$"

class Header:
    regex = r"<h[1-6]>(.*?)</h[1-6]>"
    
    def __init__(self, text: str) -> None:
        self.text = text
        self.id = self.generate_id()

    def generate_id(self) -> str:
        max_header = self.text[:50]
        return normalize_text(max_header + "-h")
    
class LinkType(Enum):
    FILE = auto() # Link to another file
    INTERNAL = auto() # Link to a section within the same file
    EXTERNAL = auto() # Link to a section within an other file

class InLineLink:
    regex = r"\[\[(.+?)\]\]"
    
    def __init__(self, raw_text: str) -> None:
        self.link_type: None | LinkType = None
        
        info_regex = r"^(.*?)(?:#(.+?)|)(?:\|(.*?)|)$"
        match = re.match(info_regex, raw_text, re.MULTILINE)
        if not match:
            raise ValueError(f"Could not parse link: {raw_text}")
        self.file = match.group(1) or ""
        self.section = match.group(2) or ""
        self.display_text = match.group(3) if match.group(3) else (self.section if self.section else self.file)
        
        if not self.file and not self.section:
            raise ValueError(f"Link must have at least a file or a section: {raw_text}")
        
        if self.section:
            if self.section.startswith("^"):
                self.section = self.section.lstrip("^")
            else:
                # So this is a link to a header, normalize it and add "-h"
                self.section = normalize_text(self.section) + "-h"
            if self.file:
                self.link_type = LinkType.EXTERNAL
            else:
                self.link_type = LinkType.INTERNAL
        else:
            self.link_type = LinkType.FILE

    def __str__(self) -> str:
        return f"Link(type={self.link_type}, file='{self.file}', section='{self.section}', display_text='{self.display_text}')"
    
    def to_html(self) -> Tag:
        href = ""
        match self.link_type:
            case LinkType.FILE:
                href = f"{self.file}.xhtml"
            case LinkType.INTERNAL:
                href = f"#{self.section}"
            case LinkType.EXTERNAL:
                href = f"{self.file}.xhtml#{self.section}"
            case _:
                raise ValueError(f"Unknown link type: {self.link_type}")
            
        a_tag = Tag(name="a", attrs={"href": href})
        a_tag.string = self.display_text
            
        return a_tag
            