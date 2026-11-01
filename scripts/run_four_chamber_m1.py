"""Run this checkout's synthetic M1; outputs require --output."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'src'))
from physiosim.experiments.four_chamber_m1_demo import main

if __name__ == '__main__':
    raise SystemExit(main())
