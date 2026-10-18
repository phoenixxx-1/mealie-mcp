"""
Tests for image_path on the recipe and timeline image upload tools.

Uses real files, folders, symlinks and a FIFO under tmp_path. Every failing
case also checks that no Mealie client was created, i.e. nothing was uploaded.
"""

import asyncio
import json
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import respx
from httpx import Response

import src.client as client_module
from src.client import IMAGE_DIRS_ENV, MealieClient, allowed_image_dirs, load_image, read_image_path
from src.tools.recipes import recipes_image_upload
from src.tools.timeline import timeline_image_upload


JPEG = b"\xff\xd8\xff\xe0" + b"\x00" * 64
PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64
BASE_URL = "https://test.example.com"


@pytest.fixture(autouse=True)
def fresh_dir_cache():
    client_module._image_dirs_cache.clear()
    yield
    client_module._image_dirs_cache.clear()


@pytest.fixture
def images(tmp_path, monkeypatch):
    """An allowed folder (…/cache/images) with one photo in it."""
    folder = tmp_path / "cache" / "images"
    folder.mkdir(parents=True)
    (folder / "img_1.jpg").write_bytes(JPEG)
    monkeypatch.setenv(IMAGE_DIRS_ENV, str(folder))
    return folder


def mock_client():
    mock = MagicMock()
    mock.__enter__ = MagicMock(return_value=mock)
    mock.__exit__ = MagicMock(return_value=None)
    mock.upload_recipe_image.return_value = {
        "slug": "soup", "image": "new2", "previous_image": "old1", "format": "jpg", "bytes": len(JPEG)
    }
    mock.update_timeline_event_image.return_value = {
        "event_id": "ev-1", "has_image": True, "format": "jpg", "bytes": len(JPEG)
    }
    return mock


def upload(**kwargs):
    """Call the recipe tool with a mocked client; return (result, client class mock)."""
    with patch("src.tools.recipes.MealieClient", return_value=mock_client()) as client_class:
        data = json.loads(recipes_image_upload("soup", **kwargs))
    return data, client_class


class TestConfig:

    def test_unset_disables_image_path(self, monkeypatch):
        monkeypatch.delenv(IMAGE_DIRS_ENV, raising=False)
        data, client_class = upload(image_path="/anything/img.jpg")
        assert data["error"] == "image_path is disabled (MEALIE_MCP_IMAGE_DIRS not set)"
        client_class.assert_not_called()

    def test_empty_and_missing_entries_are_ignored(self, tmp_path, monkeypatch):
        monkeypatch.setenv(IMAGE_DIRS_ENV, f"::{tmp_path / 'nope'}: ")
        assert allowed_image_dirs() == []
        with pytest.raises(ValueError, match="is disabled"):
            read_image_path(str(tmp_path / "x.jpg"))

    def test_roots_are_real_paths(self, tmp_path, monkeypatch):
        real = tmp_path / "real_images"
        real.mkdir()
        link = tmp_path / "linked_images"
        link.symlink_to(real)
        (real / "a.jpg").write_bytes(JPEG)
        monkeypatch.setenv(IMAGE_DIRS_ENV, f"{link}:{tmp_path / 'missing'}")

        assert allowed_image_dirs() == [os.path.realpath(real)]
        assert read_image_path(str(link / "a.jpg")) == JPEG

    def test_several_folders(self, tmp_path, monkeypatch):
        first, second = tmp_path / "one", tmp_path / "two"
        first.mkdir()
        second.mkdir()
        (second / "b.png").write_bytes(PNG)
        monkeypatch.setenv(IMAGE_DIRS_ENV, f"{first}:{second}")
        assert read_image_path(str(second / "b.png")) == PNG


    def test_root_slash_is_refused(self, monkeypatch):
        monkeypatch.setenv(IMAGE_DIRS_ENV, "/")
        assert allowed_image_dirs() == []
        data, client_class = upload(image_path="/etc/hosts")
        assert "no usable folder in MEALIE_MCP_IMAGE_DIRS" in data["error"]
        client_class.assert_not_called()

    def test_set_but_missing_says_so_and_is_not_remembered(self, tmp_path, monkeypatch):
        folder = tmp_path / "later"
        monkeypatch.setenv(IMAGE_DIRS_ENV, str(folder))
        with pytest.raises(ValueError, match="no usable folder in MEALIE_MCP_IMAGE_DIRS"):
            read_image_path(str(folder / "a.jpg"))

        folder.mkdir()  # e.g. the agent downloads its first photo after startup
        (folder / "a.jpg").write_bytes(JPEG)
        assert read_image_path(str(folder / "a.jpg")) == JPEG

    def test_a_file_listed_as_a_folder_is_ignored(self, tmp_path, monkeypatch):
        (tmp_path / "not_a_dir").write_bytes(JPEG)
        monkeypatch.setenv(IMAGE_DIRS_ENV, str(tmp_path / "not_a_dir"))
        assert allowed_image_dirs() == []


