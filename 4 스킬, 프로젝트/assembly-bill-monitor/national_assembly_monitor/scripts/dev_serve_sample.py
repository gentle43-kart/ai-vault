"""개발·점검용: 인증키 없이 샘플 모드 + 별도 DB(data/dev_sample.db)로 웹 화면 실행."""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
os.chdir(ROOT)
sys.path.insert(0, str(ROOT))
os.environ["ASSEMBLY_SAMPLE_MODE"] = "1"
os.environ["ASSEMBLY_DATABASE_PATH"] = str(ROOT / "data" / "dev_sample.db")

import uvicorn  # noqa: E402

uvicorn.run("app.main:app", host="127.0.0.1", port=int(sys.argv[1]) if len(sys.argv) > 1 else 8765)
