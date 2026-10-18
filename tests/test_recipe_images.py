"""
Tests for recipe and timeline image uploads.

Covers format detection from magic bytes, strict base64 decoding, URL
redaction, the size-capped download, the multipart uploads (including the
read-back that confirms the change took), the tool wrappers, the published
tool schemas, and that mealie_recipes_update no longer writes the image key.
"""

import asyncio
import base64
import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import httpx
import pytest
import respx
from httpx import Response

import src.client as client_module
from src.client import (
    MealieAPIError,
    MealieClient,
    decode_image_base64,
    detect_image_format,
    download_image,
    redact_url,
    validate_image_bytes,
)
from src.tools.recipes import recipes_image_upload, recipes_update, recipes_upload_image_from_url
from src.tools.timeline import timeline_image_upload, timeline_update_image


BASE_URL = "https://test.example.com"
TOKEN_URL = "https://api.telegram.org/file/bot123456:AAH-secret_token/photos/file_7.jpg"

JPEG = b"\xff\xd8\xff\xe0" + b"\x00" * 64
PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64
WEBP = b"RIFF\x00\x00\x00\x00WEBPVP8 " + b"\x00" * 64
HEIC = b"\x00\x00\x00\x18ftypheic\x00\x00\x00\x00mif1heic" + b"\x00" * 32
HEIC_MIF1 = b"\x00\x00\x00\x18ftypmif1\x00\x00\x00\x00mif1heic" + b"\x00" * 32
AVIF = b"\x00\x00\x00\x1cftypmif1\x00\x00\x00\x00mif1avifmiaf" + b"\x00" * 32
HTML = b"<!DOCTYPE html><html><body>404 Not Found</body></html>"
GIF = b"GIF89a" + b"\x00" * 64


def b64(data: bytes) -> str:
    return base64.b64encode(data).decode()


def mock_client():
    mock = MagicMock()
    mock.__enter__ = MagicMock(return_value=mock)
    mock.__exit__ = MagicMock(return_value=None)
    return mock


class TestDetectFormat:

    @pytest.mark.parametrize("data,expected", [
        (JPEG, ("jpg", "image/jpeg")),
        (PNG, ("png", "image/png")),
        (WEBP, ("webp", "image/webp")),
        (HEIC, ("heic", "image/heic")),
        (HEIC_MIF1, ("heic", "image/heic")),
        (AVIF, ("avif", "image/avif")),
    ])
    def test_supported_formats(self, data, expected):
        assert detect_image_format(data) == expected

    @pytest.mark.parametrize("data", [HTML, GIF, b"", b"hello", b"RIFF\x00\x00\x00\x00WAVE"])
    def test_everything_else_is_unknown(self, data):
        assert detect_image_format(data) is None


class TestValidateBytes:

    def test_returns_detected_format(self):
        assert validate_image_bytes(PNG) == ("png", "image/png")

    def test_empty(self):
        with pytest.raises(ValueError, match="Image is empty"):
            validate_image_bytes(b"")

    def test_too_big(self, monkeypatch):
        monkeypatch.setattr(client_module, "IMAGE_MAX_BYTES", 32)
        with pytest.raises(ValueError, match="the limit is"):
            validate_image_bytes(JPEG)

    def test_html_is_named(self):
        with pytest.raises(ValueError, match="looks like HTML"):
            validate_image_bytes(HTML)

    def test_gif_is_named(self):
        with pytest.raises(ValueError, match="GIF isn't a format"):
            validate_image_bytes(GIF)


class TestDecodeBase64:

    def test_plain(self):
        assert decode_image_base64(b64(PNG)) == PNG

    def test_data_url_prefix(self):
        assert decode_image_base64(f"data:image/png;base64,{b64(PNG)}") == PNG

    def test_whitespace_and_line_breaks_are_ignored(self):
        encoded = b64(JPEG)
        wrapped = "\n".join(encoded[i:i + 20] for i in range(0, len(encoded), 20))
        assert decode_image_base64(f"  {wrapped}\n") == JPEG

    @pytest.mark.parametrize("value,message", [
        ("", "Image is empty"),
        ("   ", "Image is empty"),
        ("data:image/png;base64,", "Image is empty"),
        ("not*base64!", "not valid base64"),
        ("abc", "not valid base64"),
        (b64(b"\xfb\xff\xbf" * 4).replace("+", "-").replace("/", "_"), "not valid base64"),
        ("data:text/html;base64,PGh0bWw+", "not an image"),
        ("data:image/png,rawbytes", "must be base64-encoded"),
    ])
    def test_rejects(self, value, message):
        with pytest.raises(ValueError, match=message):
            decode_image_base64(value)

    def test_non_string(self):
        with pytest.raises(ValueError, match="must be a string"):
            decode_image_base64(JPEG)

    def test_oversized_payload_is_rejected_before_decoding(self, monkeypatch):
        monkeypatch.setattr(client_module, "IMAGE_MAX_BYTES", 16)
        with patch("src.client.base64.b64decode") as decode:
            with pytest.raises(ValueError, match="the limit is"):
                decode_image_base64(b64(JPEG))
        decode.assert_not_called()