class TestValidPath:

    def test_recipe_upload_from_path(self, images):
        data, client_class = upload(image_path=str(images / "img_1.jpg"))

        assert data["success"] is True
        assert data["source"] == "path"
        assert data["image"] == "new2" and data["previous_image"] == "old1"
        client_class.return_value.upload_recipe_image.assert_called_once_with("soup", JPEG)

    def test_file_is_left_untouched(self, images):
        photo = images / "img_1.jpg"
        before = (photo.read_bytes(), photo.stat().st_mtime_ns, photo.stat().st_mode)
        upload(image_path=str(photo))
        assert (photo.read_bytes(), photo.stat().st_mtime_ns, photo.stat().st_mode) == before
        assert sorted(p.name for p in images.iterdir()) == ["img_1.jpg"]

    def test_symlink_to_a_file_inside_the_folder_is_fine(self, images):
        (images / "alias.jpg").symlink_to(images / "img_1.jpg")
        data, _ = upload(image_path=str(images / "alias.jpg"))
        assert data["success"] is True

    def test_extension_is_ignored(self, images):
        (images / "photo.txt").write_bytes(PNG)
        data, client_class = upload(image_path=str(images / "photo.txt"))
        assert data["success"] is True
        client_class.return_value.upload_recipe_image.assert_called_once_with("soup", PNG)

    def test_timeline_upload_from_path(self, images):
        with patch("src.tools.timeline.MealieClient", return_value=mock_client()) as client_class:
            data = json.loads(timeline_image_upload("ev-1", image_path=str(images / "img_1.jpg")))
        assert data["success"] is True and data["source"] == "path"
        client_class.return_value.update_timeline_event_image.assert_called_once_with("ev-1", JPEG)

    @respx.mock
    def test_end_to_end_keys_come_from_mealie(self, images, monkeypatch):
        monkeypatch.setenv("MEALIE_URL", BASE_URL)
        monkeypatch.setenv("MEALIE_API_TOKEN", "token")
        respx.get(f"{BASE_URL}/api/recipes/soup").mock(side_effect=[
            Response(200, json={"slug": "soup", "image": "old1"}),
            Response(200, json={"slug": "soup", "image": "new2"}),
        ])
        put = respx.put(f"{BASE_URL}/api/recipes/soup/image").mock(return_value=Response(200, json={"image": "new2"}))

        data = json.loads(recipes_image_upload("soup", image_path=str(images / "img_1.jpg")))

        assert data["image"] == "new2" and data["previous_image"] == "old1" and data["source"] == "path"
        assert JPEG in put.calls[0].request.content


class TestRejectedPaths:
    """Each of these must fail with no upload."""

    def _rejects(self, path, message):
        data, client_class = upload(image_path=str(path))
        assert message in data["error"], data
        client_class.assert_not_called()
        return data

    def test_symlink_inside_pointing_to_etc_passwd(self, images):
        (images / "evil.jpg").symlink_to("/etc/passwd")
        self._rejects(images / "evil.jpg", "outside allowed folders")

    def test_dot_dot_traversal(self, images, tmp_path):
        (tmp_path / "config.yaml").write_text("secret: hunter2\n")
        data = self._rejects(f"{images}/../../config.yaml", "outside allowed folders")
        assert "hunter2" not in json.dumps(data)

    def test_sibling_folder_with_shared_prefix(self, images, tmp_path):
        sibling = tmp_path / "cache" / "images2"
        sibling.mkdir()
        (sibling / "img.jpg").write_bytes(JPEG)
        self._rejects(sibling / "img.jpg", "outside allowed folders")

    def test_relative_path(self, images):
        self._rejects("cache/images/img_1.jpg", "must be an absolute path")

    def test_directory(self, images):
        (images / "sub").mkdir()
        self._rejects(images / "sub", "not a regular file")

    def test_the_folder_itself(self, images):
        self._rejects(images, "not a regular file")

    def test_fifo_does_not_hang(self, images):
        os.mkfifo(images / "pipe.jpg")
        self._rejects(images / "pipe.jpg", "not a regular file")

    def test_missing_file(self, images):
        self._rejects(images / "nope.jpg", "not found")

    def test_eleven_megabytes(self, images):
        big = images / "big.jpg"
        big.write_bytes(JPEG + b"\x00" * (11 * 1024 * 1024))
        self._rejects(big, "too large (11.0 MB > 10.0 MB)")

    def test_jpg_that_is_really_text(self, images):
        (images / "notes.jpg").write_text("this is just text, not a photo\n")
        data = self._rejects(images / "notes.jpg", "unsupported format")
        assert "just text" not in json.dumps(data)

    def test_empty_file(self, images):
        (images / "empty.jpg").write_bytes(b"")
        self._rejects(images / "empty.jpg", "unsupported format")

    def test_both_params(self, images):
        data, client_class = upload(image_path=str(images / "img_1.jpg"), image_base64="AAAA")
        assert "exactly one of image_path or image_base64 (both were given)" in data["error"]
        client_class.assert_not_called()

    def test_neither_param(self, images):
        data, client_class = upload()
        assert "exactly one of image_path or image_base64 (neither was given)" in data["error"]
        client_class.assert_not_called()

    def test_long_paths_are_cut_short_in_errors(self, images):
        data = self._rejects("/" + "x" * 5000, "outside allowed folders")
        assert len(data["error"]) < 300

    def test_control_characters_are_escaped_in_errors(self, images):
        data = self._rejects("/elsewhere/a\nFAKE LOG LINE.jpg", "outside allowed folders")
        assert "\n" not in data["error"]

    def test_null_byte(self, images):
        self._rejects(f"{images}/img_1.jpg\x00.png", "must be an absolute path")

    def test_unreadable_file(self, images):
        locked = images / "locked.jpg"
        locked.write_bytes(JPEG)
        locked.chmod(0)
        try:
            if os.access(locked, os.R_OK):
                pytest.skip("running as a user who can read anything")
            self._rejects(locked, "permission denied")
        finally:
            locked.chmod(0o644)


