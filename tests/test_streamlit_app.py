from streamlit_app import extract_text_from_pdf, extract_text_from_word
import pytest


class TestDOCXExtraction:
    def test_extract_text_from_word_with_only_text(self, file_resources):
        assert extract_text_from_word(file_resources["docx_text_only"]) == "This document has text!"

    def test_extract_text_from_word_with_empty_file(self, file_resources):
        assert extract_text_from_word(file_resources["docx_blank"]) == ""

    def test_extract_text_from_word_with_non_text_contents(self, file_resources):
        assert extract_text_from_word(file_resources["docx_text_and_media"]) == "This document has text!"

    def test_extract_text_from_word_with_special_characters(self, file_resources):
        assert extract_text_from_word(file_resources["docx_unicode_sample"])


class TestPDFExtraction:
    def test_extract_text_from_pdf_with_only_text(self, file_resources):
        assert extract_text_from_pdf(file_resources["pdf_text_only"]) == "This document has text!"

    def test_extract_text_from_pdf_with_empty_file(self, file_resources):
        assert extract_text_from_pdf(file_resources["pdf_blank"]) == ""

    def test_extract_text_from_pdf_with_non_text_contents(self, file_resources):
        # PyPDF2 will pull the text from charts also, so we cannot use == to compare
        assert "This document has text!" in extract_text_from_pdf(file_resources["pdf_text_and_media"])

    @pytest.mark.slow
    def test_extract_text_from_pdf_with_special_characters(self, file_resources):
        assert extract_text_from_pdf(file_resources["pdf_unicode_sample"])
