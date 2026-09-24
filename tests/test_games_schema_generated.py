import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parents[1]
GENERATED = ROOT / "src/tribunal/knowledge/games_schema.py"


def test_generated_schema_is_up_to_date(tmp_path: Path) -> None:
    """games.schema.json を変えたら `uv run datamodel-codegen` で再生成して commit する。"""
    output = tmp_path / "games_schema.py"

    subprocess.run(
        [sys.executable, "-m", "datamodel_code_generator", "--output", str(output)],
        cwd=ROOT,
        check=True,
    )

    assert output.read_text(encoding="utf-8") == GENERATED.read_text(encoding="utf-8")
