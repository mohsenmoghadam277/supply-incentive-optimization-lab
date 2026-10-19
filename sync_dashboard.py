"""Synchronize the embedded DATA payload in the standalone HTML dashboard from pipeline outputs."""
from __future__ import annotations
import json
import re
from pathlib import Path
import pandas as pd
from src.config import OUTPUT_DIR, ROOT

DASHBOARD_PATH = ROOT / "snapp_incentive_dashboard_v3.html"


def _records(path: Path, columns: list[str] | None = None) -> list[dict]:
    df = pd.read_csv(path)
    if columns:
        df = df[columns]
    df = df.astype(object).where(pd.notna(df), None)
    return df.to_dict(orient="records")


def sync_dashboard(dashboard_path: Path = DASHBOARD_PATH, output_dir: Path = OUTPUT_DIR) -> Path:
    html = dashboard_path.read_text(encoding="utf-8")
    exp = _records(output_dir / "experiment_summary.csv")
    segments = _records(output_dir / "segment_summary.csv")
    recommendations = _records(
        output_dir / "scored_candidates.csv",
        [
            "driver_id", "zone", "daypart", "avg_online_hours_4w", "avg_trips_4w",
            "cancellation_rate", "demand_index", "predicted_trips_without_incentive",
            "predicted_trips_with_incentive", "predicted_incremental_trips",
            "assumed_expected_cost_toman", "predicted_incremental_trips_per_100k_toman",
            "recommended_for_top_20pct",
        ],
    )
    economics = json.loads((output_dir / "campaign_economics.json").read_text(encoding="utf-8"))
    model = json.loads((output_dir / "model_validation.json").read_text(encoding="utf-8"))
    payload = {"recommendations": recommendations, "segments": segments, "experiment": exp, "economics": economics, "model": model}
    compact = json.dumps(payload, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
    pattern = re.compile(r"const DATA=\{.*?\};\s*const \$=", re.S)
    match = pattern.search(html)
    if not match:
        raise RuntimeError("Could not find the dashboard's embedded `const DATA={...}; const $=` payload.")
    html = html[:match.start()] + f"const DATA={compact}; const $=" + html[match.end():]

    # The incentive cost is an accounting quantity, not a tested experimental outcome.
    old = "$('experiment-table').innerHTML=rows.map(([label,key,fmt])=>{let a=getMetric(key);const p=+a.p_value_welch;return `<tr><td>${label}</td><td class=\"number\">${fmt(+a.control_mean)}</td><td class=\"number\">${fmt(+a.treatment_mean)}</td><td class=\"number\">${fmt(+a.difference_treatment_minus_control)}</td><td class=\"number\">${fmt(+a.ci95_low)} تا ${fmt(+a.ci95_high)}</td><td class=\"number\">${p===0?'تقریباً صفر':p.toExponential(2)}</td></tr>`}).join('');"
    new = "$('experiment-table').innerHTML=rows.map(([label,key,fmt])=>{let a=getMetric(key);const isCost=key==='incentive_cost_toman';const p=Number(a.p_value_welch);const ci=isCost?'—':`${fmt(+a.ci95_low)} تا ${fmt(+a.ci95_high)}`;const pv=isCost?'—':(p===0?'تقریباً صفر':p.toExponential(2));return `<tr><td>${label}</td><td class=\"number\">${fmt(+a.control_mean)}</td><td class=\"number\">${fmt(+a.treatment_mean)}</td><td class=\"number\">${fmt(+a.difference_treatment_minus_control)}</td><td class=\"number\">${ci}</td><td class=\"number\">${pv}</td></tr>`}).join('');"
    if old in html:
        html = html.replace(old, new)
    elif new not in html:
        raise RuntimeError("Could not locate expected experiment table renderer; refusing a partial sync.")
    html = html.replace('<span class="ico">⌁</span>مدل انتخاب راننده</button>', '<span class="ico">⌁</span>مدل برآورد uplift</button>')
    html = html.replace("model:'مدل انتخاب راننده'", "model:'مدل برآورد uplift'")

    # Mark the summary values as data-bound so stale v3 literals cannot contradict the regenerated outputs.
    html = html.replace('>+۲٫۲۹۴ <small style="font-size:13px;font-weight:600">سفر</small>', '><span id="hero-lift">+۲٫۰۰</span> <small style="font-size:13px;font-weight:600">سفر</small>')
    html = html.replace('>فاصله اطمینان: ۱٫۶۷ تا ۲٫۹۲ سفر</div>', ' id="hero-lift-ci">فاصله اطمینان: —</div>')
    html = html.replace('<div class="kpi-value pos">۵٫۵٪</div>', '<div class="kpi-value pos" id="hero-relative">—</div>')
    html = html.replace('<div class="econ-item"><span>R² کنترل</span><b>۰٫۷۹۹</b></div>', '<div class="econ-item"><span>R² کنترل</span><b id="model-r2-control">—</b></div>')
    html = html.replace('<div class="econ-item"><span>R² آزمایش</span><b>۰٫۷۹۸</b></div>', '<div class="econ-item"><span>R² آزمایش</span><b id="model-r2-treatment">—</b></div>')
    html = html.replace('<div class="econ-item"><span>RMSE کنترل</span><b>۷٫۷۶</b></div>', '<div class="econ-item"><span>RMSE کنترل</span><b id="model-rmse-control">—</b></div>')
    html = html.replace('<div class="econ-item"><span>RMSE آزمایش</span><b>۷٫۶۴</b></div>', '<div class="econ-item"><span>RMSE آزمایش</span><b id="model-rmse-treatment">—</b></div>')

    # Fill the dashboard from the synchronized experiment and holdout model outputs.
    html = html.replace(
        "if($('brief-control'))$('brief-control').textContent=faNum(+a.control_mean,2);",
        "if($('hero-lift'))$('hero-lift').textContent=(lift>=0?'+':'')+faNum(lift,2);if($('hero-lift-ci'))$('hero-lift-ci').textContent='فاصله اطمینان ۹۵٪: '+faNum(+a.ci95_low,2)+' تا '+faNum(+a.ci95_high,2)+' سفر';if($('hero-relative'))$('hero-relative').textContent=(relative>=0?'+':'')+faNum(relative,1)+'٪';if($('brief-control'))$('brief-control').textContent=faNum(+a.control_mean,2);"
    )
    html = html.replace(
        "if($('top20-avg-uplift'))$('top20-avg-uplift').textContent='+'+faNum(top.reduce((s,r)=>s+Number(r.predicted_incremental_trips),0)/Math.max(1,top.length),2)+' سفر';}",
        "if($('top20-avg-uplift'))$('top20-avg-uplift').textContent=(top.reduce((s,r)=>s+Number(r.predicted_incremental_trips),0)/Math.max(1,top.length)>=0?'+':'')+faNum(top.reduce((s,r)=>s+Number(r.predicted_incremental_trips),0)/Math.max(1,top.length),2)+' سفر';if($('model-r2-control'))$('model-r2-control').textContent=faNum(Number(DATA.model.control_test_r2),3);if($('model-r2-treatment'))$('model-r2-treatment').textContent=faNum(Number(DATA.model.treatment_test_r2),3);if($('model-rmse-control'))$('model-rmse-control').textContent=faNum(Number(DATA.model.control_test_rmse_trips),2);if($('model-rmse-treatment'))$('model-rmse-treatment').textContent=faNum(Number(DATA.model.treatment_test_rmse_trips),2); }"
    )
    # Make the managerial commentary use the same current snapshot as the charts.
    html = html.replace(
        '<b>مشوق در نمونه، با سفر بیشتر همراه است</b><p>میانگین گروه مشوق ۴۳٫۶۸ و گروه کنترل ۴۱٫۳۹ سفر بوده؛ اختلاف ۲٫۲۹ سفر در هفته بعد است.</p>',
        '<b>مشوق در نمونه، با سفر بیشتر همراه است</b><p id="overview-insight-lift">خلاصه اثر آزمایش از خروجی فعلی محاسبه می‌شود.</p>'
    )
    html = html.replace(
        '<b>آخرشب کم‌هزینه‌ترین بازه در این داده است</b><p>هزینه تخمینی هر سفر افزایشی آخرشب حدود ۲۴٬۴۷۱ تومان است؛ صبح هم با ۲۵٬۶۵۸ تومان نزدیک است.</p>',
        '<b id="overview-insight-best-title">بازه کم‌هزینه‌تر در داده</b><p id="overview-insight-best-copy">هزینه هر سفر افزایشی از جدول بخش‌ها محاسبه می‌شود.</p>'
    )
    html = html.replace(
        '<b>بعدازظهر را اولویت اول نگذار</b><p>در این شبیه‌سازی، هزینه هر سفر افزایشی بعدازظهر حدود ۷۹٬۵۹۸ تومان است؛ خیلی بالاتر از صبح و آخرشب.</p>',
        '<b id="overview-insight-high-title">بازه پرهزینه‌تر را با احتیاط بررسی کن</b><p id="overview-insight-high-copy">این برداشت با خروجی جاری به‌روز می‌شود.</p>'
    )
    html = html.replace(
        'در این داده، «آخرشب» و «صبح» هزینه کمتری برای هر سفر افزایشی دارند؛ «بعدازظهر» ضعیف‌تر است. پیشنهاد، اجرای یک آزمون محدود و تصادفی روی این بازه‌هاست، نه گسترش فوری کمپین.',
        'برداشت از بخش‌های کم‌هزینه‌تر و پرهزینه‌تر، بر اساس خروجی فعلی است. قبل از تخصیص بودجه، فرضیه‌ها را در یک آزمون محدود و تصادفی اعتبارسنجی کنید.'
    )
    html = html.replace(
        '<p>برداشت از بخش‌های کم‌هزینه‌تر و پرهزینه‌تر، بر اساس خروجی فعلی است. قبل از تخصیص بودجه، فرضیه‌ها را در یک آزمون محدود و تصادفی اعتبارسنجی کنید.</p>',
        '<p id="brief-nextstep-text">برداشت از بخش‌های کم‌هزینه‌تر و پرهزینه‌تر، بر اساس خروجی فعلی است. قبل از تخصیص بودجه، فرضیه‌ها را در یک آزمون محدود و تصادفی اعتبارسنجی کنید.</p>'
    )

    html = html.replace(
        '<div class="segment-decision"><div><span>بهترین فرضیه زمانی</span><b>آخرشب</b><small>۳٫۴۴ سفر افزایشی به‌ازای هر راننده</small></div><div><span>هزینه هر سفر افزایشی</span><b>۲۴٬۴۷۱ تومان</b><small>کمترین مقدار بین بازه‌های زمانی این داده</small></div><div><span>بازه نیازمند بررسی بیشتر</span><b>بعدازظهر</b><small>۷۹٬۵۹۸ تومان برای هر سفر افزایشی</small></div><p>این‌ها نشانه برای طراحی آزمایش بعدی‌اند، نه حکم قطعی برای تمام رانندگان یا ساعت‌ها.</p></div>',
        '<div class="segment-decision"><div><span>کمترین هزینه هر سفر افزایشی</span><b id="segment-best-name">—</b><small id="segment-best-lift">—</small></div><div><span>هزینه بهترین بخش</span><b id="segment-best-cost">—</b><small>برآورد توصیفی در داده مصنوعی</small></div><div><span>بیشترین هزینه هر سفر افزایشی</span><b id="segment-worst-name">—</b><small id="segment-worst-cost">—</small></div><p>این‌ها فرضیه‌هایی برای طراحی آزمایش بعدی‌اند، نه حکم قطعی برای تمام رانندگان یا ساعت‌ها.</p></div>'
    )
    html = html.replace('<b>+۲٫۱۱ سفر</b><small>میانگین خروجی مدل روی داده آزمون</small>', '<b id="mean-predicted-uplift-test">—</b><small>میانگین خروجی مدل روی داده آزمون</small>')
    html = html.replace('<small>MAE کنترل ۶٫۲۵ و آزمایش ۶٫۰۸</small>', '<small id="model-mae-brief">MAE کنترل و آزمایش از holdout محاسبه می‌شود.</small>')
    html = html.replace('<div class="grid model-two">', '<div class="callout" id="uplift-validation-note" style="margin-top:12px;margin-bottom:12px">بررسی holdout درباره اختلاف پیش‌بینی و اثر مشاهده‌شده در گروه‌های رتبه‌ای.</div><div class="grid model-two">')
    html = html.replace('<div class="kpi-value">۸۶٬۷۰۴</div>', '<div class="kpi-value" id="candidate-cost">—</div>')
    html = html.replace('<div class="kpi-value">۵٬۸۹۹</div><div class="kpi-sub">دریافت‌کننده پیشنهاد کمپین</div>', '<div class="kpi-value" id="experiment-treatment-n">—</div><div class="kpi-sub">دریافت‌کننده پیشنهاد کمپین</div>')
    html = html.replace('<div class="kpi-value">۶٬۱۰۱</div><div class="kpi-sub">بدون تخصیص کمپین</div>', '<div class="kpi-value" id="experiment-control-n">—</div><div class="kpi-sub">بدون تخصیص کمپین</div>')
    html = html.replace('<div class="kpi-value" style="font-size:23px">بسیار قوی</div><div class="kpi-sub">p-value کمتر از ۰٫۰۰۱؛ این شاخص کیفیت مالی کمپین را نشان نمی‌دهد.</div>', '<div class="kpi-value" id="experiment-p-strength" style="font-size:23px">—</div><div class="kpi-sub" id="experiment-p-summary">p-value از خروجی فعلی محاسبه می‌شود؛ این شاخص کیفیت مالی کمپین را نشان نمی‌دهد.</div>')

    # One-time JS wiring: all visible statistics and narrative are derived from the embedded snapshot.
    if 'overview-insight-lift' not in html:
        raise RuntimeError("Dashboard commentary was not wired to the current output snapshot.")
    # The previous statement intentionally identifies the first-sync path; add JS only once by checking its new binding.
    if "$('overview-insight-lift').textContent" not in html:
        html = html.replace(
            "if($('brief-ci'))$('brief-ci').textContent='بازه اطمینان ۹۵٪: '+faNum(+a.ci95_low,2)+' تا '+faNum(+a.ci95_high,2)+' سفر';}",
            "if($('brief-ci'))$('brief-ci').textContent='بازه اطمینان ۹۵٪: '+faNum(+a.ci95_low,2)+' تا '+faNum(+a.ci95_high,2)+' سفر';if($('kpi-lift'))$('kpi-lift').textContent=(lift>=0?'+':'')+faNum(lift,2);if($('kpi-cost'))$('kpi-cost').textContent=faNum(Number(DATA.economics.incremental_cost_per_assigned_driver_toman));if($('experiment-treatment-n'))$('experiment-treatment-n').textContent=faNum(DATA.economics.treatment_n);if($('experiment-control-n'))$('experiment-control-n').textContent=faNum(DATA.economics.control_n);const times=DATA.segments.filter(s=>s.segment_by==='daypart'&&Number.isFinite(Number(s.cost_per_incremental_trip_toman))).sort((x,y)=>Number(x.cost_per_incremental_trip_toman)-Number(y.cost_per_incremental_trip_toman));if(times.length){const best=times[0],second=times[Math.min(1,times.length-1)],worst=times[times.length-1],label=x=>dayFa[x.segment]||x.segment;if($('overview-insight-lift'))$('overview-insight-lift').textContent='میانگین گروه مشوق '+faNum(+a.treatment_mean,2)+' و گروه کنترل '+faNum(+a.control_mean,2)+' سفر بوده؛ اختلاف '+faNum(lift,2)+' سفر در هفته بعد است.';if($('overview-insight-best-title'))$('overview-insight-best-title').textContent=label(best)+' کم‌هزینه‌ترین بازه در این داده است';if($('overview-insight-best-copy'))$('overview-insight-best-copy').textContent='هزینه هر سفر افزایشی '+money(best.cost_per_incremental_trip_toman)+' است؛ بازه بعدی، '+label(second)+' با '+money(second.cost_per_incremental_trip_toman)+' است.';if($('overview-insight-high-title'))$('overview-insight-high-title').textContent='بازه پرهزینه‌تر: '+label(worst);if($('overview-insight-high-copy'))$('overview-insight-high-copy').textContent='هزینه هر سفر افزایشی در این بازه '+money(worst.cost_per_incremental_trip_toman)+' است؛ پیش از گسترش، دلیل تفاوت و عدم‌قطعیت آن را بررسی کنید.';if($('brief-nextstep-text'))$('brief-nextstep-text').textContent='در این شبیه‌سازی، کمترین هزینه مشاهده‌شده برای هر سفر افزایشی در بازه '+label(best)+' و سپس '+label(second)+' بوده است. این نتیجه اکتشافی است؛ پیش از تغییر بودجه، در یک آزمون تصادفی آینده‌نگر اعتبارسنجی شود.'; } }"
        )
        html = html.replace(
            "$('plain-control').textContent=faNum(c,2)+' سفر';$('plain-treatment').textContent=faNum(t,2)+' سفر';$('plain-lift').textContent=(d>=0?'+':'')+faNum(d,2)+' سفر';$('plain-relative').textContent='حدود '+faNum(rel,1)+'٪ '+(rel>=0?'بیشتر':'کمتر');",
            "$('plain-control').textContent=faNum(c,2)+' سفر';$('plain-treatment').textContent=faNum(t,2)+' سفر';$('plain-lift').textContent=(d>=0?'+':'')+faNum(d,2)+' سفر';$('plain-relative').textContent='حدود '+faNum(rel,1)+'٪ '+(rel>=0?'بیشتر':'کمتر');const pTrip=Number(trip.p_value_welch);if($('experiment-p-strength'))$('experiment-p-strength').textContent=pTrip<0.001?'بسیار قوی':pTrip<0.05?'معنادار':'نامشخص';if($('experiment-p-summary'))$('experiment-p-summary').textContent='p-value='+pTrip.toExponential(2)+'؛ این شاخص کیفیت مالی کمپین را نشان نمی‌دهد.';"
        )
        html = html.replace(
            "$('segment-chart-title').textContent='افزایش سفر به تفکیک '+(dim==='zone'?'منطقه':'بازه زمانی');",
            "$('segment-chart-title').textContent='افزایش سفر به تفکیک '+(dim==='zone'?'منطقه':'بازه زمانی');const timeEntries=DATA.segments.filter(s=>s.segment_by==='daypart'&&Number.isFinite(Number(s.cost_per_incremental_trip_toman))).sort((x,y)=>Number(x.cost_per_incremental_trip_toman)-Number(y.cost_per_incremental_trip_toman));if(timeEntries.length){const low=timeEntries[0],high=timeEntries[timeEntries.length-1];if($('segment-best-name'))$('segment-best-name').textContent=dayFa[low.segment]||low.segment;if($('segment-best-lift'))$('segment-best-lift').textContent=faNum(low.trip_lift,2)+' سفر افزایشی به‌ازای هر راننده';if($('segment-best-cost'))$('segment-best-cost').textContent=money(low.cost_per_incremental_trip_toman);if($('segment-worst-name'))$('segment-worst-name').textContent=dayFa[high.segment]||high.segment;if($('segment-worst-cost'))$('segment-worst-cost').textContent=money(high.cost_per_incremental_trip_toman);}"
        )
        html = html.replace(
            "if($('top20-avg-uplift'))$('top20-avg-uplift').textContent=(top.reduce((s,r)=>s+Number(r.predicted_incremental_trips),0)/Math.max(1,top.length)>=0?'+':'')+faNum(top.reduce((s,r)=>s+Number(r.predicted_incremental_trips),0)/Math.max(1,top.length),2)+' سفر';",
            "if($('top20-avg-uplift'))$('top20-avg-uplift').textContent=(top.reduce((s,r)=>s+Number(r.predicted_incremental_trips),0)/Math.max(1,top.length)>=0?'+':'')+faNum(top.reduce((s,r)=>s+Number(r.predicted_incremental_trips),0)/Math.max(1,top.length),2)+' سفر';if($('mean-predicted-uplift-test'))$('mean-predicted-uplift-test').textContent=(Number(DATA.model.mean_predicted_uplift_test)>=0?'+':'')+faNum(Number(DATA.model.mean_predicted_uplift_test),2)+' سفر';if($('model-mae-brief'))$('model-mae-brief').textContent='MAE کنترل '+faNum(Number(DATA.model.control_test_mae_trips),2)+' و آزمایش '+faNum(Number(DATA.model.treatment_test_mae_trips),2);if($('candidate-cost'))$('candidate-cost').textContent=faNum(Number(DATA.economics.incremental_cost_per_assigned_driver_toman));"
        )
        html = html.replace(
            "const top=recs.filter(r=>+r.recommended_for_top_20pct===1);if($('top20-avg-uplift'))",
            "const top=recs.filter(r=>+r.recommended_for_top_20pct===1);if($('uplift-validation-note'))$('uplift-validation-note').textContent='اعتبارسنجی holdout: افزایش مشاهده‌شده در ۲۰٪ بالای امتیاز '+faNum(Number(DATA.model.top20_observed_trip_lift),2)+' سفر (فاصله اطمینان ۹۵٪: '+faNum(Number(DATA.model.top20_observed_trip_lift_ci95_low),2)+' تا '+faNum(Number(DATA.model.top20_observed_trip_lift_ci95_high),2)+')؛ میانگین uplift پیش‌بینی‌شده در همین گروه '+faNum(Number(DATA.model.top20_predicted_uplift),2)+' سفر بود. این اختلاف و پهنای بازه، ضرورت آزمون آینده‌نگر را نشان می‌دهد.';if($('top20-avg-uplift'))"
        )
    # Avoid malformed '+-x' labels if a model predicts a negative score.
    html = html.replace("<b style=\"color:#087e5d\">+${enNum(r.predicted_incremental_trips,2)}</b>", "<b style=\"color:${+r.predicted_incremental_trips>=0?'#087e5d':'#b45309'}\">${+r.predicted_incremental_trips>=0?'+':''}${enNum(r.predicted_incremental_trips,2)}</b>")
    dashboard_path.write_text(html, encoding="utf-8")
    return dashboard_path


def main() -> None:
    p = sync_dashboard()
    print(f"Dashboard synchronized from the latest pipeline outputs: {p}")


if __name__ == "__main__":
    main()
