# main.py  – Cron Schedule API v2.0
from datetime import datetime
import re

from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from croniter import croniter
from cron_descriptor import get_description
from cron_converter import Cron
from dateutil import tz

# -----------------------------------------------------------
app = FastAPI(
    title="Cron Schedule API",
    description=(
        "Validate CRON expressions, generate next/previous run-times, "
        "convert between time-zones a nově i Natural-language ↔ CRON."
    ),
    version="2.0.0",
)

# CORS – pokud volá front-end přímo
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# -----------------------------------------------------------
# Pomocné funkce
# -----------------------------------------------------------
def _parse_timezone(tz_name: str):
    tzinfo = tz.gettz(tz_name)
    if tzinfo is None:
        raise HTTPException(status_code=400, detail=f"Neznámé časové pásmo: {tz_name}")
    return tzinfo


def _human_to_cron(text: str) -> str:
    """
    Natural-language → CRON.
    Nejprve zkusíme knihovnu cron_converter;
    pokud selže a najdeme v textu formát HH:MM,
    převedeme si ho ručně.
    """
    try:
        return Cron(text).expression            # 1️⃣ přímý pokus
    except Exception:
        # 2️⃣ zkusíme zachytit HH:MM
        m = re.search(r'(\d{1,2}):(\d{2})', text)
        if not m:
            raise HTTPException(status_code=400,
                                detail="Invalid cron string format")

        hour, minute = map(int, m.groups())

        # a) pokud minuta ≠ 0 → rovnou vrátíme pětiprvkový CRON
        if minute != 0:
            return f"{minute} {hour} * * *"

        # b) minuta = 0 → přepíšeme na 12h+am/pm a zkusíme znovu
        ampm = "pm" if hour >= 12 else "am"
        h12 = hour if 1 <= hour <= 12 else hour - 12
        patched = re.sub(r'\d{1,2}:\d{2}', f"{h12}{ampm}", text)

        # druhý pokus přes Cron()
        try:
            return Cron(patched).expression
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))


def _cron_to_human(expr: str) -> str:
    """CRON → popis (cron-descriptor, EN)."""
    return get_description(expr)


def _format(dt: datetime, pattern: str) -> str:
    """Vlastní formát data/hodiny."""
    return dt.strftime(pattern)


# -----------------------------------------------------------
# Health-check root
# -----------------------------------------------------------
@app.get("/", summary="Health-check")
def root():
    return {"status": "ok"}


# -----------------------------------------------------------
# 1  VALIDATE / NEXT / PREVIOUS (původní + explain)
# -----------------------------------------------------------
@app.get("/validate", summary="Validace CRON")
def validate(expr: str):
    try:
        croniter(expr)
        return {"valid": True}
    except Exception:
        return {"valid": False}


@app.get("/validate_explain", summary="Validace + vysvětlení")
def validate_explain(expr: str):
    try:
        croniter(expr)
        return {"valid": True, "description": _cron_to_human(expr)}
    except Exception as e:
        return {"valid": False, "error": str(e)}


@app.get("/next", summary="Další termíny (ISO 8601)")
def next_runs(
    expr: str = Query(..., description="CRON – např. */15 * * * *"),
    count: int = Query(5, gt=0, le=100),
    tzname: str = Query("UTC"),
):
    tzinfo = _parse_timezone(tzname)
    itr = croniter(expr, datetime.now(tz=tzinfo))
    return {
        "cron": expr,
        "timezone": tzname,
        "next": [itr.get_next(datetime).isoformat() for _ in range(count)],
    }


@app.get("/previous", summary="Minulé termíny (ISO 8601)")
def previous_runs(
    expr: str,
    count: int = Query(5, gt=0, le=100),
    tzname: str = Query("UTC"),
):
    tzinfo = _parse_timezone(tzname)
    itr = croniter(expr, datetime.now(tz=tzinfo))
    return {
        "cron": expr,
        "timezone": tzname,
        "previous": [itr.get_prev(datetime).isoformat() for _ in range(count)],
    }


# -----------------------------------------------------------
# 2  Natural-language ↔ CRON
# -----------------------------------------------------------
@app.get("/human2cron", summary="Natural language → CRON")
def human2cron(text: str = Query(..., description="např. 'every monday at 5pm'")):
    try:
        return {"text": text, "cron": _human_to_cron(text)}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/cron2human", summary="CRON → lidský popis (EN)")
def cron2human(expr: str):
    try:
        return {"cron": expr, "description": _cron_to_human(expr)}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# -----------------------------------------------------------
# 3  Převod mezi time-zonami
# -----------------------------------------------------------
@app.get("/convert_tz", summary="Převod CRONu mezi time-zonami")
def convert_tz(
    expr: str,
    from_tz: str = Query("UTC"),
    to_tz: str = Query("UTC"),
):
    try:
        from_zone = _parse_timezone(from_tz)
        to_zone = _parse_timezone(to_tz)

        start = datetime.now(tz=from_zone)
        next_dt = croniter(expr, start).get_next(datetime).astimezone(to_zone)
        # Složíme nový výraz (pouze minuty/hodiny se mění)
        converted = f"{next_dt.minute} {next_dt.hour} " + " ".join(expr.split()[2:])
        return {
            "original": expr,
            "from": from_tz,
            "to": to_tz,
            "converted": converted,
            "example_next_run": next_dt.isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# -----------------------------------------------------------
# 4  Formátované výstupy
# -----------------------------------------------------------
@app.get("/next_fmt", summary="Next N – vlastní formát")
def next_fmt(
    expr: str,
    count: int = Query(5, gt=0, le=100),
    tzname: str = Query("UTC"),
    fmt: str = Query("%Y-%m-%d %H:%M"),
):
    tzinfo = _parse_timezone(tzname)
    itr = croniter(expr, datetime.now(tz=tzinfo))
    return [_format(itr.get_next(datetime), fmt) for _ in range(count)]


@app.get("/prev_fmt", summary="Previous N – vlastní formát")
def prev_fmt(
    expr: str,
    count: int = Query(5, gt=0, le=100),
    tzname: str = Query("UTC"),
    fmt: str = Query("%Y-%m-%d %H:%M"),
):
    tzinfo = _parse_timezone(tzname)
    itr = croniter(expr, datetime.now(tz=tzinfo))
    return [_format(itr.get_prev(datetime), fmt) for _ in range(count)]
