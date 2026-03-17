from pathlib import Path


def test_root_dockerignore_excludes_local_frontend_artifacts() -> None:
    dockerignore_path = Path(__file__).resolve().parents[2] / ".dockerignore"

    assert dockerignore_path.exists(), "Root .dockerignore must exist for Docker builds."

    entries = {
        line.strip()
        for line in dockerignore_path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.strip().startswith("#")
    }

    assert "frontend/node_modules" in entries
    assert "frontend/dist" in entries
    assert "**/__pycache__" in entries
