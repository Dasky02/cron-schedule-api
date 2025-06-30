from fastapi import FastAPI, Query, HTTPException
from croniter import croniter
from datetime import datetime
from dateutil import tz

app = FastAPI(
    title="Cron Schedule API",
    description="Vypočítá nejbližší budoucí (nebo minulé) termíny podle CRON výrazu.",
    version="1.0.0",
)

def _parse_timezone(tz_name: str):
    tzinfo = tz.gettz(tz_name)
    if tzinfo is None:
        raise HTTPException(status_code=400, detail=f"Neznámé časové pásmo: {tz_name}")
    return tzinfo


@app.get("/next")
def next_runs(
    expr: str = Query(..., description="CRON výraz – např. */15 * * * *"),
    count: int = Query(5, gt=0, le=100, description="Počet termínů (1-100)"),
    tzname: str = Query("UTC", description="Časové pásmo, default UTC"),
):
    """
    Vrátí pole ISO 8601 časů příštích spuštění.
    """
    try:
        tzinfo = _parse_timezone(tzname)
        start = datetime.now(tz=tzinfo)
        itr = croniter(expr, start)
        times = [itr.get_next(datetime).isoformat() for _ in range(count)]
        return {"cron": expr, "timezone": tzname, "next": times}
    except (ValueError, KeyError) as e:
        raise HTTPException(status_code=400, detail=f"Neplatný CRON: {e}")


@app.get("/previous")
def previous_runs(
    expr: str = Query(..., description="CRON výraz"),
    count: int = Query(5, gt=0, le=100),
    tzname: str = Query("UTC"),
):
    """
    Vrátí pole ISO 8601 časů minulých spuštění.
    """
    try:
        tzinfo = _parse_timezone(tzname)
        start = datetime.now(tz=tzinfo)
        itr = croniter(expr, start)
        times = [itr.get_prev(datetime).isoformat() for _ in range(count)]
        return {"cron": expr, "timezone": tzname, "previous": times}
    except (ValueError, KeyError) as e:
        raise HTTPException(status_code=400, detail=f"Neplatný CRON: {e}")


@app.get("/validate")
def validate(expr: str = Query(..., description="CRON výraz k validaci")):
    """
    Jen zkontroluje syntaxi CRON výrazu.
    """
    try:
        croniter(expr)
        return {"valid": True}
    except (ValueError, KeyError):
        return {"valid": False}

@app.get("/", summary="Health-check")
def root():
    """Jednoduchá sonda pro CI / Render."""
    return {"status": "ok"}
