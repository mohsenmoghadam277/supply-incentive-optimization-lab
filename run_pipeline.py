"""Run the complete reproducible portfolio workflow from synthetic data to model artifact."""
from __future__ import annotations
import argparse
from pathlib import Path
import json
import pandas as pd
from src.config import ASSUMED_GROSS_MARGIN_TOMAN, ARTIFACT_DIR, DATA_DIR, OUTPUT_DIR, SEED
from src.generate_data import generate_datasets
from src.analyze_experiment import analyze_experiment
from src.train_uplift import train_and_score
from src.monitoring import make_monitoring_snapshot
from src.sync_dashboard import sync_dashboard
from src.quality_checks import validate_datasets
from src.make_charts import make_charts


def run(output_root: Path | None = None, seed: int = SEED, margin_per_trip: float = ASSUMED_GROSS_MARGIN_TOMAN) -> dict:
    # Paths remain project-local for reproducibility; optional output_root supports test/CI runs.
    if output_root is None:
        data_dir, output_dir, artifact_dir = DATA_DIR, OUTPUT_DIR, ARTIFACT_DIR
    else:
        output_root.mkdir(parents=True, exist_ok=True)
        data_dir, output_dir, artifact_dir = output_root / "data" / "raw", output_root / "project_outputs", output_root / "artifacts"
    exp, candidates = generate_datasets(data_dir, seed)
    quality = validate_datasets(exp, candidates, output_dir / "data_quality_report.json")
    analysis = analyze_experiment(exp, output_dir, margin_per_trip)
    model = train_and_score(exp, candidates, output_dir, artifact_dir, seed, margin_per_trip)
    monitoring = make_monitoring_snapshot(exp, candidates, model["recommendations"], output_dir / "monitoring_snapshot.json")
    figures = make_charts(output_dir)
    report = {
        "project": "Incentive Lab — Supply Incentive Optimization (independent portfolio)",
        "data_classification": "synthetic_educational_data",
        "seed": seed,
        "experiment_rows": int(len(exp)),
        "candidate_rows": int(len(candidates)),
        "treatment_n": int(exp.treatment.sum()),
        "control_n": int((exp.treatment == 0).sum()),
        "trip_lift": analysis["economics"]["trip_lift_per_assigned_driver"],
        "assumed_margin_toman_per_trip": margin_per_trip,
        "scenario_roi": analysis["economics"]["estimated_roi"],
        "recommendations_top20_n": int(model["recommendations"]["recommended_for_top_20pct"].sum()),
        "model_type": "T-learner with separate RandomForestRegressor outcome models",
        "data_quality_status": quality["status"],
        "static_figures": [str(p.relative_to(output_dir)) for p in figures],
        "api_model_artifact": "artifacts/uplift_model.joblib",
        "note": "Metrics are generated from synthetic data; never describe as actual Snapp campaign performance.",
    }
    (output_dir / "run_report_fa.txt").write_text(
        "گزارش اجرای خط لوله پروژه (داده مصنوعی)\n"
        "======================================\n\n"
        f"داده آزمایش: {len(exp):,} راننده | گروه مشوق: {int(exp.treatment.sum()):,} | کنترل: {int((exp.treatment == 0).sum()):,}\n"
        f"جامعه امتیازدهی مستقل: {len(candidates):,} راننده\n"
        f"افزایش مشاهده‌شده سفر در آزمایش A/B: {analysis['economics']['trip_lift_per_assigned_driver']:.3f} سفر (فاصله اطمینان ۹۵٪: {analysis['economics']['trip_lift_ci95_low']:.3f} تا {analysis['economics']['trip_lift_ci95_high']:.3f})\n"
        f"حاشیه سود فرضی هر سفر: {margin_per_trip:,.0f} تومان | ROI سناریویی: {analysis['economics']['estimated_roi']:.1%}\n"
        f"مدل: T-Learner با دو RandomForestRegressor مستقل؛ MAE کنترل: {model['validation']['control_test_mae_trips']:.3f}؛ MAE آزمایش: {model['validation']['treatment_test_mae_trips']:.3f}\n"
        f"رانندگان رتبه‌بندی‌شده برای بررسی (۲۰٪ بالای امتیاز): {int(model['recommendations']['recommended_for_top_20pct'].sum()):,}\n"
        f"کنترل کیفیت داده: {quality['status']} | نمودارهای خروجی: {len(figures)}\n"
        f"اثر تعدیل‌شده (بررسی ثانویه): {analysis['adjusted']['treatment_coefficient_trips']:.3f} سفر؛ برآورد اصلی A/B در بالا گزارش شده است. جزئیات در adjusted_effect_check.json\n"
        f"فایل مدل برای API: artifacts/uplift_model.joblib\n\n"
        "محدودیت: داده‌ها کاملاً مصنوعی‌اند. ROI سناریویی است و پیش‌بینی uplift برای هر فرد اثر علّی قطعی را اثبات نمی‌کند. هدف‌گیری باید در آزمایش تصادفی آینده‌نگر ارزیابی شود.\n",
        encoding="utf-8",
    )
    (output_dir / "pipeline_summary.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    if output_root is None:
        sync_dashboard()
    return {"analysis": analysis, "model": model, "monitoring": monitoring, "quality": quality, "figures": figures, "summary": report}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=SEED)
    parser.add_argument("--margin-per-trip", type=float, default=ASSUMED_GROSS_MARGIN_TOMAN)
    parser.add_argument("--output-root", type=Path, default=None, help="Optional isolated root for reproducibility/testing.")
    args = parser.parse_args()
    result = run(args.output_root, args.seed, args.margin_per_trip)
    print("Pipeline completed successfully (synthetic data only).")
    print(f"Data quality: {result['quality']['status']} | Figures created: {len(result['figures'])}")
    print(json.dumps(result["summary"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
