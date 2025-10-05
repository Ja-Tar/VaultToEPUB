import logging
import os
import re
import zipfile
from pathlib import Path 
from rich.logging import RichHandler
from markdown_it import MarkdownIt
from bs4 import BeautifulSoup
from bs4.element import Tag, NavigableString

from .obsidian_classes import Header, BottomFootnote, InlineFootnote, SectionID, InLineLink
from .files_classes import MDFile, CombinedMDFile

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
        bs_conv.add_id_to_headers()
        bs_conv.convert_section_ids()
        bs_conv.convert_inline_links()

        self.converted_html = bs_conv.get_converted_html()

    class BSConverter:
        def __init__(self, input_html) -> None:
            self.soup = BeautifulSoup(input_html, "html.parser")

        def get_converted_html(self) -> str:
            return str(self.soup)
        
        def add_id_to_headers(self):
            # Convert headers to have IDs based on their text content
            input_soup = self.soup

            headers = input_soup.find_all(re.compile(r"h[1-6]"))

            if headers:
                log.info("Adding IDs to %d headers", len(headers))
                for header in headers:
                    if isinstance(header, Tag):
                        text = header.get_text()
                        header_obj = Header(text)
                        header['id'] = header_obj.id
                        log.debug("Added ID '%s' to header: %s", header_obj.id, text)
            else:
                log.info("No headers found to add IDs to")

        def convert_section_ids(self):
            # Convert section IDs to HTML ("^c1150d" -> '<... id="c1150d">')
            input_soup = self.soup

            for text_node in input_soup.find_all(string=re.compile(SectionID.regex)):
                match = re.search(SectionID.regex, str(text_node))
                if match:
                    section_id = match.group(1)
                    parent = text_node.parent
                    if parent:
                        parent['id'] = section_id
                    text_node.replace_with(NavigableString(re.sub(SectionID.regex, '', str(text_node))))
                    log.info("Converted section ID: %s", section_id)

            self.soup = input_soup
        
        def convert_inline_links(self):
            # Convert internal links like [[#^d758ad]] or [[Note Title]]
            input_soup = self.soup
            text_nodes = input_soup.find_all(string=re.compile(InLineLink.regex))

            for text_node in text_nodes:
                if not isinstance(text_node, NavigableString):
                    continue
                matches = re.findall(InLineLink.regex, str(text_node))
                modified_text = str(text_node)
                for match in matches:
                    link = InLineLink(str(match))
                    log.debug("Processing link: %s", link)
                    modified_text = modified_text.replace(str(f"[[{match}]]"), str(link.to_html()))
                
                text_node.replace_with(BeautifulSoup(modified_text, "html.parser"))
                    
            log.info("Converted %d inline links", len(text_nodes))
            self.soup = input_soup

def normalize_file_name(file_path: Path) -> Path:
    # Normalize file name to be filesystem-friendly
    normalized_name = re.sub(r'[<>:"/\\|?*]', '_', file_path.stem)
    normalized_name = re.sub(r'\s+', '_', normalized_name)
    normalized_name = normalized_name.strip('_')
    return file_path.with_name(normalized_name).with_suffix(file_path.suffix)

def convert_file_to_xhtml(file_path: Path, save_dir: Path | None = None) -> MDFile:
    md_conv = MDConverter(get_markdown_from_file(file_path))
    title = Header(md_conv.get_title(file_path))
    md_conv.remove_yaml_frontmatter()

    html_conv = HTMLConverter(md_conv.convert_markdown_to_html())
    html_conv.add_obsidian_formatting()
    html_content = html_conv.get_converted_html()

    # create XHTML file
    new_file_path = generate_xhtml_path(file_path, save_dir)

    xhtml_content = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        "<!DOCTYPE html>\n"
        '<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops">\n'
        "<head>\n"
        '  <meta charset="utf-8"/>\n'
        f"  <title>{title.text}</title>\n"
        "</head>\n"
        "<body>\n"
        f'<section role="doc-chapter" epub:type="chapter" aria-labelledby="{title.id}">\n'
        f'<h1 id="{title.id}">{title.text}</h1>\n'
        f'{html_content}\n'
        "</section>\n"
        "</body>\n"
        "</html>"
    )

    save_file(new_file_path, xhtml_content)

    return MDFile(new_file_path)

