"""Cycle prediction engine.

Pure-python logic shared by all endpoints:
- averages from history
- next period prediction
- fertile window / ovulation
- current cycle day & phase
- calendar-day classification
"""
import datetime as dt
from statistics import mean


def parse_date(s):
    if s is None:
        return None
    if isinstance(s, dt.datetime):
        return s.date()
    if isinstance(s, dt.date):
        return s
    return dt.date.fromisoformat(str(s)[:10])


def completed_cycles(periods, avg_fallback=28):
    """Return list of cycle lengths (gap between consecutive period starts)."""
    starts = sorted({parse_date(p["start_date"]) for p in periods})
    lengths = []
    for a, b in zip(starts, starts[1:]):
        diff = (b - a).days
        if 15 <= diff <= 60:  # physiologically plausible
            lengths.append(diff)
    return lengths


def compute_stats(periods, settings):
    cycles = completed_cycles(periods)
    period_lens = [
        (parse_date(p["end_date"]) - parse_date(p["start_date"])).days + 1
        for p in periods
        if p.get("end_date")
    ]
    # settings may come back as REAL/float from SQLite/Oracle — always coerce to int
    fb_cycle = int(round(float((settings or {}).get("avg_cycle_length") or 28)))
    fb_period = int(round(float((settings or {}).get("avg_period_length") or 5)))
    avg_cycle = int(round(mean(cycles))) if cycles else fb_cycle
    avg_period = int(round(mean(period_lens))) if period_lens else fb_period
    return {
        "avg_cycle_length": max(15, min(60, int(avg_cycle))),
        "avg_period_length": max(1, min(14, int(avg_period))),
        "cycles_tracked": len(cycles),
        "periods_logged": len(periods),
        "cycle_variability": (max(cycles) - min(cycles)) if len(cycles) >= 2 else 0,
    }


def latest_period_start(periods):
    starts = [parse_date(p["start_date"]) for p in periods]
    return max(starts) if starts else None


def predict_next_period(last_start, avg_cycle):
    return last_start + dt.timedelta(days=avg_cycle) if last_start else None


def fertile_window(next_start, luteal=14, span=5):
    """Ovulation = next_start - luteal. Fertile window = ovulation-span .. ovulation+1."""
    if not next_start:
        return None, None, None
    ovu = next_start - dt.timedelta(days=luteal)
    return ovu - dt.timedelta(days=span), ovu + dt.timedelta(days=1), ovu


def cycle_phase(day_in_cycle, avg_period, ovulation_day):
    if day_in_cycle <= avg_period:
        return "menstrual"
    if day_in_cycle < ovulation_day - 2:
        return "follicular"
    if ovulation_day - 2 <= day_in_cycle <= ovulation_day + 1:
        return "ovulation"
    return "luteal"


PHASE_INFO = {
    "menstrual": {"title": "Menstrual phase", "emoji": "🩸"},
    "follicular": {"title": "Follicular phase", "emoji": "🌱"},
    "ovulation": {"title": "Ovulation window", "emoji": "✨"},
    "luteal": {"title": "Luteal phase", "emoji": "🌙"},
}


def insights_for_phase(phase, day_in_cycle):
    tips = {
        "menstrual": [
            "Iron-rich foods (spinach, lentils, red meat) help replenish losses.",
            "Gentle movement like walking or yoga can ease cramps.",
            "Heat pads on the lower abdomen relax uterine muscles.",
        ],
        "follicular": [
            "Estrogen is rising — a great time for strength training and new projects.",
            "Your skin often looks its best in this window.",
            "Social energy tends to be higher — plan gatherings now.",
        ],
        "ovulation": [
            "You're at peak fertility — most likely to conceive now.",
            "Libido and energy commonly peak around ovulation.",
            "Some notice mild one-sided pelvic twinges (mittelschmerz).",
        ],
        "luteal": [
            "Progesterone rises — you may feel more tired or introspective.",
            "Complex carbs and magnesium can soften PMS symptoms.",
            "Prioritize sleep; body temperature runs slightly higher.",
        ],
    }
    return tips.get(phase, [])


