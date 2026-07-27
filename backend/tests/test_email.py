"""
Unit tests for app/email.py — the Resend-backed send_email(). No real network
calls are made; httpx.post is monkeypatched throughout.
"""
import httpx
import pytest

from app import email as email_module


class _FakeResponse:
    def __init__(self, status_code, text="error detail"):
        self.status_code = status_code
        self.text = text


class TestSendEmail:
    def test_returns_false_without_raising_when_key_missing(self, monkeypatch):
        monkeypatch.setattr(email_module, "RESEND_API_KEY", "")
        assert email_module.send_email("a@example.com", "Subject", "<p>hi</p>") is False

    def test_returns_true_on_success(self, monkeypatch):
        monkeypatch.setattr(email_module, "RESEND_API_KEY", "fake-key")
        monkeypatch.setattr(email_module.httpx, "post", lambda *a, **k: _FakeResponse(200))
        assert email_module.send_email("a@example.com", "Subject", "<p>hi</p>") is True

    def test_provider_error_response_returns_false_without_raising(self, monkeypatch):
        monkeypatch.setattr(email_module, "RESEND_API_KEY", "fake-key")
        monkeypatch.setattr(email_module.httpx, "post", lambda *a, **k: _FakeResponse(500, "internal error"))
        assert email_module.send_email("a@example.com", "Subject", "<p>hi</p>") is False

    def test_network_exception_does_not_propagate(self, monkeypatch):
        monkeypatch.setattr(email_module, "RESEND_API_KEY", "fake-key")

        def boom(*a, **k):
            raise httpx.ConnectError("connection refused")
        monkeypatch.setattr(email_module.httpx, "post", boom)

        assert email_module.send_email("a@example.com", "Subject", "<p>hi</p>") is False

    def test_timeout_does_not_propagate(self, monkeypatch):
        monkeypatch.setattr(email_module, "RESEND_API_KEY", "fake-key")

        def boom(*a, **k):
            raise httpx.TimeoutException("timed out")
        monkeypatch.setattr(email_module.httpx, "post", boom)

        assert email_module.send_email("a@example.com", "Subject", "<p>hi</p>") is False

    def test_sends_from_verified_domain(self, monkeypatch):
        captured = {}

        def fake_post(url, headers, json, timeout):
            captured.update(json=json, headers=headers, url=url)
            return _FakeResponse(200)

        monkeypatch.setattr(email_module, "RESEND_API_KEY", "fake-key")
        monkeypatch.setattr(email_module.httpx, "post", fake_post)

        email_module.send_email("someone@example.com", "Hello", "<p>hi</p>")
        assert captured["json"]["from"] == "noreply@fivera.co.uk"
        assert captured["json"]["to"] == ["someone@example.com"]
        assert captured["headers"]["Authorization"] == "Bearer fake-key"
