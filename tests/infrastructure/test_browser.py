from aria.infrastructure.browser import normalize_user_url


def test_normalize_user_url_adds_https_scheme():
    url, error = normalize_user_url("example.com/path")
    assert error is None
    assert url == "https://example.com/path"


def test_normalize_user_url_rejects_non_http_scheme():
    url, error = normalize_user_url("file:///tmp/index.html")
    assert url is None
    assert error == "Only HTTP and HTTPS URLs are supported."


def test_normalize_user_url_rejects_empty_value():
    url, error = normalize_user_url("   ")
    assert url is None
    assert error == "Please enter a URL."