def build_overview(periods, settings):
    stats = compute_stats(periods, settings)
    today = dt.date.today()
    last = latest_period_start(periods)
    luteal = int(round(float((settings or {}).get("luteal_phase_length") or 14)))

    out = {"stats": stats, "today": today.isoformat()}
    if not last:
        out.update({"has_data": False, "message": "Log your first period to unlock predictions."})
        return out

    next_start = predict_next_period(last, stats["avg_cycle_length"])
    # If the predicted date already passed without a new log, project forward.
    while next_start and next_start < today and stats["cycle_variability"] < 20:
        next_start = next_start + dt.timedelta(days=stats["avg_cycle_length"])

    fert_start, fert_end, ovu_day = fertile_window(next_start, luteal)

    day_in_cycle = (today - last).days + 1
    if day_in_cycle > stats["avg_cycle_length"]:
        # overdue — keep counting but flag it
        pass
    phase = cycle_phase(day_in_cycle, stats["avg_period_length"], ovu_day if False else luteal and (next_start - dt.timedelta(days=luteal)).toordinal() - last.toordinal() + 1)

    days_until = (next_start - today).days
    pregnant_hint = days_until < -3 and stats["cycles_tracked"] >= 3

    out.update({
        "has_data": True,
        "last_period_start": last.isoformat(),
        "predicted_next_start": next_start.isoformat() if next_start else None,
        "days_until_next_period": days_until,
        "day_of_cycle": day_in_cycle,
        "phase": phase,
        "phase_info": PHASE_INFO.get(phase, {}),
        "fertile_window_start": fert_start.isoformat() if fert_start else None,
        "fertile_window_end": fert_end.isoformat() if fert_end else None,
        "ovulation_date": (next_start - dt.timedelta(days=luteal)).isoformat(),
        "pregnancy_chance_note": (
            "Period is noticeably late — consider taking a pregnancy test."
            if pregnant_hint else None
        ),
        "insights": insights_for_phase(phase, day_in_cycle),
    })
    return out


def classify_calendar_days(days, periods, settings):
    """Given a list of ISO dates, mark each as period/predicted_period/fertile/ovulation/plain."""
    stats = compute_stats(periods, settings)
    luteal = int(round(float((settings or {}).get("luteal_phase_length") or 14)))
    logged = {}
    for p in periods:
        s = parse_date(p["start_date"])
        e = parse_date(p.get("end_date")) or s + dt.timedelta(days=stats["avg_period_length"] - 1)
        d = s
        while d <= e:
            logged[d] = "period"
            d += dt.timedelta(days=1)

    # projected future period starts (up to ~6 cycles ahead of last log)
    projections = []
    last = latest_period_start(periods)
    if last:
        nxt = last + dt.timedelta(days=stats["avg_cycle_length"])
        horizon = max(parse_date(d) for d in days) + dt.timedelta(days=45)
        while nxt <= horizon:
            projections.append(nxt)
            nxt += dt.timedelta(days=stats["avg_cycle_length"])

    proj_days = set()
    for start in projections:
        d = start
        for _ in range(stats["avg_period_length"]):
            proj_days.add(d)
            d += dt.timedelta(days=1)

    # fertile windows per projection/current
    fert = {}
    anchors = []
    today = dt.date.today()
    if last:
        anchors.append(last + dt.timedelta(days=stats["avg_cycle_length"]))
    anchors.extend(projections)
    for start in anchors:
        ovu = start - dt.timedelta(days=luteal)
        fs = ovu - dt.timedelta(days=4)
        fe = ovu + dt.timedelta(days=1)
        d = fs
        while d <= fe:
            fert.setdefault(d, "ovulation" if d == ovu else "fertile")
            d += dt.timedelta(days=1)

    result = {}
    for iso in days:
        d = parse_date(iso)
        tag = "plain"
        if d in logged:
            tag = "period"
        elif d in proj_days:
            tag = "predicted_period"
        elif d in fert:
            tag = fert[d]
        result[iso] = tag
    return result