from __future__ import annotations

import sys
from pathlib import Path


if __name__ == "__main__":
    package_root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(package_root))
    from executar import main

    raise SystemExit(main())
