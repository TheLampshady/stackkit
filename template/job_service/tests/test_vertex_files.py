"""How files are handed to the model."""

import base64

import pytest
from gcp_services.clients.gcp_vertex import (
    FileInput,
    ModelError,
    _claude_file_block,
    media_type,
)


def test_media_type_drops_parameters_and_case():
    assert media_type(FileInput(b"", "Text/Plain; charset=utf-8")) == "text/plain"
    assert media_type(FileInput(b"", "application/pdf")) == "application/pdf"


def test_claude_reads_text_as_text():
    block = _claude_file_block(FileInput(b"hello", "text/plain"))
    assert block == {"type": "text", "text": "hello"}


def test_claude_reads_pdfs_as_documents_and_images_as_images():
    pdf = _claude_file_block(FileInput(b"%PDF", "application/pdf"))
    assert pdf["type"] == "document"
    assert pdf["source"]["data"] == base64.standard_b64encode(b"%PDF").decode()
    assert _claude_file_block(FileInput(b"x", "image/png"))["type"] == "image"


def test_claude_refuses_types_it_cannot_read():
    with pytest.raises(ModelError):
        _claude_file_block(FileInput(b"x", "audio/mpeg"))