class TestRedactUrl:

    @pytest.mark.parametrize("url,expected", [
        (TOKEN_URL, "https://api.telegram.org/file/bot<redacted>/photos/file_7.jpg"),
        ("https://user:pw@cdn.example/a.jpg?token=abc&w=100#x",
         "https://<redacted>@cdn.example/a.jpg?token=<redacted>&w=<redacted>"),
        ("https://example.com/a.jpg", "https://example.com/a.jpg"),
    ])
    def test_redaction(self, url, expected):
        assert redact_url(url) == expected


class TestDownload:

    @respx.mock
    def test_image_is_returned_with_detected_format(self):
        respx.get("https://img.example/p").mock(
            return_value=Response(200, content=PNG, headers={"content-type": "image/jpeg"})
        )
        # The bytes decide the format, not the declared type
        assert download_image("https://img.example/p") == (PNG, "png", "image/png")

    @respx.mock
    def test_octet_stream_is_checked_by_magic_bytes(self):
        respx.get(TOKEN_URL).mock(
            return_value=Response(200, content=HEIC, headers={"content-type": "application/octet-stream"})
        )
        assert download_image(TOKEN_URL)[1] == "heic"

    @respx.mock
    def test_html_content_type_is_an_error(self):
        respx.get("https://img.example/p").mock(
            return_value=Response(200, content=HTML, headers={"content-type": "text/html; charset=utf-8"})
        )
        with pytest.raises(ValueError, match="returned text/html, not an image"):
            download_image("https://img.example/p")

    @respx.mock
    def test_html_body_with_octet_stream_is_an_error(self):
        respx.get("https://img.example/p").mock(
            return_value=Response(200, content=HTML, headers={"content-type": "application/octet-stream"})
        )
        with pytest.raises(ValueError, match="looks like HTML"):
            download_image("https://img.example/p")

    @respx.mock
    def test_http_error_hides_the_token(self):
        respx.get(TOKEN_URL).mock(return_value=Response(404, content=HTML))
        with pytest.raises(ValueError) as error:
            download_image(TOKEN_URL)
        assert "HTTP 404" in str(error.value)
        assert "secret_token" not in str(error.value)
        assert "bot<redacted>" in str(error.value)

    @respx.mock
    def test_connection_error_hides_the_token(self):
        respx.get(TOKEN_URL).mock(side_effect=httpx.ConnectError(f"cannot reach {TOKEN_URL}"))
        with pytest.raises(ValueError) as error:
            download_image(TOKEN_URL)
        assert "secret_token" not in str(error.value)

    @respx.mock
    def test_declared_size_over_the_cap(self):
        respx.get("https://img.example/p").mock(
            return_value=Response(200, content=JPEG, headers={"content-length": str(50 * 1024 * 1024)})
        )
        with pytest.raises(ValueError, match="the limit is"):
            download_image("https://img.example/p")

    @respx.mock
    def test_streamed_size_over_the_cap(self):
        """No Content-Length (a chunked response): the cap is enforced while reading."""
        respx.get("https://img.example/p").mock(return_value=Response(200, content=iter([JPEG[:32], JPEG[32:]])))
        with pytest.raises(ValueError, match="larger than the 16 bytes limit"):
            download_image("https://img.example/p", max_bytes=16)

    def test_only_http_urls(self):
        with pytest.raises(ValueError, match="must be http or https"):
            download_image("file:///etc/passwd")


def recipe(image):
    return {"id": "recipe-1", "slug": "soup", "name": "Soup", "image": image}