class TestRaceSafety:

    def test_checks_use_the_opened_file(self, images, monkeypatch):
        """A file swapped for a symlink after realpath is refused by O_NOFOLLOW."""
        if not hasattr(os, "O_NOFOLLOW"):
            pytest.skip("O_NOFOLLOW not available")
        photo = images / "img_1.jpg"
        real_realpath = os.path.realpath

        def swap_then_resolve(path, *args, **kwargs):
            resolved = real_realpath(path, *args, **kwargs)
            if resolved == real_realpath(photo):
                photo.unlink()
                photo.symlink_to("/etc/passwd")
            return resolved

        monkeypatch.setattr(client_module.os.path, "realpath", swap_then_resolve)
        with pytest.raises(ValueError, match="can't be opened"):
            read_image_path(str(photo))

    def test_directory_swapped_for_a_symlink_mid_path(self, images, tmp_path, monkeypatch):
        """A folder on the path swapped for a symlink after realpath can't redirect the read."""
        sub = images / "sub"
        sub.mkdir()
        (sub / "photo.jpg").write_bytes(JPEG)
        outside = tmp_path / "outside"
        outside.mkdir()
        (outside / "photo.jpg").write_bytes(PNG)  # an image, so the format check wouldn't catch it
        real_realpath = os.path.realpath

        def swap_then_resolve(path, *args, **kwargs):
            resolved = real_realpath(path, *args, **kwargs)
            if resolved == real_realpath(sub / "photo.jpg"):
                (sub / "photo.jpg").unlink()
                sub.rmdir()
                sub.symlink_to(outside)
            return resolved

        monkeypatch.setattr(client_module.os.path, "realpath", swap_then_resolve)
        with pytest.raises(ValueError, match="can't be opened"):
            read_image_path(str(sub / "photo.jpg"))

    def test_reads_at_most_the_cap_plus_one(self, images, monkeypatch):
        monkeypatch.setattr(client_module, "IMAGE_MAX_BYTES", 32)
        photo = images / "img_1.jpg"  # 68 bytes, but pretend fstat said 10
        real_fstat = os.fstat

        class Small:
            def __init__(self, info):
                self._info = info

            def __getattr__(self, name):
                return 10 if name == "st_size" else getattr(self._info, name)

        monkeypatch.setattr(client_module.os, "fstat", lambda fd: Small(real_fstat(fd)))
        with pytest.raises(ValueError, match="too large \\(over 32 bytes\\)"):
            read_image_path(str(photo))


class TestLoadImage:

    def test_base64_source(self):
        import base64

        assert load_image(image_base64=base64.b64encode(PNG).decode()) == (PNG, "base64")

    def test_empty_strings_count_as_not_given(self, images):
        assert load_image(image_base64="", image_path=str(images / "img_1.jpg")) == (JPEG, "path")


class TestPublishedSchemas:

    def test_both_sources_are_optional_and_described(self):
        sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
        import server
        from fastmcp import Client

        async def fetch():
            async with Client(server.mcp) as client:
                return {
                    tool.name: getattr(tool, "input_schema", None) or tool.inputSchema
                    for tool in await client.list_tools()
                }

        tools = asyncio.run(fetch())
        for name, key in (("mealie_recipes_image_upload", "slug"), ("mealie_timeline_image_upload", "event_id")):
            schema = tools[name]
            assert schema["required"] == [key], name
            assert {"image_path", "image_base64"} <= set(schema["properties"]), name
            assert "Preferred over image_base64" in schema["properties"]["image_path"]["description"], name
