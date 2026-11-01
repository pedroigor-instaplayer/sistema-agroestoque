"""Utilitários de data/hora (UTC no banco, fuso local na exibição) e dinheiro."""
from datetime import date, datetime, time, timedelta, timezone

try:
    from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
except ImportError:  # pragma: no cover
    ZoneInfo = None

FMT_DB = "%Y-%m-%d %H:%M:%S"
_TZ = timezone(timedelta(hours=-3))


def configurar_fuso(nome):
    """Define o fuso local. Se o pacote tzdata não existir, usa UTC-3 fixo."""
    global _TZ
    try:
        _TZ = ZoneInfo(nome)
    except Exception:
        _TZ = timezone(timedelta(hours=-3))


def agora_utc():
    return datetime.now(timezone.utc)


def para_db(dt):
    return dt.astimezone(timezone.utc).strftime(FMT_DB)


def de_db(texto):
    return datetime.strptime(texto, FMT_DB).replace(tzinfo=timezone.utc)


def iso_local(texto):
    return None if not texto else de_db(texto).astimezone(_TZ).isoformat()


def data_local(texto):
    return de_db(texto).astimezone(_TZ).date()


def hoje_local(agora=None):
    return (agora or agora_utc()).astimezone(_TZ).date()


def inicio_dia_db(d: date):
    """Meia-noite local de `d`, expressa em UTC (para filtros no banco)."""
    return para_db(datetime.combine(d, time.min, tzinfo=_TZ))


def local_para_db(d: date, hora=12, minuto=0):
    return para_db(datetime.combine(d, time(hora, minuto), tzinfo=_TZ))


def centavos_str(c):
    if c is None:
        return None
    return f"{c // 100}.{c % 100:02d}"
