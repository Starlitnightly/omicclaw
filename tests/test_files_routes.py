from pathlib import Path

from routes.files import _default_absolute_browser_root, _is_desktop_app_path


def test_default_absolute_browser_root_uses_launch_root_when_not_desktop_app(tmp_path: Path) -> None:
    launch_root = tmp_path / "workspace"
    launch_root.mkdir()

    assert _is_desktop_app_path(launch_root) is False
    assert _default_absolute_browser_root(launch_root) == launch_root.resolve()


def test_default_absolute_browser_root_falls_back_to_home_for_desktop_app_bundle() -> None:
    app_root = Path("/Applications/OmicClaw Desktop.app/Contents/Resources/app")

    assert _is_desktop_app_path(app_root) is True
    assert _default_absolute_browser_root(app_root) == Path.home().resolve()
