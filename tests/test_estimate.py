import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"


def run_estimate(args: list[str]) -> dict:
    cmd = [sys.executable, str(SCRIPTS / "estimate_downloads.py"), *args]
    proc = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return json.loads(proc.stdout)


def test_pure_calculation_without_benchmarks(tmp_path: Path):
    result = run_estimate(
        [
            "--appid",
            "demo",
            "--category",
            "Utilities",
            "--country",
            "US",
            "--total-ratings",
            "500",
            "--delta-ratings",
            "100",
            "--rank",
            "100",
            "--benchmark-dir",
            str(tmp_path),
        ]
    )
    assert result["methodology"] == "pure_calculation"
    assert result["est_monthly_downloads"] > 0
    assert result["confidence"] == "medium"


def test_waterline_cap_with_sample_benchmarks():
    result = run_estimate(
        [
            "--appid",
            "demo-wallet",
            "--category",
            "Finance / Banking",
            "--country",
            "US",
            "--total-ratings",
            "5000",
            "--delta-ratings",
            "5000",
            "--rank",
            "10",
            "--benchmark-dir",
            str(ROOT / "examples" / "benchmarks"),
        ]
    )
    assert result["methodology"] in {"waterline_capped", "waterline_validated"}
    assert result["confidence"] == "high"
    assert result["factors"]["benchmark_waterline"] is not None


def test_delta_normalization_flag_in_output():
    result = run_estimate(
        [
            "--appid",
            "demo",
            "--category",
            "Games",
            "--country",
            "US",
            "--total-ratings",
            "2000",
            "--delta-ratings",
            "70",
            "--snapshot-days",
            "7",
            "--rank",
            "50",
            "--benchmark-dir",
            str(ROOT / "examples" / "benchmarks"),
        ]
    )
    assert result["factors"]["snapshot_days"] == 7
    assert result["factors"]["delta_ratings_30d"] == 300.0