class TestRecipeUpload:

    @respx.mock
    def test_upload_sends_multipart_with_detected_extension_and_confirms(self):
        respx.get(f"{BASE_URL}/api/recipes/soup").mock(side_effect=[
            Response(200, json=recipe("old1")), Response(200, json=recipe("new2")),
        ])
        put = respx.put(f"{BASE_URL}/api/recipes/soup/image").mock(
            return_value=Response(200, json={"image": "new2"})
        )

        result = MealieClient(BASE_URL, "token").upload_recipe_image("soup", HEIC)

        assert result == {"slug": "soup", "image": "new2", "previous_image": "old1",
                          "format": "heic", "bytes": len(HEIC)}
        request = put.calls[0].request
        assert request.headers["content-type"].startswith("multipart/form-data; boundary=")
        assert request.headers["authorization"] == "Bearer token"
        body = request.content
        assert b'name="extension"\r\n\r\nheic' in body
        assert b'filename="image.heic"' in body and HEIC in body

    @respx.mock
    def test_unchanged_key_is_an_error(self):
        respx.get(f"{BASE_URL}/api/recipes/soup").mock(return_value=Response(200, json=recipe("same")))
        respx.put(f"{BASE_URL}/api/recipes/soup/image").mock(return_value=Response(200, json={"image": "same"}))

        with pytest.raises(MealieAPIError, match="still has image key"):
            MealieClient(BASE_URL, "token").upload_recipe_image("soup", JPEG)

    @respx.mock
    def test_rejected_upload_is_an_error(self):
        respx.get(f"{BASE_URL}/api/recipes/soup").mock(return_value=Response(200, json=recipe("old1")))
        respx.put(f"{BASE_URL}/api/recipes/soup/image").mock(
            return_value=Response(400, json={"detail": "bad image"})
        )
        with pytest.raises(MealieAPIError) as error:
            MealieClient(BASE_URL, "token").upload_recipe_image("soup", JPEG)
        assert error.value.status_code == 400

    @respx.mock
    def test_invalid_bytes_make_no_request(self):
        route = respx.route(host="test.example.com")
        with pytest.raises(ValueError, match="looks like HTML"):
            MealieClient(BASE_URL, "token").upload_recipe_image("soup", HTML)
        assert not route.called

    @respx.mock
    def test_url_upload_checks_the_download_before_touching_the_recipe(self):
        respx.get("https://img.example/p").mock(
            return_value=Response(200, content=HTML, headers={"content-type": "text/html"})
        )
        mealie = respx.route(host="test.example.com")
        with pytest.raises(ValueError, match="not an image"):
            MealieClient(BASE_URL, "token").upload_recipe_image_from_url("soup", "https://img.example/p")
        assert not mealie.called


class TestTimelineUpload:

    @respx.mock
    def test_upload_is_multipart_not_json(self):
        """The old upload sent the multipart body labelled application/json."""
        put = respx.put(f"{BASE_URL}/api/recipes/timeline/events/ev-1/image").mock(
            return_value=Response(200, json={"image": "has image"})
        )
        respx.get(f"{BASE_URL}/api/recipes/timeline/events/ev-1").mock(
            return_value=Response(200, json={"id": "ev-1", "image": "has image"})
        )

        result = MealieClient(BASE_URL, "token").update_timeline_event_image("ev-1", PNG, extension="jpg")

        assert result == {"event_id": "ev-1", "has_image": True, "format": "png", "bytes": len(PNG)}
        request = put.calls[0].request
        assert request.headers["content-type"].startswith("multipart/form-data")
        assert b'name="extension"\r\n\r\npng' in request.content  # caller's "jpg" is ignored

    @respx.mock
    def test_event_without_image_after_upload_is_an_error(self):
        respx.put(f"{BASE_URL}/api/recipes/timeline/events/ev-1/image").mock(
            return_value=Response(200, json={"image": "has image"})
        )
        respx.get(f"{BASE_URL}/api/recipes/timeline/events/ev-1").mock(
            return_value=Response(200, json={"id": "ev-1", "image": "does not have image"})
        )
        with pytest.raises(MealieAPIError, match="reports no image"):
            MealieClient(BASE_URL, "token").update_timeline_event_image("ev-1", PNG)


