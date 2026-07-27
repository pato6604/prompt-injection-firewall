from app.proxy.request_parser import parse_request
import pytest


def test_parse_valid_request():
    body = {
        "model": "gpt-4o-mini",
        "messages": [{"role": "user", "content": "Hello"}],
    }
    result = parse_request(body)
    assert result.model == "gpt-4o-mini"
    assert len(result.messages) == 1
    assert result.messages[0].content == "Hello"


def test_parse_empty_messages():
    body = {
        "model": "gpt-4o-mini",
        "messages": [],
    }
    with pytest.raises(ValueError, match="messages.*empty"):
        parse_request(body)


def test_parse_missing_messages():
    body = {"model": "gpt-4o-mini"}
    with pytest.raises(ValueError, match="messages.*empty"):
        parse_request(body)


def test_parse_empty_content():
    body = {
        "model": "gpt-4o-mini",
        "messages": [{"role": "user", "content": "   "}],
    }
    with pytest.raises(ValueError, match="content.*empty"):
        parse_request(body)


def test_parse_empty_model():
    body = {
        "model": "",
        "messages": [{"role": "user", "content": "Hello"}],
    }
    with pytest.raises(ValueError, match="model.*empty"):
        parse_request(body)
