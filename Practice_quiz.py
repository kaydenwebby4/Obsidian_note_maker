import argparse
import re
from pathlib import Path

import requests

OLLAMA_URL = "http://localhost:11434/api/generate"
OUT_DIR_NAME = "Practice"



PROMPT = """You are a study assistant. From the notes below, write exactly {n} practice \
questions, each followed by a worked answer.

Rules:
- Write exactly {n} questions. Numbered Q1 to Q{n}. Do not stop early
- Try to only use information from the notes.
- Write answers in plain text, Use LaTeX($..$) only for math.
- Do include any links or URLs
- Format exactly like this:


### Q1
Question text

**Answer:** worked answer

### Q2
Question text

**Answer:** worked answer

NOTES:
{notes}
"""


def strip_frontmatter(text: str) -> str:
    return re.sub(r"\A---\n.*?\n---\n", "", text, flags=re.S)




def generate(notes: str, model: str, n: int) -> str:
    r = requests.post(
        OLLAMA_URL,
        json={"model": model, "prompt": PROMPT.format(n=n, notes=notes), "stream": False, "options":{"num_ctx":8192}},
        timeout=600,
    )
    r.raise_for_status()

    return r.json()["response"].strip()


def process_note(path: Path, root: Path, model: str, n: int, force: bool) -> None:
    out_path = root / OUT_DIR_NAME / path.relative_to(root).parent / f"{path.stem} - Practice.md"
    if out_path.exists() and not force:
        print(f"skip (exists): {path.name}")
        return

    text = strip_frontmatter(path.read_text(encoding="utf-8"))
    if not text.strip():
        print(f"skip (empty): {path.name}")
        return

    print(f"  generating: {path.name}...")
    body = generate(text, model, n)

    header = (
        "---\n"
        f"source: \"[[{path.stem}]]\"\n"
        f"model: {model}\n"
        "tags: [practice, ai-generated]\n"
        "reviewed: false\n"
        "---\n\n"
        f"Practice questions for [[{path.stem}]]\n\n"
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(header + body + "\n", encoding="utf-8")
    print(f"wrote: {out_path.relative_to(root)}")


def main() -> None:
    ap = argparse.ArgumentParser(description="Generate practice questions from Obsidian notes.")
    ap.add_argument("folder", type=Path, help="vault or class folder to scan")
    ap.add_argument("--model", default="qwen2.5:7b")
    ap.add_argument("--questions", type=int, default=5, help="questions per note")
    ap.add_argument("--force", action="store_true", help="regenerate existing files")
    args = ap.parse_args()

    root = args.folder.expanduser().resolve()
    notes = [
        p for p in sorted(root.rglob("*.md"))
        if OUT_DIR_NAME not in p.relative_to(root).parts
        and ".obsidian" not in p.parts
    ]
    print(f"Found {len(notes)} notes")
    for p in notes:
        process_note(p, root, args.model, args.questions, args.force)


if __name__ == "__main__":
    main()