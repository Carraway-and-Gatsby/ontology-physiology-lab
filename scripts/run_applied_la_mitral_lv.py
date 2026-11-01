"""Run the isolated workspace's private synthetic metadata demonstration."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'src'))
from physiosim.experiments.applied_la_mitral_lv_demo import main

if __name__ == '__main__':
    raise SystemExit(main())
