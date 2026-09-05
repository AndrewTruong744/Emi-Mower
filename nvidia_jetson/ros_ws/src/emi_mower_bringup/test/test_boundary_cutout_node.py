from pathlib import Path

from emi_mower_bringup.cutout_download import download_cutout


def test_download_cutout_writes_atomically(monkeypatch, tmp_path: Path) -> None:
    class Response:
        def __enter__(self): return self
        def __exit__(self, *_args): return False
        def read(self, _size):
            if getattr(self, "done", False): return b""
            self.done = True
            return b"boundary"

    monkeypatch.setattr(
        "emi_mower_bringup.cutout_download.urlopen", lambda *_args, **_kwargs: Response()
    )
    destination = tmp_path / "cutouts" / "boundary.png"
    download_cutout("https://example.test/cutout", destination)
    assert destination.read_bytes() == b"boundary"
    assert not destination.with_suffix(".png.part").exists()
