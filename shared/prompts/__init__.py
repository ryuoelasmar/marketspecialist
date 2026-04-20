from pathlib import Path


def load_prompt(name: str) -> str:
    path = Path(__file__).resolve().parent / f"{name}.md"
    return path.read_text()