def generate_xhtml_path(file_path: Path, save_dir: Path | None = None) -> Path:
    new_file_path = file_path.with_suffix(".xhtml")
    new_file_path = normalize_file_name(new_file_path)
    if save_dir:
        new_file_path = Path(save_dir) / new_file_path.name
    return new_file_path

def save_file(new_file_path: Path, xhtml_content: str):
    with open(new_file_path, "w", encoding="utf-8") as f:
        f.write(xhtml_content)

def combine_files_to_xhtml(file_paths: list[Path], filename: str, save_dir: Path | None = None) -> CombinedMDFile:
    title = Header(filename)
    xhtml_content = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        "<!DOCTYPE html>\n"
        '<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops">\n'
        "<head>\n"
        '  <meta charset="utf-8"/>\n'
        f"  <title>{title.text}</title>\n"
        "</head>\n"
        "<body>\n"
        f'<h1 id="{title.id}">{title.text}</h1>\n'
    )

    for _, file_path in enumerate(file_paths):
        md_conv = MDConverter(get_markdown_from_file(file_path))
        title = Header(md_conv.get_title(file_path)) # Every title is a header <h1> with section
        md_conv.remove_yaml_frontmatter()

        html_conv = HTMLConverter(md_conv.convert_markdown_to_html())
        html_conv.add_obsidian_formatting()
        html_content = html_conv.get_converted_html()

        xhtml_content += (
            f'<section role="doc-chapter" epub:type="chapter" aria-labelledby="{title.id}">\n'
            f'<h1 id="{title.id}">{title.text}</h1>\n'
            f'{html_content}\n'
            "</section>\n"
        )
    
    xhtml_content += "</body>\n</html>"

    new_file_path = generate_xhtml_path(Path(filename).with_suffix(".xhtml"), save_dir)
    save_file(new_file_path, xhtml_content)

    return CombinedMDFile(new_file_path, [MDFile(fp) for fp in file_paths])

def convert_directory_to_xhtml(directory_path: Path, tempdir: Path, f_to_one_file: bool) -> list[CombinedMDFile | MDFile]:
    converted_files: list[CombinedMDFile | MDFile] = []

    for root, dirs, files in os.walk(directory_path):
        if not dirs and f_to_one_file:
            combine_files = []
            for file in files:
                if file.endswith(".md"):
                    file_path = Path(root) / file
                    combine_files.append(file_path)
            if combine_files:
                log.info("Last folder detected, combining %s files into one", len(combine_files))
                filename = Path(root).name
                converted_files.append(combine_files_to_xhtml(combine_files, filename, save_dir=tempdir / "OEBPS" / "Text"))
                continue
        for file in files:
            if file.endswith(".md"):
                file_path = Path(root) / file
                converted_files.append(convert_file_to_xhtml(file_path, save_dir=tempdir / "OEBPS" / "Text"))
    
    return converted_files

def create_epub_temp_directory(temp_dir: Path):
    directories = ["", "META-INF", "OEBPS", "OEBPS/Text", "OEBPS/Styles", "OEBPS/Images"]

    for directory in directories:
        if not os.path.exists(temp_dir / directory):
            os.makedirs(temp_dir / directory)

def create_epub_config_files(temp_dir: Path, converted_files: list[CombinedMDFile | MDFile], custom_css_file: Path | None = None):
    generate_mimetype_file(temp_dir)
    generate_container_xml(temp_dir)
    generate_default_css(temp_dir)
    if custom_css_file:
        # TODO Implement custom CSS handling
        log.warning("Custom CSS handling is not implemented yet.")
    generate_content_opf(temp_dir, converted_files, custom_css_file)

def generate_mimetype_file(temp_dir: Path):
    mimetype_path = temp_dir / "mimetype"
    with open(mimetype_path, "w", encoding="utf-8") as f:
        f.write("application/epub+zip")
    
    # Ensure the mimetype file is uncompressed
    os.chmod(mimetype_path, 0o644)  # Set permissions to read/write for owner, read for others
    log.info("Created mimetype file at: %s", mimetype_path)

