import re

class InlineFootnote:
    regex = r"\^\[(.+?)\]"

    def __init__(self, footnote: str) -> None:
        self.footnote = footnote

    def __str__(self) -> str:
        return self.footnote
    
    def convert_inline_footnotes(self, html_input: str, num: int) -> str:
        # Replace inline footnotes with EPUB 3-compliant footnote markup
        footnote_id = f"fn{num}"
        ref_id = f"fnref{num}"

        # Replace the inline footnote marker with a superscripted link
        html_input = html_input.replace(
            f"^[{self.footnote}]",
            f'<sup id="{ref_id}"><a href="#{footnote_id}" epub:type="noteref">{num}</a></sup>',
        )

        # Append the footnote at the end of the document (EPUB 3 standard)
        insert_pos = html_input.rfind("</body>")
        html_input = (
            html_input[:insert_pos]
            + f'\n<aside id="{footnote_id}" epub:type="footnote"><p>{self.footnote}</p></aside>'
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
            f'<sup id="{ref_id}"><a href="#{footnote_id}" epub:type="noteref">{num}</a></sup>',
            html_input
        )

        # Append the footnote at the end of the document (EPUB 3 standard)
        insert_pos = html_input.rfind("</body>")
        html_input = (
            html_input[:insert_pos]
            + f'\n<aside id="{footnote_id}" epub:type="footnote"><p>{self.footnote}</p></aside>'
            + html_input[insert_pos:]
        )

        remove_regex = r"<\w+>\[\^" + re.escape(self.connected_to) + r"\]: " + re.escape(self.footnote) + r"</\w+>"
        html_input = re.sub(remove_regex, '', html_input)

        return html_input