class TestToolWrappers:

    def test_recipe_bytes_tool(self):
        mock = mock_client()
        mock.upload_recipe_image.return_value = {"slug": "soup", "image": "new2", "previous_image": "old1",
                                                 "format": "jpg", "bytes": len(JPEG)}
        with patch("src.tools.recipes.MealieClient", return_value=mock):
            data = json.loads(recipes_image_upload("soup", b64(JPEG)))

        assert data["success"] is True and data["image"] == "new2"
        mock.upload_recipe_image.assert_called_once_with("soup", JPEG)

    def test_bad_base64_never_opens_a_client(self):
        with patch("src.tools.recipes.MealieClient") as client_class:
            data = json.loads(recipes_image_upload("soup", "not*base64"))
        assert "not valid base64" in data["error"]
        client_class.assert_not_called()

    def test_timeline_bytes_tool(self):
        mock = mock_client()
        mock.update_timeline_event_image.return_value = {"event_id": "ev-1", "has_image": True,
                                                         "format": "heic", "bytes": len(HEIC)}
        with patch("src.tools.timeline.MealieClient", return_value=mock):
            data = json.loads(timeline_image_upload("ev-1", b64(HEIC)))

        assert data["success"] is True and data["format"] == "heic"
        mock.update_timeline_event_image.assert_called_once_with("ev-1", HEIC)

    @respx.mock
    def test_recipe_url_tool_never_shows_the_token(self):
        respx.get(TOKEN_URL).mock(return_value=Response(404))
        data = json.loads(recipes_upload_image_from_url("soup", TOKEN_URL))
        assert "secret_token" not in json.dumps(data)

    @respx.mock
    def test_timeline_url_tool_never_shows_the_token(self):
        respx.get(TOKEN_URL).mock(
            return_value=Response(200, content=JPEG, headers={"content-type": "application/octet-stream"})
        )
        mock = mock_client()
        mock.update_timeline_event_image.return_value = {"event_id": "ev-1", "has_image": True,
                                                         "format": "jpg", "bytes": len(JPEG)}
        with patch("src.tools.timeline.MealieClient", return_value=mock):
            data = json.loads(timeline_update_image("ev-1", TOKEN_URL))

        assert data["success"] is True
        assert "secret_token" not in json.dumps(data)


class TestRecipesUpdateKeepsImage:

    def test_existing_key_is_always_sent_back(self):
        mock = mock_client()
        mock.get.return_value = {**recipe("keep-me"), "groupId": "g", "userId": "u",
                                 "recipeIngredient": [], "recipeInstructions": []}
        with patch("src.tools.recipes.MealieClient", return_value=mock):
            recipes_update("soup", name="Better soup")

        sent = (mock.put.call_args or mock.patch.call_args).kwargs["json"]
        assert sent["image"] == "keep-me"

    def test_tags_only_update_keeps_the_key_too(self):
        """Tag-only updates take the PATCH path, which used to check `image`."""
        mock = mock_client()
        mock.get.return_value = {**recipe("keep-me"), "groupId": "g", "userId": "u", "tags": []}
        with patch("src.tools.recipes.MealieClient", return_value=mock), \
                patch("src.tools.recipes._resolve_tags", return_value=[{"name": "soup"}]):
            data = json.loads(recipes_update("soup", tags=["soup"]))

        assert "error" not in data, data
        mock.put.assert_not_called()
        assert mock.patch.call_args.kwargs["json"]["image"] == "keep-me"

    def test_image_is_no_longer_a_parameter(self):
        with pytest.raises(TypeError):
            recipes_update("soup", image="zzzzTEST")


class TestPublishedSchemas:

    @staticmethod
    def _tools():
        sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
        import server
        from fastmcp import Client

        async def fetch():
            async with Client(server.mcp) as client:
                return {
                    tool.name: getattr(tool, "input_schema", None) or tool.inputSchema
                    for tool in await client.list_tools()
                }, client

        return asyncio.run(fetch())[0], server

    def test_new_tools_take_base64(self):
        tools, _ = self._tools()
        assert set(tools["mealie_recipes_image_upload"]["required"]) == {"slug", "image_base64"}
        assert set(tools["mealie_timeline_image_upload"]["required"]) == {"event_id", "image_base64"}

    def test_recipes_update_has_no_image_and_rejects_it(self):
        tools, server = self._tools()
        schema = tools["mealie_recipes_update"]
        assert "image" not in schema["properties"]
        assert schema["additionalProperties"] is False

        from fastmcp import Client

        async def call():
            async with Client(server.mcp) as client:
                return await client.call_tool(
                    "mealie_recipes_update", {"slug": "soup", "image": "zzzzTEST"}, raise_on_error=False
                )

        with patch("tools.recipes.MealieClient") as client_class:
            result = asyncio.run(call())
        assert result.is_error
        client_class.assert_not_called()