def generate_container_xml(temp_dir: Path):
    container_path = temp_dir / "META-INF" / "container.xml"
    container_content = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">\n'
        '  <rootfiles>\n'
        '    <rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>\n'
        '  </rootfiles>\n'
        '</container>'
    )
    
    with open(container_path, "w", encoding="utf-8") as f:
        f.write(container_content)
    
    log.info("Created container.xml at: %s", container_path)

def generate_default_css(temp_dir: Path):
    css_path = temp_dir / "OEBPS" / "Styles" / "default.css"
    css_content = (
        "body { font-family: Arial, sans-serif; line-height: 1.6; }\n"
        "h1, h2, h3, h4, h5, h6 { font-weight: bold; }\n"
        "p { margin-bottom: 1em; }\n"
        "a { color: blue; text-decoration: underline; }\n"
    )
    
    with open(css_path, "w", encoding="utf-8") as f:
        f.write(css_content)
    
    log.info("Created default CSS file at: %s", css_path)

def generate_content_opf(temp_dir: Path, converted_files: list[CombinedMDFile | MDFile], custom_css_file: Path | None = None):
    content_opf_path = temp_dir / "OEBPS" / "content.opf"
    
    manifest_items: list[str] = []
    spine_items: list[str] = []
    #TODO Add handling for images and custom CSS
    #TODO Add support for combined files
    for _, md_file in enumerate(converted_files):
        if isinstance(md_file, CombinedMDFile):
            manifest_items.append(f'<item id="{md_file.name}" href="Text/{md_file.filename}" media-type="application/xhtml+xml" properties="rendition:flow-scrolled-doc"/>')
            spine_items.append(f'<itemref idref="{md_file.name}"/>')
        else:
            manifest_items.append(f'<item id="{md_file.name}" href="Text/{md_file.filename}" media-type="application/xhtml+xml"/>')
            spine_items.append(f'<itemref idref="{md_file.name}"/>')
    
    manifest = (
        '<?xml version="1.0" encoding="utf-8"?>\n'
        '<package version="3.0" unique-identifier="BookId" xmlns="http://www.idpf.org/2007/opf">\n'
        '<metadata xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:opf="http://www.idpf.org/2007/opf">\n'
        '<dc:identifier id="BookId">urn:uuid:780aec4a-test-ssss-ssss-658479f492e9</dc:identifier>\n' # TODO Generate unique UUID
        '<dc:language>en</dc:language>\n' # TODO Allow setting language
        '<dc:title>[Main title]</dc:title>\n' # TODO Allow setting title
        '</metadata>\n'
        '<manifest>\n'
        f'{"\n".join(manifest_items)}\n'
        '<item id="css" href="Styles/default.css" media-type="text/css"/>\n'
        '</manifest>\n'
        '<spine>\n'
        f'{"\n".join(spine_items)}\n'
        '</spine>\n'
        '</package>'
    )

    save_file(content_opf_path, manifest)
    log.info("Created content.opf at: %s", content_opf_path)

def generate_epub(directory_path: Path, f_to_one_file: bool, output_path: Path | None = None):
    tempdir: Path = directory_path.parent / f"{directory_path.name}_temp"
    create_epub_temp_directory(tempdir)
    converted_files = convert_directory_to_xhtml(directory_path, tempdir, f_to_one_file)
    create_epub_config_files(tempdir, converted_files)

    if output_path is None:
        output_path = directory_path.parent / f"{directory_path.name}.epub"
    
    generate_epub_file(tempdir, output_path)

def generate_epub_file(temp_dir: Path, output_path: Path):
    # Create the final EPUB file from the temp directory
    
    with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as epub:
        # The mimetype file must be the first file and must not be compressed
        mimetype_path = temp_dir / "mimetype"
        epub.write(mimetype_path, 'mimetype', compress_type=zipfile.ZIP_STORED)
        
        for foldername, subfolders, filenames in os.walk(temp_dir):
            for filename in filenames:
                if filename == "mimetype":
                    continue  # Already added
                file_path = os.path.join(foldername, filename)
                arcname = os.path.relpath(file_path, temp_dir)
                epub.write(file_path, arcname)