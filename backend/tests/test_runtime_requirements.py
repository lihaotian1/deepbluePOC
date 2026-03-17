from pathlib import Path


def test_backend_requirements_include_chapter_splitter_http_dependency() -> None:
    requirements_path = Path(__file__).resolve().parents[2] / "backend" / "requirements.txt"

    entries = {
        line.strip().split("==", 1)[0]
        for line in requirements_path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.strip().startswith("#")
    }

    assert "requests" in entries
