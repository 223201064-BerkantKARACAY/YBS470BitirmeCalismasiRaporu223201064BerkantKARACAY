# ═══════════════════════════════════════════════════════════════════
#  BAĞIMLILIKLAR
# ═══════════════════════════════════════════════════════════════════
import sys, os, re
from abc import ABC, abstractmethod

_eksik = []
try:    import borsapy as bp
except: _eksik.append("borsapy")
try:
    from rich.console import Console
    from rich.table   import Table
    from rich.panel   import Panel
    from rich         import box
except: _eksik.append("rich")
try:
    import pandas as pd
    import numpy  as np
except: _eksik.append("pandas")
try:
    import matplotlib
    import matplotlib.pyplot  as plt
    import matplotlib.patches as mpatches
    import matplotlib.ticker  as mticker
    matplotlib.rcParams["toolbar"] = "None"
except: _eksik.append("matplotlib")
try:
    import mplcursors; _CURSORS = True
except: _CURSORS = False

if _eksik:
    print(f"\nEksik: {', '.join(_eksik)}")
    print(f"Kurmak için: pip install {' '.join(_eksik)}\n")
    sys.exit(1)

console = Console()

# ═══════════════════════════════════════════════════════════════════
#  TEMA VE RENKLER
# ═══════════════════════════════════════════════════════════════════
plt.style.use("dark_background")
_BG, _BG2, _GRID, _TICK = "#0d1117", "#161b22", "#21262d", "#8b949e"
plt.rcParams.update({
    "figure.facecolor": _BG,  "axes.facecolor": _BG2,
    "axes.edgecolor": _GRID,  "text.color": "#c9d1d9",
    "xtick.color": _TICK,     "ytick.color": _TICK,
    "grid.color": _GRID,      "grid.linestyle": "--",
    "grid.alpha": 0.4,        "font.family": "monospace",
})

C = {
    "up": "#26a641",    "down": "#f85149",    "line": "#58a6ff",
    "sma20": "#ffa657", "sma50": "#3fb950",   "ema9": "#d2a8ff",
    "ema20": "#79c0ff", "bb": "#8b949e",       "bb_fill": "#58a6ff",
    "vwap": "#e3b341",  "rsi": "#d2a8ff",
    "rsi_up": "#f85149","rsi_dn": "#26a641",
    "macd": "#58a6ff",  "sig": "#ffa657",
    "stk_k": "#ffa657", "stk_d": "#d2a8ff",
    "atr": "#ffa657",   "obv": "#79c0ff",
    "enf": "#3fb950",
    "tenkan": "#ff6b6b","kijun": "#4ecdc4",
    "senkou_a": "#3fb950","senkou_b": "#f85149","chikou": "#ffa657",
    "fib_r": "#e3b341", "fib_e": "#79c0ff",
    "destek": "#3fb950","direnc": "#f85149",
    "buy": "#26a641",   "sell": "#f85149",
    "cross": "#ffffff",
}
PALETTE = ["#58a6ff","#3fb950","#ffa657","#f85149",
           "#d2a8ff","#79c0ff","#56d364","#e3b341","#ff7b72","#a5d6ff"]


# ═══════════════════════════════════════════════════════════════════
#  YARDIMCI FONKSİYONLAR
# ═══════════════════════════════════════════════════════════════════

def temizle(): os.system("cls" if os.name == "nt" else "clear")
def geri_don(): input("\n  [Enter] ile devam edin...")

def sayi_kisalt(v) -> str:
    try:
        f = float(v)
        if f != f: return "—"
        s, a = ("" if f >= 0 else "-"), abs(f)
        if a >= 1e12: return f"{s}{a/1e12:.2f}T"
        if a >= 1e9:  return f"{s}{a/1e9:.2f}B"
        if a >= 1e6:  return f"{s}{a/1e6:.2f}M"
        if a >= 1e3:  return f"{s}{a:,.0f}"
        return f"{s}{a:,.4f}"
    except: return str(v) if v is not None else "—"

def safe_float(v) -> float | None:
    if v is None: return None
    if isinstance(v, dict):
        for k in ("last","close","sell","buy","value","price","current"):
            try: return float(v[k])
            except: pass
        try: return float(next(iter(v.values())))
        except: return None
    try:
        f = float(v)
        return None if f != f else f
    except: return None

def df_kontrol(df) -> bool:
    return df is not None and isinstance(df, pd.DataFrame) and not df.empty

def dict_kontrol(d) -> bool:
    return bool(d) and isinstance(d, dict)

def kisalt_sutunlar(df) -> list:
    return [str(c) for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]

def df_to_rich(df, baslik="", max_satir=40, renk="cyan",
               kisalt: list = None) -> Table:
    t = Table(title=baslik, box=box.ROUNDED, border_style=renk,
              show_lines=True, header_style=f"bold {renk}")
    df2 = df.reset_index()
    for s in df2.columns: t.add_column(str(s), overflow="fold")
    for _, row in df2.head(max_satir).iterrows():
        vals = []
        for col, v in zip(df2.columns, row):
            if v is None or (isinstance(v, float) and v != v): vals.append("—")
            elif kisalt and str(col) in kisalt: vals.append(sayi_kisalt(v))
            else:
                s2 = str(v)
                vals.append(s2[:90] if len(s2) > 90 else s2)
        t.add_row(*vals)
    if len(df2) > max_satir:
        t.caption = f"(Toplam {len(df2)}, ilk {max_satir} gösteriliyor)"
    return t

def dict_to_rich(d: dict, baslik="", renk="green") -> Table:
    t = Table(title=baslik, box=box.ROUNDED, border_style=renk,
              show_lines=True, header_style=f"bold {renk}")
    t.add_column("Alan", style="bold", min_width=28)
    t.add_column("Değer")
    for k, v in d.items():
        gos = sayi_kisalt(v) if isinstance(v, (int, float)) else (str(v)[:120] if v else "—")
        t.add_row(str(k), gos)
    return t

def _panel(metin, baslik="", renk="cyan"):
    console.print(Panel(metin, title=f"[bold]{baslik}[/bold]",
                        border_style=renk, expand=False))

def secim_al(secenekler, mesaj="Seciminiz") -> str:
    while True:
        g = input(f"  {mesaj}: ").strip()
        if g in secenekler: return g
        console.print(f"  [red]Geçersiz. Seçenekler: {', '.join(secenekler)}[/red]")

def period_sec() -> str:
    op = {"1":"1g","2":"5g","3":"1ay","4":"3ay","5":"6ay","6":"1y","7":"2y","8":"max"}
    ad = {"1":"1G","2":"5G","3":"1Ay","4":"3Ay","5":"6Ay","6":"1Yıl","7":"2Yıl","8":"Max"}
    console.print("\n  " + "  ".join(f"[cyan]{k}[/cyan]/{ad[k]}" for k in op))
    return op[secim_al(list(op), "Dönem (1-8)")]

def interval_sec() -> str:
    op = {"1":"1d","2":"1h","3":"30m","4":"15m","5":"5m","6":"1m"}
    ad = {"1":"Günlük","2":"Saatlik","3":"30dk","4":"15dk","5":"5dk","6":"1dk"}
    console.print("\n  " + "  ".join(f"[cyan]{k}[/cyan]/{ad[k]}" for k in op))
    return op[secim_al(list(op), "Interval (1-6)")]

def tum_sirketler() -> pd.DataFrame:   return bp.companies()
def sirket_ara(q) -> pd.DataFrame:     return bp.search_companies(q)
def fon_ara(q) -> pd.DataFrame:        return bp.search_funds(q)
def kripto_ciftleri() -> list:          return bp.crypto_pairs()
def tum_endeksler() -> list:            return bp.indices()
def coklu_hisse(semboller, period="1ay") -> pd.DataFrame:
    return bp.download(semboller, period=period, group_by="column")


# ═══════════════════════════════════════════════════════════════════
#  SOYUT TABAN SINIF
# ═══════════════════════════════════════════════════════════════════

class FinansalEnstruman(ABC):
    """
    Tüm finansal enstrüman sınıflarının miras aldığı soyut taban sınıf.

    Zorunlu metodlar (alt sınıf implement etmek zorunda):
        guncel_fiyat() → float
        gecmis_veri(period) → pd.DataFrame

    Hazır metodlar:
        getiri_hesapla(period) → float | None
        ozet_yazdir()
    """
    def __init__(self, sembol: str): self.sembol = sembol

    @abstractmethod
    def guncel_fiyat(self) -> float: ...

    @abstractmethod
    def gecmis_veri(self, period: str = "1ay") -> pd.DataFrame: ...

    def getiri_hesapla(self, period="1ay") -> float | None:
        try:
            df = self.gecmis_veri(period)
            if not df_kontrol(df) or "Close" not in df.columns: return None
            b, s = df["Close"].iloc[0], df["Close"].iloc[-1]
            return round((s - b) / b * 100, 2) if b else None
        except: return None

    def ozet_yazdir(self):
        fiyat  = self.guncel_fiyat()
        getiri = self.getiri_hesapla("1ay")
        g_str  = f"  [{('green' if getiri >= 0 else 'red')}]"
        g_str += f"{'▲' if getiri >= 0 else '▼'} {abs(getiri):.2f}%[/]" if getiri else ""
        console.print(
            f"  [bold]{self.__class__.__name__:12}[/bold] "
            f"[cyan]{self.sembol:<14}[/cyan] "
            f"[yellow]{sayi_kisalt(fiyat):>14}[/yellow]{g_str}")


# ═══════════════════════════════════════════════════════════════════
#  HİSSE  (bp.Ticker)
# ═══════════════════════════════════════════════════════════════════

class Hisse(FinansalEnstruman):
    """
    BIST hisse senetleri.
    Kaynak: İş Yatırım + TradingView (~15 dk gecikme) + KAP + hedeffiyat.com.tr

    fast_info: last_price, open, day_high, day_low, previous_close,
               volume, amount, market_cap, shares, pe_ratio, pb_ratio,
               year_high, year_low, fifty_day_average, two_hundred_day_average,
               free_float, foreign_ratio, currency, exchange, timezone
    """
    def __init__(self, sembol: str):
        super().__init__(sembol.upper())
        self._t = bp.Ticker(self.sembol)

    def guncel_fiyat(self) -> float:
        return safe_float(self._t.fast_info["last_price"])

    def gecmis_veri(self, period="1ay", interval="1d") -> pd.DataFrame:
        return self._t.history(period=period, interval=interval)

    def hizli_bilgi(self) -> dict:
        fi = self._t.fast_info
        def _f(k):
            try: return fi[k]
            except: return None
        return {
            "Son Fiyat (TRY)"   : _f("last_price"),
            "Açılış"            : _f("open"),
            "Gün Yüksek"        : _f("day_high"),
            "Gün Düşük"         : _f("day_low"),
            "Önceki Kapanış"    : _f("previous_close"),
            "Hacim (Adet)"      : _f("volume"),
            "İşlem Hacmi (TRY)" : _f("amount"),
            "Piyasa Değeri"     : _f("market_cap"),
            "Dolaşımdaki Pay"   : _f("shares"),
            "F/K Oranı"         : _f("pe_ratio"),
            "PD/DD"             : _f("pb_ratio"),
            "52H Yüksek"        : _f("year_high"),
            "52H Düşük"         : _f("year_low"),
            "50G Ortalama"      : _f("fifty_day_average"),
            "200G Ortalama"     : _f("two_hundred_day_average"),
            "Halka Açıklık %"   : _f("free_float"),
            "Yabancı Oranı %"   : _f("foreign_ratio"),
            "Para Birimi"       : _f("currency"),
        }

    def detayli_bilgi(self) -> dict:
        try:
            inf = self._t.info
            if isinstance(inf, dict) and len(inf) > 3: return inf
        except: pass
        # Fallback: fast_info'dan temel alanlar
        return self.hizli_bilgi()

    def tarih_araliginda(self, bas: str, bit: str) -> pd.DataFrame:
        try:
            df = self._t.history(start=bas, end=bit, interval="1d")
            if not df_kontrol(df): return pd.DataFrame()
            # Tarih filtresi (timezone uyumu)
            idx = pd.to_datetime(df.index, errors="coerce")
            b_ts = pd.Timestamp(bas)
            e_ts = pd.Timestamp(bit)
            if idx.tz is not None:
                b_ts = b_ts.tz_localize(idx.tz)
                e_ts = e_ts.tz_localize(idx.tz)
            return df[(idx >= b_ts) & (idx <= e_ts)]
        except: return pd.DataFrame()

    def gelir_tablosu(self, ceyreklik=False) -> pd.DataFrame:
        return self._t.quarterly_income_stmt if ceyreklik else self._t.income_stmt
    def bilanco(self, ceyreklik=False) -> pd.DataFrame:
        return self._t.quarterly_balance_sheet if ceyreklik else self._t.balance_sheet
    def nakit_akis(self, ceyreklik=False) -> pd.DataFrame:
        return self._t.quarterly_cashflow if ceyreklik else self._t.cashflow
    def ttm_gelir(self) -> pd.DataFrame:  return self._t.ttm_income_stmt
    def temettu(self) -> pd.DataFrame:    return self._t.dividends
    def sermaye_artirimi(self) -> pd.DataFrame: return self._t.splits
    def kurumsal_islemler(self) -> pd.DataFrame: return self._t.actions
    def ana_ortaklar(self) -> pd.DataFrame: return self._t.major_holders
    def etf_sahipleri(self) -> pd.DataFrame: return self._t.etf_holders
    def analist_hedef(self) -> dict:       return self._t.analyst_price_targets

    def analist_tavsiye(self) -> pd.DataFrame:
        r = self._t.recommendations
        if isinstance(r, pd.DataFrame): return r
        if isinstance(r, dict): return pd.DataFrame(list(r.items()), columns=["Alan","Değer"])
        return pd.DataFrame()

    def tavsiye_ozet(self) -> pd.DataFrame:
        r = self._t.recommendations_summary
        if isinstance(r, pd.DataFrame): return r
        if isinstance(r, dict): return pd.DataFrame(list(r.items()), columns=["Alan","Değer"])
        return pd.DataFrame()

    def kap_haberleri(self) -> list:
        r = self._t.news
        if r is None: return []
        if isinstance(r, pd.DataFrame): return [] if r.empty else r.to_dict("records")
        if isinstance(r, list): return r
        if isinstance(r, dict):
            rows = []
            for k, v in r.items():
                if isinstance(v, dict): rows.append({**v, "_key": k})
                else: rows.append({"Tarih": k, "Başlık": str(v)})
            return rows
        return []

    def takvim(self) -> dict: return self._t.calendar
    def kazanc_tarihleri(self) -> pd.DataFrame: return self._t.earnings_dates
    def isin(self) -> str: return self._t.isin


# ═══════════════════════════════════════════════════════════════════
#  DÖVİZ  (bp.FX)
# ═══════════════════════════════════════════════════════════════════

class Doviz(FinansalEnstruman):
    """
    Döviz kurları. Kaynak: doviz.com (65+ para birimi)
    Desteklenen kurumlar (kurum_gecmisi): akbank, garanti-bbva, isbankasi,
    ziraatbankasi, vakifbank, halkbankasi, denizbank, qnb-finansbank, teb...
    """
    def __init__(self, sembol: str):
        super().__init__(sembol.upper())
        self._fx = bp.FX(self.sembol)

    def guncel_fiyat(self) -> float:
        return safe_float(self._fx.current)

    def gecmis_veri(self, period="1ay") -> pd.DataFrame:
        return self._fx.history(period=period)

    def kurum_gecmisi(self, kurum: str, period="1ay") -> pd.DataFrame:
        return self._fx.institution_history(kurum, period=period)


# ═══════════════════════════════════════════════════════════════════
#  EMTİA  (bp.FX — Doviz'den türer)
# ═══════════════════════════════════════════════════════════════════

class Emtia(Doviz):
    """
    Altın, gümüş, platin, paladyum.
    Doviz'den kalıtım alır; ikisi de bp.FX kullanır.

    KRİTİK: Doviz.__init__ sembol.upper() yapar → "gram-altin" → "GRAM-ALTIN"
    Bu borsapy'yi çökertir. Emtia.__init__ bu yüzden FinansalEnstruman.__init__'i
    direkt çağırır ve bp.FX'e sembolü olduğu gibi verir.

    KURUM_DESTEKLI: sadece bu semboller institution_rates destekler.
    """
    TURLER = {
        "1" : ("Gram Altın",        "gram-altin"),
        "2" : ("Çeyrek Altın",      "ceyrek-altin"),
        "3" : ("Yarım Altın",       "yarim-altin"),
        "4" : ("Tam Altın",         "tam-altin"),
        "5" : ("Gram Gümüş (TRY)", "gram-gumus"),
        "6" : ("Ons Altın (TRY)",  "ons-altin"),
        "7" : ("Gram Platin (TRY)","gram-platin"),
        "8" : ("Gümüş/USD (XAG)",  "XAG-USD"),
        "9" : ("Platin/USD (XPT)", "XPT-USD"),
        "10": ("Paladyum/USD(XPD)","XPD-USD"),
    }
    KURUM_DESTEKLI = {"gram-altin","gram-gumus","ons-altin","gram-platin"}

    def __init__(self, sembol: str):
        FinansalEnstruman.__init__(self, sembol)   # upper() YOK
        self._fx = bp.FX(sembol)


# ═══════════════════════════════════════════════════════════════════
#  KRİPTO  (bp.Crypto)
# ═══════════════════════════════════════════════════════════════════

class Kripto(FinansalEnstruman):
    """Kripto para fiyatları. Kaynak: BtcTurk. Tüm çiftler: bp.crypto_pairs()"""
    def __init__(self, sembol: str):
        super().__init__(sembol.upper())
        self._c = bp.Crypto(self.sembol)

    def guncel_fiyat(self) -> float:
        return safe_float(self._c.current)

    def gecmis_veri(self, period="1ay") -> pd.DataFrame:
        return self._c.history(period=period)


# ═══════════════════════════════════════════════════════════════════
#  YATIRIM FONU  (bp.Fund)
# ═══════════════════════════════════════════════════════════════════

class YatirimFonu(FinansalEnstruman):
    """TEFAS yatırım fonları. Arama: bp.search_funds(terim)"""
    def __init__(self, kod: str):
        super().__init__(kod.upper())
        self._f = bp.Fund(self.sembol)

    def guncel_fiyat(self) -> float:
        bilgi = self._f.info
        if not dict_kontrol(bilgi): return None
        for k in ("pay fiyatı","pay_fiyati","unit_price","price","last"):
            try: return float(str(bilgi[k]).replace(",","."))
            except: pass
        return None

    def gecmis_veri(self, period="1ay") -> pd.DataFrame:
        return self._f.history(period=period)

    def bilgi(self) -> dict:           return self._f.info
    def performans(self) -> dict:      return self._f.performance
    def dagilim(self) -> pd.DataFrame: return self._f.allocation
    def dagilim_gecmis(self, period="3ay") -> pd.DataFrame:
        return self._f.allocation_history(period=period)


# ═══════════════════════════════════════════════════════════════════
#  ENDEKs  (bp.Index)
# ═══════════════════════════════════════════════════════════════════

class Endeks(FinansalEnstruman):
    """
    BIST endeksleri. Kaynak: Paratic / TradingView
    Tüm endeksler: bp.indices() → 33 popüler, bp.all_indices() → 79 tamamı
    """
    def __init__(self, kod: str):
        super().__init__(kod.upper())
        self._idx = bp.Index(self.sembol)

    def guncel_fiyat(self) -> float:
        try:
            bilgi = self._idx.info
            if isinstance(bilgi, dict):
                for k in ("last","value","close","current","price"):
                    v = safe_float(bilgi.get(k))
                    if v: return v
        except: pass
        try:
            df = self._idx.history(period="1g")
            return safe_float(df["Close"].iloc[-1]) if df_kontrol(df) else None
        except: return None

    def gecmis_veri(self, period="1ay") -> pd.DataFrame:
        return self._idx.history(period=period)

    def bilgi(self) -> dict:           return self._idx.info
    def bilesenler(self) -> pd.DataFrame: return self._idx.components


# ═══════════════════════════════════════════════════════════════════
#  ENFLASYON  (bp.Inflation — TÜREMEZ)
# ═══════════════════════════════════════════════════════════════════

class Enflasyon:
    """TCMB enflasyon verileri. Fiyat enstrümanı değil → FinansalEnstruman'dan türemez."""
    def __init__(self):
        self._inf = bp.Inflation()

    def son_tufe(self)                    -> dict:          return self._inf.latest()
    def tufe_gecmis(self)                 -> pd.DataFrame:  return self._inf.tufe()
    def ufe_gecmis(self)                  -> pd.DataFrame:  return self._inf.ufe()
    def hesapla(self, tutar, bas, bit)    -> dict:
        return self._inf.calculate(tutar, bas, bit)


# ═══════════════════════════════════════════════════════════════════
#  VİOP  (bp.VIOP — TÜREMEZ)
# ═══════════════════════════════════════════════════════════════════

class VIOP:
    """Vadeli işlem ve opsiyonlar. Kaynak: İş Yatırım. Fiyat metodu yok → türemez."""
    def __init__(self): self._v = bp.VIOP()

    @property
    def futures(self):           return self._v.futures
    @property
    def options(self):           return self._v.options
    @property
    def stock_futures(self):     return self._v.stock_futures
    @property
    def index_futures(self):     return self._v.index_futures
    @property
    def currency_futures(self):  return self._v.currency_futures
    @property
    def commodity_futures(self): return self._v.commodity_futures
    @property
    def stock_options(self):     return self._v.stock_options
    @property
    def index_options(self):     return self._v.index_options
    def sembole_gore(self, sembol) -> pd.DataFrame:
        return self._v.get_by_symbol(sembol.upper())


# ═══════════════════════════════════════════════════════════════════
#  PORTFÖY  (bp.Portfolio — kompozisyon, TÜREMEZ)
# ═══════════════════════════════════════════════════════════════════

class Portfoy:
    """
    Portföy yöneticisi. Tüm pozisyonlar _lotlar listesinde tutulur.
    Aynı sembol birden fazla lot olarak eklenebilir (farklı maliyetler).
    """
    def __init__(self, ad="Portföyüm"):
        self.ad            = ad
        self._bp           = bp.Portfolio()
        self._lotlar: list = []
        self.benchmark     = None

    # ── Ekleme ───────────────────────────────────────────────────────────────

    def _ekle(self, sembol, tur, adet, maliyet, tarih, nesne):
        self._lotlar.append({
            "sembol" : sembol,
            "tur"    : tur,
            "adet"   : float(adet),
            "maliyet": float(maliyet) if maliyet is not None else None,
            "tarih"  : tarih,
            "nesne"  : nesne,
        })

    def ekle_hisse(self, sembol, adet, maliyet=None, tarih=None):
        s = sembol.upper()
        kw = {"shares": float(adet)}
        if maliyet: kw["cost"] = float(maliyet)
        if tarih:   kw["purchase_date"] = tarih
        try: self._bp.add(s, **kw)
        except: pass
        self._ekle(s, "Hisse", adet, maliyet, tarih, Hisse(s))
        console.print(f"  [green]✓[/green] Hisse: {s}  {adet} adet"
                      + (f"  @ {maliyet} TRY" if maliyet else ""))

    def ekle_fon(self, kod, adet, maliyet=None):
        k = kod.upper()
        kw = {"shares": float(adet), "asset_type": "fund"}
        if maliyet: kw["cost"] = float(maliyet)
        try: self._bp.add(k, **kw)
        except: pass
        self._ekle(k, "Fon", adet, maliyet, None, YatirimFonu(k))
        console.print(f"  [green]✓[/green] Fon: {k}  {adet} adet"
                      + (f"  @ {maliyet} TRY" if maliyet else ""))

    def ekle_emtia(self, sembol, miktar, maliyet=None):
        self._ekle(sembol, "Emtia", miktar, maliyet, None, Emtia(sembol))
        console.print(f"  [green]✓[/green] Emtia: {sembol}  {miktar} birim"
                      + (f"  @ {maliyet} TRY" if maliyet else ""))

    def ekle_kripto(self, sembol, miktar, maliyet=None):
        s = sembol.upper()
        self._ekle(s, "Kripto", miktar, maliyet, None, Kripto(s))
        console.print(f"  [green]✓[/green] Kripto: {s}  {miktar} adet"
                      + (f"  @ {maliyet} TRY" if maliyet else ""))

    def ekle_doviz(self, sembol, miktar, maliyet=None):
        s = sembol.upper()
        self._ekle(s, "Döviz", miktar, maliyet, None, Doviz(s))
        console.print(f"  [green]✓[/green] Döviz: {s}  {miktar} birim"
                      + (f"  @ {maliyet} TRY" if maliyet else ""))

    def benchmark_ayarla(self, endeks="XU100"):
        self.benchmark = endeks.upper()
        try: self._bp.set_benchmark(self.benchmark)
        except: pass
        console.print(f"  [cyan]Benchmark: {self.benchmark}[/cyan]")

    # ── Görüntüleme ──────────────────────────────────────────────────────────

    def ozet(self):
        if not self._lotlar:
            console.print("  [yellow]Portföy boş.[/yellow]"); return

        t = Table(title=f"Portföy — {self.ad}", box=box.ROUNDED,
                  border_style="cyan", show_lines=True)
        for col, kw in [("#","right"), ("Sembol",""), ("Tür",""), ("Adet","right"),
                        ("Mal./Birim","right"), ("Güncel","right"),
                        ("Top.Maliyet","right"), ("Güncel Değer","right"),
                        ("PnL","right"), ("PnL%","right"), ("Tarih","")]:
            t.add_column(col, justify=kw if kw else "left",
                         min_width=8 if kw == "right" else 6)

        top_mal = top_deg = 0.0
        for i, lot in enumerate(self._lotlar, 1):
            try:
                raw   = lot["nesne"].guncel_fiyat()
                guncel = safe_float(raw)
                hata   = None if guncel else f"[dim]?[/dim]"
            except Exception as e:
                guncel = None
                hata   = f"[red]{str(e)[:25]}[/red]"

            adet   = lot["adet"]
            mal_b  = lot["maliyet"]
            # Maliyet girilmediyse güncel fiyatı maliyet say
            if mal_b is None and guncel: mal_b = guncel

            t_mal  = (mal_b  * adet) if mal_b  is not None else None
            t_deg  = (guncel * adet) if guncel is not None else None
            pnl    = (t_deg - t_mal) if (t_deg and t_mal) else None
            pct    = (pnl / t_mal * 100) if (pnl is not None and t_mal and t_mal != 0) else None

            if t_mal: top_mal += t_mal
            if t_deg: top_deg += t_deg

            renk    = lambda v: "green" if v >= 0 else "red"
            pnl_s   = (f"[{renk(pnl)}]{sayi_kisalt(pnl)}[/]" if pnl is not None else "—")
            pct_s   = (f"[{renk(pct)}]{pct:+.2f}%[/]" if pct is not None else "—")
            gun_s   = hata or sayi_kisalt(guncel)

            t.add_row(str(i), lot["sembol"], lot["tur"],
                      f"{adet:,.4f}",
                      sayi_kisalt(mal_b) if mal_b else "—",
                      gun_s,
                      sayi_kisalt(t_mal), sayi_kisalt(t_deg),
                      pnl_s, pct_s, str(lot["tarih"] or "—"))

        console.print(t)
        net    = top_deg - top_mal
        rn     = "green" if net >= 0 else "red"
        pct_g  = (net / top_mal * 100) if top_mal else 0
        console.print(
            f"\n  Toplam Maliyet : [yellow]{sayi_kisalt(top_mal)} TRY[/yellow]\n"
            f"  Toplam Değer   : [yellow]{sayi_kisalt(top_deg)} TRY[/yellow]\n"
            f"  Net PnL        : [{rn}]{sayi_kisalt(net)} TRY  ({pct_g:+.2f}%)[/{rn}]")

        if self.benchmark:
            try:
                bg = Endeks(self.benchmark).getiri_hesapla("1ay")
                if bg is not None:
                    fark = pct_g - bg
                    rf   = "green" if fark >= 0 else "red"
                    console.print(
                        f"  Benchmark ({self.benchmark}) 1Ay: "
                        f"[cyan]{bg:+.2f}%[/cyan]  |  "
                        f"Fark: [{rf}]{fark:+.2f}%[/{rf}]")
            except: pass

    def lot_sil(self, no: int):
        idx = no - 1
        if 0 <= idx < len(self._lotlar):
            s = self._lotlar.pop(idx)
            console.print(f"  [red]Silindi:[/red] #{no} {s['sembol']}")
        else:
            console.print(f"  [red]Geçersiz lot no: {no}[/red]")

    def bp_holdings(self) -> pd.DataFrame:
        return self._bp.holdings


# ═══════════════════════════════════════════════════════════════════
#  TEKNİK ANALİZ
# ═══════════════════════════════════════════════════════════════════

class TeknikAnalizci:
    """OHLCV DataFrame alan statik teknik indikatör metodları."""

    @staticmethod
    def sma(df, n):    return df["Close"].rolling(n).mean()
    @staticmethod
    def ema(df, n):    return df["Close"].ewm(span=n, adjust=False).mean()
    @staticmethod
    def rsi(df, n=14) -> pd.Series:
        d = df["Close"].diff()
        g = d.clip(lower=0).rolling(n).mean()
        l = (-d.clip(upper=0)).rolling(n).mean()
        return 100 - 100 / (1 + g / l)
    @staticmethod
    def macd(df, fast=12, slow=26, sig=9) -> pd.DataFrame:
        m = df["Close"].ewm(span=fast,adjust=False).mean() - df["Close"].ewm(span=slow,adjust=False).mean()
        s = m.ewm(span=sig, adjust=False).mean()
        return pd.DataFrame({"macd": m, "sinyal": s, "hist": m - s})
    @staticmethod
    def bollinger(df, n=20, k=2.0) -> pd.DataFrame:
        mid = df["Close"].rolling(n).mean()
        std = df["Close"].rolling(n).std()
        return pd.DataFrame({"ust": mid+k*std, "orta": mid, "alt": mid-k*std})
    @staticmethod
    def stokastik(df, k=14, d=3) -> pd.DataFrame:
        lo = df["Low"].rolling(k).min()
        hi = df["High"].rolling(k).max()
        K  = 100 * (df["Close"] - lo) / (hi - lo)
        return pd.DataFrame({"K": K, "D": K.rolling(d).mean()})
    @staticmethod
    def atr(df, n=14) -> pd.Series:
        tr = pd.concat([df["High"]-df["Low"],
                        (df["High"]-df["Close"].shift()).abs(),
                        (df["Low"] -df["Close"].shift()).abs()], axis=1).max(axis=1)
        return tr.rolling(n).mean()
    @staticmethod
    def obv(df) -> pd.Series:
        sgn = np.where(df["Close"]>df["Close"].shift(1),1,
              np.where(df["Close"]<df["Close"].shift(1),-1,0))
        return pd.Series((sgn*df["Volume"]).cumsum(), index=df.index)
    @staticmethod
    def vwap(df) -> pd.Series:
        tp = (df["High"]+df["Low"]+df["Close"])/3
        return (tp*df["Volume"]).cumsum() / df["Volume"].cumsum()
    @staticmethod
    def cci(df, n=20) -> pd.Series:
        tp  = (df["High"]+df["Low"]+df["Close"])/3
        mad = tp.rolling(n).apply(lambda x: np.mean(np.abs(x-x.mean())), raw=True)
        return (tp - tp.rolling(n).mean()) / (0.015 * mad)
    @staticmethod
    def williams_r(df, n=14) -> pd.Series:
        return -100*(df["High"].rolling(n).max()-df["Close"]) / \
               (df["High"].rolling(n).max()-df["Low"].rolling(n).min())
    @staticmethod
    def momentum(df, n=10) -> pd.Series:
        return df["Close"] - df["Close"].shift(n)
    @staticmethod
    def pivot_noktalari(df) -> dict:
        h,l,c = float(df["High"].iloc[-2]),float(df["Low"].iloc[-2]),float(df["Close"].iloc[-2])
        P = (h+l+c)/3
        return {"P":round(P,2),"R1":round(2*P-l,2),"R2":round(P+(h-l),2),
                "S1":round(2*P-h,2),"S2":round(P-(h-l),2)}
    @staticmethod
    def fibonacci(df) -> dict:
        yuk = float(df["High"].max() if "High" in df.columns else df["Close"].max())
        dus = float(df["Low"].min()  if "Low"  in df.columns else df["Close"].min())
        ar  = yuk - dus
        if ar == 0: return {}
        geri = {f"%{r*100:.1f}": round(yuk-ar*r,4)
                for r in [0.0,0.236,0.382,0.500,0.618,0.786,1.0]}
        uznt = {f"%{e*100:.1f}": round(dus+ar*e,4)
                for e in [1.272,1.414,1.618,2.000,2.618]}
        return {"geri": geri, "uzanti": uznt, "yuksek": yuk, "dusuk": dus}
    @staticmethod
    def ichimoku(df) -> pd.DataFrame:
        if len(df) < 26: return pd.DataFrame()
        h9  = df["High"].rolling(9).max();  l9  = df["Low"].rolling(9).min()
        h26 = df["High"].rolling(26).max(); l26 = df["Low"].rolling(26).min()
        h52 = (df["High"].rolling(52).max() if len(df)>=52
               else df["High"].rolling(26).max())
        l52 = (df["Low"].rolling(52).min()  if len(df)>=52
               else df["Low"].rolling(26).min())
        tenkan = (h9+l9)/2; kijun = (h26+l26)/2
        return pd.DataFrame({
            "tenkan": tenkan, "kijun": kijun,
            "senkou_a": (tenkan+kijun)/2, "senkou_b": (h52+l52)/2,
            "chikou": df["Close"],
        })
    @staticmethod
    def destek_direnc(df, pencere=5, min_temas=2, tolerans=0.015) -> dict:
        if not all(c in df.columns for c in ("High","Low","Close")):
            return {"Direnc":[],"Destek":[]}
        h = df["High"].values.astype(float)
        l = df["Low"].values.astype(float)
        n = len(df)
        tepeler, dipler = [], []
        for i in range(pencere, n-pencere):
            bh = h[i-pencere:i+pencere+1]
            bl = l[i-pencere:i+pencere+1]
            if h[i] >= bh.max()-1e-9: tepeler.append(h[i])
            if l[i] <= bl.min()+1e-9: dipler.append(l[i])
        def zone(noktalar):
            if not noktalar: return []
            sirali = sorted(noktalar)
            gruplar = [[sirali[0]]]
            for s in sirali[1:]:
                ref = gruplar[-1][0]
                if abs(s-ref)/max(ref,1e-9) < tolerans: gruplar[-1].append(s)
                else: gruplar.append([s])
            return [(round(sum(g)/len(g),4), len(g)) for g in gruplar if len(g)>=min_temas]
        son = float(df["Close"].iloc[-1])
        return {"Direnc": [(s,t) for s,t in zone(tepeler) if s>son][:5],
                "Destek": [(s,t) for s,t in zone(dipler)  if s<son][:5]}


# ═══════════════════════════════════════════════════════════════════
#  GRAFİK
# ═══════════════════════════════════════════════════════════════════

class GrafikEkrani:
    """Mumlu grafik + teknik indikatörler + çapraz imleç."""

    AGIRLIK = {
        "fiyat":3,"hacim":0.7,"obv":0.7,"rsi":0.9,
        "macd":0.9,"stokastik":0.9,"atr":0.7,"cci":0.8,
        "williams":0.7,"momentum":0.7,
    }

    @staticmethod
    def panel_sec() -> dict:
        _panel(
            "  [bold]Fiyat Katmanları (her zaman mumlu fiyat + SMA20/50):[/bold]\n"
            "  [cyan]1[/cyan] Bollinger Bantları   [cyan]2[/cyan] EMA9   [cyan]3[/cyan] EMA20\n"
            "  [cyan]4[/cyan] VWAP   [cyan]5[/cyan] Pivot   [cyan]6[/cyan] Fibonacci\n"
            "  [cyan]7[/cyan] Ichimoku (Tenkan/Kijun/Bulut)   [cyan]8[/cyan] Destek & Direnc\n\n"
            "  [bold]Alt Paneller:[/bold]\n"
            "  [cyan]9[/cyan] Hacim   [cyan]10[/cyan] OBV   [cyan]11[/cyan] RSI\n"
            "  [cyan]12[/cyan] MACD   [cyan]13[/cyan] Stokastik   [cyan]14[/cyan] ATR\n"
            "  [cyan]15[/cyan] CCI   [cyan]16[/cyan] Williams %R   [cyan]17[/cyan] Momentum\n\n"
            "  Virgülle sec (örn: 1,6,7,8,9,11,12) | [cyan]temel[/cyan] | [cyan]tam[/cyan] | [cyan]hepsi[/cyan]",
            "GRAFİK PANEL SEÇİMİ", "cyan")
        HAR = {
            "1":"bollinger","2":"ema9","3":"ema20","4":"vwap","5":"pivot",
            "6":"fibonacci","7":"ichimoku","8":"destek",
            "9":"hacim","10":"obv","11":"rsi","12":"macd",
            "13":"stokastik","14":"atr","15":"cci","16":"williams","17":"momentum",
        }
        g = input("  Seçim: ").strip().lower()
        if g == "temel": return {"bollinger":True,"hacim":True,"rsi":True,"macd":True}
        if g == "tam":   return {"bollinger":True,"fibonacci":True,"ichimoku":True,
                                  "destek":True,"hacim":True,"rsi":True,"macd":True}
        if g == "hepsi": return {v:True for v in HAR.values()}
        sec = {v:False for v in HAR.values()}
        for s in [x.strip() for x in g.split(",")]:
            if s in HAR: sec[HAR[s]] = True
        return sec

    @staticmethod
    def _has_ohlc(df): return all(c in df.columns for c in ("Open","High","Low","Close"))

    @staticmethod
    def _mum_ciz(ax, df):
        n = len(df)
        if not GrafikEkrani._has_ohlc(df):
            ax.plot(range(n), df["Close"].values, color=C["line"], lw=1.5, label="Fiyat")
        else:
            for i in range(n):
                try:
                    o,h,l,c = (float(df[x].iloc[i]) for x in ("Open","High","Low","Close"))
                except: continue
                rk = C["up"] if c>=o else C["down"]
                ax.plot([i,i],[l,h], color=rk, lw=0.9, zorder=1)
                bh = max(abs(c-o), abs(c)*0.0001)
                ax.add_patch(mpatches.Rectangle(
                    (i-0.38,min(o,c)), 0.76, bh,
                    facecolor=rk, edgecolor=rk, lw=0, alpha=0.92, zorder=2))
        adim = max(1,n//10); ticks = list(range(0,n,adim))
        ax.set_xticks(ticks)
        ax.set_xticklabels([str(df.index[i])[:10] for i in ticks],
                           rotation=35, ha="right", fontsize=7)
        ax.set_xlim(-1, n)

    @staticmethod
    def _crosshair(fig, axler, df, panel_adlari):
        vlines = [ax.axvline(0,color=C["cross"],alpha=0.3,lw=0.7,ls=":",visible=False)
                  for ax in axler]
        hlines = [ax.axhline(0,color=C["cross"],alpha=0.3,lw=0.7,ls=":",visible=False)
                  for ax in axler]
        info   = axler[0].text(0.01,0.99,"",transform=axler[0].transAxes,
                               fontsize=8, va="top",
                               bbox=dict(boxstyle="round,pad=0.4",
                                         facecolor=_BG2,edgecolor=_GRID,alpha=0.9),
                               color="#c9d1d9", family="monospace", zorder=10)
        idx = df.index.tolist()
        def on_move(ev):
            if ev.xdata is None: return
            xi = max(0,min(int(round(ev.xdata)),len(idx)-1))
            for vl in vlines: vl.set_xdata([xi,xi]); vl.set_visible(True)
            for ax,hl in zip(axler,hlines):
                hl.set_ydata([ev.ydata,ev.ydata] if ax==ev.inaxes else [0,0])
                hl.set_visible(ax==ev.inaxes)
            row = df.iloc[xi]
            lines = [f"  {str(idx[xi])[:16]}"]
            try: lines += [f"  A:{row['Open']:.4f}  Y:{row['High']:.4f}",
                           f"  D:{row['Low']:.4f}  K:{row['Close']:.4f}"]
            except: lines.append(f"  K:{row.get('Close','?')}")
            if "Volume" in row: lines.append(f"  H:{sayi_kisalt(row['Volume'])}")
            info.set_text("\n".join(lines))
            fig.canvas.draw_idle()
        def on_leave(ev):
            for vl in vlines: vl.set_visible(False)
            for hl in hlines: hl.set_visible(False)
            info.set_text("")
            fig.canvas.draw_idle()
        fig.canvas.mpl_connect("motion_notify_event", on_move)
        fig.canvas.mpl_connect("axes_leave_event",    on_leave)

    @classmethod
    def ciz(cls, df: pd.DataFrame, sembol="", goster: dict = None):
        if not df_kontrol(df): console.print("  [red]Veri yok.[/red]"); return
        if goster is None: goster = {"bollinger":True,"hacim":True,"rsi":True,"macd":True}

        ALT = ["hacim","obv","rsi","macd","stokastik","atr","cci","williams","momentum"]
        aktif = [p for p in ALT if goster.get(p,False)]
        paneller = ["fiyat"] + aktif
        agirlik  = [cls.AGIRLIK.get(p,0.8) for p in paneller]

        fig, axler = plt.subplots(
            len(paneller),1,
            figsize=(16, 3+2.2*len(paneller)),
            gridspec_kw={"height_ratios": agirlik},
            sharex=False)
        if len(paneller)==1: axler=[axler]
        fig.suptitle(f"  ▶  {sembol}  —  Teknik Analiz",
                     fontsize=13, color=C["line"], fontweight="bold",
                     x=0.02, ha="left")
        fig.patch.set_facecolor(_BG)
        ax0 = axler[0]; n = len(df)

        # Mumlar
        cls._mum_ciz(ax0, df)

        # SMA 20/50
        if n>=20: ax0.plot(range(n),TeknikAnalizci.sma(df,20).values,
                           color=C["sma20"],lw=1.1,ls=":",label="SMA20",zorder=3)
        if n>=50: ax0.plot(range(n),TeknikAnalizci.sma(df,50).values,
                           color=C["sma50"],lw=1.1,ls=":",label="SMA50",zorder=3)

        # Fiyat katmanları
        if goster.get("bollinger") and n>=20:
            bb=TeknikAnalizci.bollinger(df)
            ax0.plot(range(n),bb["ust"].values, color=C["bb"],lw=0.8,ls="--")
            ax0.plot(range(n),bb["orta"].values,color=C["sma20"],lw=0.8,ls="--",label="BB Mid")
            ax0.plot(range(n),bb["alt"].values, color=C["bb"],lw=0.8,ls="--")
            ax0.fill_between(range(n),bb["ust"].values,bb["alt"].values,alpha=0.05,color=C["bb_fill"])
        if goster.get("ema9") and n>=9:
            ax0.plot(range(n),TeknikAnalizci.ema(df,9).values,
                     color=C["ema9"],lw=1.0,ls="-.",label="EMA9",zorder=3)
        if goster.get("ema20") and n>=20:
            ax0.plot(range(n),TeknikAnalizci.ema(df,20).values,
                     color=C["ema20"],lw=1.0,ls="-.",label="EMA20",zorder=3)
        if goster.get("vwap") and "Volume" in df.columns:
            ax0.plot(range(n),TeknikAnalizci.vwap(df).values,
                     color=C["vwap"],lw=1.2,ls="--",label="VWAP",zorder=3)
        if goster.get("pivot") and n>=2:
            pvt=TeknikAnalizci.pivot_noktalari(df)
            for k,v in pvt.items():
                rk={"P":"#ffffff","R1":C["direnc"],"R2":C["direnc"],"S1":C["destek"],"S2":C["destek"]}[k]
                ax0.axhline(v,color=rk,lw=0.7,ls="--",alpha=0.7,label=f"{k}={v}")

        # Fibonacci
        if goster.get("fibonacci"):
            fib=TeknikAnalizci.fibonacci(df)
            if fib:
                ax0.set_xlim(-2,n+14)
                for etiket,sev in fib["geri"].items():
                    rk=C["fib_r"]
                    ax0.axhline(sev,color=rk,lw=0.8,ls="--",alpha=0.75)
                    ax0.annotate(f" GC {etiket}  {sev:,.2f}",
                                 xy=(n,sev), xytext=(n+0.5,sev),
                                 fontsize=7,color=rk,va="center",
                                 bbox=dict(boxstyle="round,pad=0.15",
                                           facecolor=_BG,edgecolor=rk,alpha=0.8,lw=0.5))
                for etiket,sev in fib["uzanti"].items():
                    ax0.axhline(sev,color=C["fib_e"],lw=0.6,ls=":",alpha=0.65)
                    ax0.annotate(f" UZ {etiket}  {sev:,.2f}",
                                 xy=(n,sev), xytext=(n+0.5,sev),
                                 fontsize=7,color=C["fib_e"],va="center",
                                 bbox=dict(boxstyle="round,pad=0.15",
                                           facecolor=_BG,edgecolor=C["fib_e"],alpha=0.8,lw=0.5))

        # Ichimoku
        if goster.get("ichimoku") and n>=26:
            ich=TeknikAnalizci.ichimoku(df)
            ix=np.arange(n)
            ax0.plot(ix,ich["tenkan"].fillna(method="bfill").values,
                     color=C["tenkan"],lw=1.5,label="Tenkan",zorder=5)
            ax0.plot(ix,ich["kijun"].fillna(method="bfill").values,
                     color=C["kijun"],lw=1.8,label="Kijun",zorder=5)
            ax0.plot(ix,ich["chikou"].values,color=C["chikou"],
                     lw=0.9,ls="dashed",alpha=0.55,label="Chikou",zorder=3)
            sa=ich["senkou_a"].fillna(method="bfill").values
            sb=ich["senkou_b"].fillna(method="bfill").values
            ax0.plot(ix,sa,color=C["senkou_a"],lw=0.7,alpha=0.5)
            ax0.plot(ix,sb,color=C["senkou_b"],lw=0.7,alpha=0.5)
            gecerli = ~np.isnan(sa)&~np.isnan(sb)
            if (gecerli&(sa>=sb)).any():
                ax0.fill_between(ix,sa,sb,where=gecerli&(sa>=sb),
                                 interpolate=True,alpha=0.25,color=C["senkou_a"],label="Kumo↑")
            if (gecerli&(sa<sb)).any():
                ax0.fill_between(ix,sa,sb,where=gecerli&(sa<sb),
                                 interpolate=True,alpha=0.25,color=C["senkou_b"],label="Kumo↓")
            for lbl,seri,rk in [("T",ich["tenkan"],C["tenkan"]),
                                  ("K",ich["kijun"],C["kijun"]),
                                  ("A",ich["senkou_a"],C["senkou_a"]),
                                  ("B",ich["senkou_b"],C["senkou_b"])]:
                val=safe_float(seri.dropna().iloc[-1]) if not seri.dropna().empty else None
                if val and not np.isnan(val):
                    ax0.annotate(f" {lbl}={val:,.2f}",xy=(n-1,val),xytext=(n+0.3,val),
                                 fontsize=7,color=rk,va="center",
                                 bbox=dict(boxstyle="round,pad=0.2",facecolor=_BG,edgecolor=rk,alpha=0.85,lw=0.6))

        # Destek / Direnc
        if goster.get("destek") and n>=30:
            dd=TeknikAnalizci.destek_direnc(df)
            son=float(df["Close"].iloc[-1]); tol=son*0.005
            for sev,tm in dd["Direnc"]:
                ax0.axhspan(sev-tol,sev+tol,alpha=0.12,color=C["direnc"],zorder=3)
                ax0.axhline(sev,color=C["direnc"],lw=1.0,ls=(0,(5,3)),alpha=0.9,zorder=4)
                ax0.annotate(f" DİR {sev:,.2f} ({tm}×)",
                             xy=(2,sev),xytext=(2,sev+tol*0.5),fontsize=7.5,
                             color=C["direnc"],fontweight="bold",
                             bbox=dict(boxstyle="round,pad=0.2",facecolor=_BG,
                                       edgecolor=C["direnc"],alpha=0.88,lw=0.7))
            for sev,tm in dd["Destek"]:
                ax0.axhspan(sev-tol,sev+tol,alpha=0.12,color=C["destek"],zorder=3)
                ax0.axhline(sev,color=C["destek"],lw=1.0,ls=(0,(5,3)),alpha=0.9,zorder=4)
                ax0.annotate(f" DES {sev:,.2f} ({tm}×)",
                             xy=(2,sev),xytext=(2,sev-tol*1.5),fontsize=7.5,
                             color=C["destek"],fontweight="bold",
                             bbox=dict(boxstyle="round,pad=0.2",facecolor=_BG,
                                       edgecolor=C["destek"],alpha=0.88,lw=0.7))

        ax0.set_ylabel("Fiyat",fontsize=8,color=_TICK)
        ax0.legend(fontsize=7,loc="upper left",facecolor=_BG2,
                   edgecolor=_GRID,framealpha=0.85,ncol=2,handlelength=1.2)
        ax0.grid(True,alpha=0.3)
        ax0.set_facecolor(_BG2)

        # Alt paneller
        for ax,panel in zip(axler[1:],aktif):
            ax.set_facecolor(_BG2); ax.grid(True,alpha=0.3)
            ix = np.arange(n)
            if panel=="hacim" and "Volume" in df.columns:
                rk=[C["up"] if df["Close"].iloc[i]>=df["Open"].iloc[i] else C["down"] for i in range(n)]
                ax.bar(ix,df["Volume"].values,color=rk,alpha=0.85,width=0.85)
                ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x,_:sayi_kisalt(x)))
                ax.set_ylabel("Hacim",fontsize=8,color=_TICK); ax.set_xlim(-1,n)
            elif panel=="obv" and "Volume" in df.columns:
                v=TeknikAnalizci.obv(df).values
                ax.plot(ix,v,color=C["obv"],lw=1.3); ax.fill_between(ix,v,alpha=0.1,color=C["obv"])
                ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x,_:sayi_kisalt(x)))
                ax.set_ylabel("OBV",fontsize=8,color=_TICK); ax.set_xlim(-1,n)
            elif panel=="rsi" and n>=14:
                v=TeknikAnalizci.rsi(df).values
                ax.plot(ix,v,color=C["rsi"],lw=1.3)
                ax.axhline(70,color=C["rsi_up"],ls="--",lw=0.7,alpha=0.7)
                ax.axhline(50,color=_TICK,ls="--",lw=0.5,alpha=0.4)
                ax.axhline(30,color=C["rsi_dn"],ls="--",lw=0.7,alpha=0.7)
                ax.fill_between(ix,v,70,where=(v>=70),alpha=0.2,color=C["rsi_up"])
                ax.fill_between(ix,v,30,where=(v<=30),alpha=0.2,color=C["rsi_dn"])
                ax.set_ylim(0,100); ax.set_yticks([30,50,70])
                ax.set_ylabel("RSI(14)",fontsize=8,color=_TICK); ax.set_xlim(-1,n)
            elif panel=="macd" and n>=26:
                md=TeknikAnalizci.macd(df)
                ax.plot(ix,md["macd"].values,color=C["macd"],lw=1.3,label="MACD")
                ax.plot(ix,md["sinyal"].values,color=C["sig"],lw=1.0,ls="--",label="Sinyal")
                rk=[C["up"] if v>=0 else C["down"] for v in md["hist"].values]
                ax.bar(ix,md["hist"].values,color=rk,alpha=0.65,width=0.85)
                ax.axhline(0,color=_TICK,lw=0.5)
                ax.legend(fontsize=7,loc="upper left",facecolor=_BG2,edgecolor=_GRID,framealpha=0.8)
                ax.set_ylabel("MACD",fontsize=8,color=_TICK); ax.set_xlim(-1,n)
            elif panel=="stokastik" and n>=14:
                stk=TeknikAnalizci.stokastik(df)
                ax.plot(ix,stk["K"].values,color=C["stk_k"],lw=1.2,label="%K")
                ax.plot(ix,stk["D"].values,color=C["stk_d"],lw=1.0,ls="--",label="%D")
                ax.axhline(80,color=C["rsi_up"],ls="--",lw=0.7,alpha=0.7)
                ax.axhline(20,color=C["rsi_dn"],ls="--",lw=0.7,alpha=0.7)
                ax.set_ylim(0,100); ax.set_yticks([20,50,80])
                ax.legend(fontsize=7,loc="upper left",facecolor=_BG2,edgecolor=_GRID,framealpha=0.8)
                ax.set_ylabel("Stokastik",fontsize=8,color=_TICK); ax.set_xlim(-1,n)
            elif panel=="atr" and n>=14:
                v=TeknikAnalizci.atr(df).values
                ax.plot(ix,v,color=C["atr"],lw=1.4); ax.fill_between(ix,v,alpha=0.15,color=C["atr"])
                ax.set_ylabel("ATR(14)",fontsize=8,color=_TICK); ax.set_xlim(-1,n)
            elif panel=="cci" and n>=20:
                v=TeknikAnalizci.cci(df).values
                ax.plot(ix,v,color="#e3b341",lw=1.2)
                ax.axhline(100,color=C["rsi_up"],ls="--",lw=0.7,alpha=0.7)
                ax.axhline(-100,color=C["rsi_dn"],ls="--",lw=0.7,alpha=0.7)
                ax.axhline(0,color=_TICK,lw=0.5)
                ax.set_ylabel("CCI(20)",fontsize=8,color=_TICK); ax.set_xlim(-1,n)
            elif panel=="williams" and n>=14:
                v=TeknikAnalizci.williams_r(df).values
                ax.plot(ix,v,color="#ff9e64",lw=1.2)
                ax.axhline(-20,color=C["rsi_up"],ls="--",lw=0.7,alpha=0.7)
                ax.axhline(-80,color=C["rsi_dn"],ls="--",lw=0.7,alpha=0.7)
                ax.set_ylabel("W%R(14)",fontsize=8,color=_TICK); ax.set_xlim(-1,n)
            elif panel=="momentum" and n>=10:
                v=TeknikAnalizci.momentum(df).values
                rk=[C["up"] if x>=0 else C["down"] for x in v]
                ax.bar(ix,v,color=rk,alpha=0.75,width=0.85)
                ax.axhline(0,color=_TICK,lw=0.5)
                ax.set_ylabel("Mom(10)",fontsize=8,color=_TICK); ax.set_xlim(-1,n)

        cls._crosshair(fig, axler, df, paneller)
        plt.tight_layout(rect=[0,0,1,0.97])
        plt.subplots_adjust(hspace=0.06)
        plt.show()

    @classmethod
    def normalize_karsilastirma(cls, enstrumanlar: list, period="1ay"):
        fig,ax = plt.subplots(figsize=(15,6))
        fig.patch.set_facecolor(_BG); ax.set_facecolor(_BG2)
        fig.suptitle(f"Normalize Getiri — {period}",fontsize=13,
                     color=C["line"],fontweight="bold")
        for i,(nesne,etiket) in enumerate(enstrumanlar):
            try:
                df=nesne.gecmis_veri(period=period)
                if not df_kontrol(df) or "Close" not in df.columns: continue
                norm=(df["Close"]/df["Close"].iloc[0])*100
                ax.plot(df.index,norm.values,label=etiket,
                        color=PALETTE[i%len(PALETTE)],lw=1.8)
            except Exception as e:
                console.print(f"  [yellow]{etiket}: {e}[/yellow]")
        ax.axhline(100,color=_TICK,ls="--",lw=0.8,alpha=0.5)
        ax.set_ylabel("Normalize (Başlangıç=100)")
        ax.legend(fontsize=9,facecolor=_BG2,edgecolor=_GRID)
        ax.grid(True,alpha=0.3)
        plt.tight_layout(); plt.show()

    @staticmethod
    def enflasyon(df: pd.DataFrame, baslik="Enflasyon"):
        if not df_kontrol(df): return
        fig,ax = plt.subplots(figsize=(13,5))
        fig.patch.set_facecolor(_BG); ax.set_facecolor(_BG2)
        fig.suptitle(baslik,fontsize=13,color=C["enf"],fontweight="bold")
        sutun = df.columns[-1]
        ax.plot(df.index,df[sutun].values,color=C["enf"],lw=1.8)
        ax.fill_between(df.index,df[sutun].values,alpha=0.15,color=C["enf"])
        ax.set_ylabel("(%)"); ax.grid(True,alpha=0.3)
        plt.xticks(rotation=30,ha="right"); plt.tight_layout(); plt.show()


# ═══════════════════════════════════════════════════════════════════
#  TEMEL ANALİZ RASYOLARI
# ═══════════════════════════════════════════════════════════════════

class TemelAnalizci:
    """
    Hisse senedi temel analizi — Türkçe terimler.
    Öncelik sırası: fast_info → mali tablolar → info → geçmiş veri
    """
    BIST30 = [
        "AKBNK","ARCLK","ASELS","BIMAS","EKGYO","EREGL","FROTO","GARAN",
        "HEKTS","ISCTR","KCHOL","KOZAA","PETKM","PGSUS","SAHOL","SASA",
        "SISE","TAVHL","TCELL","THYAO","TOASO","TTKOM","TUPRS","VAKBN",
        "VESTL","YKBNK","OYAKC","ENKAI","AKSEN","KOZAL",
    ]

    # ── Yardımcılar ─────────────────────────────────────────────────────────

    @staticmethod
    def _norm(s: str) -> str:
        """Türkçe karakterleri normalize et, küçük harf yap."""
        for o, y in [("ş","s"),("Ş","s"),("ğ","g"),("Ğ","g"),
                     ("ü","u"),("Ü","u"),("ö","o"),("Ö","o"),
                     ("ı","i"),("İ","i"),("ç","c"),("Ç","c"),
                     ("â","a"),("î","i"),("û","u"),("Â","a")]:
            s = s.replace(o, y)
        return re.sub(r"[\s\-_/\(\)]+","", s.lower())

    @staticmethod
    def _g(d: dict, *keys):
        """dict'ten ilk bulunan geçerli sayısal değeri döndür."""
        for k in keys:
            v = d.get(k)
            if v is None: continue
            try:
                f = float(str(v).replace(",",".").replace("%","").strip())
                if f == f: return f
            except: pass
        return None

    @staticmethod
    def _df_oku(df: pd.DataFrame, *terimler):
        """DataFrame index'inde normalize substring araması."""
        if not df_kontrol(df): return None
        for terim in terimler:
            nt = TemelAnalizci._norm(terim)
            for satir in df.index:
                ns = TemelAnalizci._norm(str(satir))
                if nt in ns or ns in nt:
                    try:
                        for col in df.columns:
                            v = float(df.loc[satir, col])
                            if v == v and v != 0: return v
                    except: pass
        return None

    # ── Ana hesaplama ────────────────────────────────────────────────────────

    @staticmethod
    def hesapla(sembol: str) -> dict:
        """
        Hissenin temel rasyolarını hesaplar.
        Döner: {rasyo_adı: değer, ...} — başlıklar "---" ile ayrılır.
        """
        h = Hisse(sembol)
        dfo = TemelAnalizci._df_oku
        g   = TemelAnalizci._g

        # Veri çek
        fi = None
        try: fi = h._t.fast_info
        except: pass
        inf = {}
        try: inf = h.detayli_bilgi() or {}
        except: pass
        inc = None
        try: inc = h.gelir_tablosu()
        except: pass
        bs = None
        try: bs = h.bilanco()
        except: pass
        cf = None
        try: cf = h.nakit_akis()
        except: pass

        def fia(k):
            try: return safe_float(fi[k])
            except: return None

        # fast_info
        fiyat     = fia("last_price")
        pd_deger  = fia("market_cap")
        paysayisi = fia("shares")
        fi_fk     = fia("pe_ratio")
        fi_pddd   = fia("pb_ratio")
        fi_yuk    = fia("year_high")
        fi_dus    = fia("year_low")

        # Değerleme — info önce, fast_info fallback
        fk      = g(inf,"trailingPE")  or fi_fk
        pd_dd   = g(inf,"priceToBook") or fi_pddd
        temkarvr= g(inf,"dividendYield")

        # Gelir tablosu
        ciro = dfo(inc,
            "net satis","satis gelirleri","hasilat","toplam satis",
            "net revenue","total revenue","revenues","net sales")
        brut = dfo(inc,"brut kar","gross profit")
        favok = dfo(inc,
            "favok","ebitda","esas faaliyet kar","faaliyet kar",
            "operating income","operating profit","ebit")
        net_kar = dfo(inc,
            "donem net kar","net kar","ana ortakliga ait",
            "net income","profit for the period","net profit")
        amortisman = dfo(inc,"amortisman","depreciation","itfa","amortisation")
        if favok is None and amortisman is not None:
            faaliyet = dfo(inc,"faaliyet kar","esas faaliyet","operating income")
            if faaliyet: favok = faaliyet + abs(amortisman)

        # Bilanço
        toplam_v = dfo(bs,
            "toplam varlik","aktif toplam","varliklar toplam",
            "toplam aktif","total assets")
        ozkaynak = dfo(bs,
            "toplam ozkaynak","ozkaynaklar toplam","ana ortakliga ait ozkaynak",
            "total equity","stockholders equity","shareholders equity","equity")
        if ozkaynak is None:
            top_y = dfo(bs,"toplam yukumluluk","total liabilities","yukumlulukler toplam")
            if toplam_v and top_y: ozkaynak = toplam_v - top_y
        kv_borc = dfo(bs,"kisa vadeli yukumluluk","current liabilities")
        donen_v = dfo(bs,"donen varlik","current assets")
        nakit   = dfo(bs,
            "nakit ve nakit benzeri","nakit ve diger nakit",
            "cash and cash equivalents","cash equivalents","nakit")
        kv_fin = dfo(bs,"kisa vadeli finansal borc","kisa vadeli banka kredi",
                     "short term borrowings","short-term borrowings")
        uv_fin = dfo(bs,"uzun vadeli finansal borc","uzun vadeli banka kredi",
                     "long term debt","long-term borrowings","long term borrowings")
        if kv_fin and uv_fin:   fin_borc = kv_fin + uv_fin
        elif uv_fin:             fin_borc = uv_fin
        elif kv_fin:             fin_borc = kv_fin
        else:
            fin_borc = dfo(bs,"finansal borc","total debt","net financial debt","borrowings")
        if fin_borc is None and ozkaynak:
            de_raw = g(inf,"debtToEquity")
            if de_raw: fin_borc = abs(ozkaynak) * (de_raw/100 if de_raw>10 else de_raw)

        # Nakit akış
        faaliyet_ncf = dfo(cf,
            "isletme faaliyetlerinden","faaliyet nakit",
            "operating activities","operating cash flow")
        fcf = dfo(cf,"serbest nakit","free cash flow")
        if fcf is None and faaliyet_ncf:
            yatirim = dfo(cf,"yatirim faaliyetleri","investing activities")
            capex   = dfo(cf,"maddi duran varlik","capital expenditure","property plant")
            if capex:  fcf = faaliyet_ncf - abs(capex)
            elif yatirim: fcf = faaliyet_ncf + min(0, yatirim)

        # Hesaplamalar
        def oran(pay, payda):
            if pay is None or payda is None or payda == 0: return None
            v = pay / payda * 100
            return None if v != v else round(v, 2)

        roe = oran(net_kar, ozkaynak)
        roa = oran(net_kar, toplam_v)
        nm  = oran(net_kar, ciro)
        em  = oran(favok,   ciro)
        bm  = oran(brut,    ciro)
        # info fallback (varsa daha güvenilir)
        if roe is None:
            v = g(inf,"roe"); roe = round(v*100,2) if v and abs(v)<5 else (round(v,2) if v else None)
        if roa is None:
            v = g(inf,"roa"); roa = round(v*100,2) if v and abs(v)<5 else (round(v,2) if v else None)
        if nm  is None:
            v = g(inf,"netMargin");   nm  = round(v*100,2) if v and abs(v)<5 else (round(v,2) if v else None)
        if em  is None:
            v = g(inf,"ebitdaMargin"); em = round(v*100,2) if v and abs(v)<5 else (round(v,2) if v else None)
        if bm  is None:
            v = g(inf,"grossMargin"); bm  = round(v*100,2) if v and abs(v)<5 else (round(v,2) if v else None)

        borcoz = None
        if fin_borc and ozkaynak: borcoz = round(abs(fin_borc/ozkaynak), 2)
        if borcoz is None:
            v = g(inf,"debtToEquity"); borcoz = round(v/100,2) if v and v>10 else (round(v,2) if v else None)

        cario = None
        if donen_v and kv_borc and kv_borc!=0: cario = round(donen_v/kv_borc, 2)
        if cario is None:
            v = g(inf,"currentRatio"); cario = round(v,2) if v else None

        net_borc = round(fin_borc - (nakit or 0), 0) if fin_borc else None
        firma_d  = round(pd_deger + net_borc, 0)     if (pd_deger and net_borc is not None) else None
        fd_favok = round(firma_d / favok, 2)          if (firma_d and favok and favok!=0) else None
        scf_ver  = round(fcf / pd_deger * 100, 2)     if (fcf and pd_deger and pd_deger!=0) else None

        # Temettü verimi
        if temkarvr:
            temkarvr = round(temkarvr*100 if temkarvr < 0.5 else temkarvr, 2)
        else:
            try:
                div_df = h.temettu()
                if df_kontrol(div_df) and fiyat and fiyat > 0:
                    now = pd.Timestamp.now()
                    idx_dt = pd.to_datetime(div_df.index, errors="coerce")
                    try:
                        bir_yil = now.tz_localize(idx_dt.tz) - pd.DateOffset(years=1)
                    except: bir_yil = now - pd.DateOffset(years=1)
                    son12 = div_df[idx_dt >= bir_yil]
                    if not son12.empty:
                        num_cols = [c for c in div_df.columns if pd.api.types.is_numeric_dtype(div_df[c])]
                        if num_cols:
                            yillik = float(son12[num_cols[0]].sum())
                            if yillik > 0: temkarvr = round(yillik / fiyat * 100, 2)
            except: pass

        # Getiriler — önce info, yoksa history
        r1m = r3m = r1y = None
        for attr, var in [("return_1m","r1m"),("return_3m","r3m"),("return_1y","r1y")]:
            v = g(inf, attr)
            if v:
                pct = round(v*100 if abs(v)<5 else v, 2)
                if var=="r1m":  r1m=pct
                elif var=="r3m": r3m=pct
                elif var=="r1y": r1y=pct
        if r1m is None or r3m is None or r1y is None:
            try:
                df_h = h.gecmis_veri(period="1y")
                if df_kontrol(df_h) and "Close" in df_h.columns:
                    son = float(df_h["Close"].iloc[-1])
                    nv  = len(df_h)
                    def getiri(b):
                        if nv>b: bas=float(df_h["Close"].iloc[-b]); return round((son-bas)/bas*100,2) if bas else None
                        return None
                    if r1m is None: r1m = getiri(21)
                    if r3m is None: r3m = getiri(63)
                    if r1y is None: r1y = getiri(min(252,nv-1))
            except: pass

        # Sektör — info + companies()
        sektor = sektortr = ""
        if isinstance(inf, dict):
            for k in ("sector","sectorDisp","sectorKey","Sektör","Sektor","sektör"):
                v = str(inf.get(k,"")).strip()
                if v and v not in ("None","nan",""): sektor = v; break
            for k in ("industry","industryDisp","industryKey","Alt Sektör","AltSektor"):
                v = str(inf.get(k,"")).strip()
                if v and v not in ("None","nan",""): sektortr = v; break
        if not sektor:
            try:
                df_s = tum_sirketler()
                if df_kontrol(df_s):
                    sym_c = df_s.columns[0]
                    for c in df_s.columns:
                        if any(k in str(c).lower() for k in ("kod","sembol","symbol","ticker")):
                            sym_c = c; break
                    esle = df_s[df_s[sym_c].astype(str).str.upper() == sembol.upper()]
                    if not esle.empty:
                        for c in df_s.columns:
                            cn = str(c).lower()
                            v  = str(esle[c].iloc[0]).strip()
                            if v and v not in ("nan","None","") and \
                               any(k in cn for k in ("sektor","sector","faaliyet")) and \
                               "alt" not in cn:
                                sektor = v; break
                        for c in df_s.columns:
                            cn = str(c).lower()
                            v  = str(esle[c].iloc[0]).strip()
                            if v and v not in ("nan","None","") and \
                               ("alt" in cn or "industry" in cn):
                                sektortr = v; break
                        # Fallback: kolon sırası (genellikle 2. ve 3. kolon)
                        if not sektor and len(esle.columns) > 2:
                            for ci in range(2, min(6, len(esle.columns))):
                                v = str(esle.iloc[0, ci]).strip()
                                if v and v not in ("nan","None",""):
                                    if not sektor:   sektor   = v
                                    elif not sektortr: sektortr = v; break
            except: pass

        def fmt(v):
            if v is None or (isinstance(v,float) and v!=v): return "—"
            try: return round(float(v),2)
            except: return str(v) if v else "—"

        return {
            "--- DEĞERLEME ---"              : "",
            "Güncel Fiyat (TRY)"             : sayi_kisalt(fiyat) if fiyat else "—",
            "Fiyat/Kazanç (F/K)"             : fmt(fk),
            "Fiyat/Defter (F/DD)"            : fmt(pd_dd),
            "Firma Değeri/FAVÖK (FD/FAVÖK)"  : fmt(fd_favok),
            "Serbest NCF Verimi (%)"         : fmt(scf_ver),
            "Temettü Verimi (%)"             : fmt(temkarvr),
            "--- KARLILIK ---"               : "",
            "Özkaynak Kârlılığı (ÖKO %)"    : fmt(roe),
            "Aktif Kârlılığı (AKO %)"        : fmt(roa),
            "Net Kâr Marjı (%)"             : fmt(nm),
            "FAVÖK Marjı (%)"               : fmt(em),
            "Brüt Kâr Marjı (%)"            : fmt(bm),
            "--- FİNANSAL YAPI ---"          : "",
            "Borç/Özkaynak Oranı"            : fmt(borcoz),
            "Cari Oran"                      : fmt(cario),
            "Net Borç (TRY)"                 : sayi_kisalt(net_borc) if net_borc else "—",
            "Firma Değeri (TRY)"             : sayi_kisalt(firma_d)  if firma_d  else "—",
            "--- PİYASA ---"                 : "",
            "Piyasa Değeri (TRY)"            : sayi_kisalt(pd_deger) if pd_deger else "—",
            "52H Yüksek (TRY)"              : fmt(fi_yuk),
            "52H Düşük (TRY)"               : fmt(fi_dus),
            "Sektör"                         : sektor   or "—",
            "Alt Sektör"                     : sektortr or "—",
            "--- GETİRİLER ---"              : "",
            "1 Aylık Getiri (%)"             : fmt(r1m),
            "3 Aylık Getiri (%)"             : fmt(r3m),
            "1 Yıllık Getiri (%)"            : fmt(r1y),
        }

    @staticmethod
    def yazdir(sembol: str, rasyo: dict):
        if not rasyo: console.print("  [yellow]Veri alınamadı.[/yellow]"); return
        t = Table(title=f"Temel Analiz — {sembol}",
                  box=box.ROUNDED, border_style="magenta",
                  show_lines=True, show_header=True)
        t.add_column("Rasyo", style="bold", min_width=34)
        t.add_column("Değer", justify="right", min_width=18)
        for k, v in rasyo.items():
            if k.startswith("---"):
                t.add_row(f"[bold yellow]  {k.strip('- ')}[/bold yellow]", "[dim]──[/dim]")
                continue
            v_str = str(v)
            try:
                f = float(str(v).replace("—","").strip())
                kl = k.lower()
                if any(x in kl for x in ("f/k","f/dd","fd/","borc","oran")):
                    rk = "green" if f < 15 else ("yellow" if f < 30 else "red")
                elif any(x in kl for x in ("marj","karlil","getiri","verim")):
                    rk = "green" if f > 0 else "red"
                else: rk = "white"
                v_str = f"[{rk}]{v}[/{rk}]"
            except: pass
            t.add_row(k, v_str)
        console.print(t)
        console.print("  [dim]NOT: Değerler borsapy verilerine dayanır; "
                      "resmi finansal tablo yerine geçmez.[/dim]")

    @staticmethod
    def sektor_karsilastir(sembol: str, sektor_listesi: list = None) -> pd.DataFrame:
        """
        Hisseyi sektördeki diğer hisselerle fast_info bazında karşılaştırır.
        Hızlı çalışması için yalnızca fast_info ve info kullanır.
        """
        if sektor_listesi is None:
            sektor_listesi = TemelAnalizci.BIST30
        semboller = [sembol.upper()] + [s for s in sektor_listesi
                                         if s.upper() != sembol.upper()]
        console.print(f"  [dim]{len(semboller)} hisse için veri çekiliyor...[/dim]")

        def _fi(fi_obj, k):
            try: return safe_float(fi_obj[k])
            except: return None
        def _ig(d, k):
            if not isinstance(d, dict): return None
            v = d.get(k)
            if v is None: return None
            try:
                f = float(str(v).replace(",",".")); return None if f!=f else f
            except: return None
        def _pct(v):
            if v is None: return "—"
            p = v*100 if abs(v)<2 else v
            return round(p,2)

        satirlar = []
        for s in semboller:
            satir = {"Sembol": s}
            try:
                hh  = Hisse(s)
                fi  = hh._t.fast_info
                fk   = _fi(fi,"pe_ratio")
                pddd = _fi(fi,"pb_ratio")
                fp   = _fi(fi,"last_price")
                mc   = _fi(fi,"market_cap")
                satir["F/K"]             = round(fk,  2) if fk   and 0<fk<500  else "—"
                satir["F/DD"]            = round(pddd, 2) if pddd and pddd>0    else "—"
                satir["Fiyat"]           = round(fp,   2) if fp               else "—"
                satir["Piy.Değeri"]      = sayi_kisalt(mc)if mc               else "—"
                # info
                try:
                    inf2 = hh.detayli_bilgi() or {}
                    satir["ÖKO %"] = _pct(_ig(inf2,"roe"))
                    satir["Net Marj %"] = _pct(_ig(inf2,"netMargin"))
                    dy = _ig(inf2,"dividendYield")
                    satir["Temettü %"] = round(dy*100 if dy and dy<1 else (dy or 0), 2)
                    de = _ig(inf2,"debtToEquity")
                    satir["Borç/Özk"] = round(de/100,2) if de and de>10 else (round(de,2) if de else "—")
                except:
                    for k in ["ÖKO %","Net Marj %","Temettü %","Borç/Özk"]:
                        satir.setdefault(k,"—")
            except:
                for k in ["F/K","F/DD","Fiyat","Piy.Değeri","ÖKO %","Net Marj %","Temettü %","Borç/Özk"]:
                    satir[k] = "—"
            satirlar.append(satir)

        if not satirlar: return pd.DataFrame()
        return pd.DataFrame(satirlar).set_index("Sembol")


# ═══════════════════════════════════════════════════════════════════
#  KORELASYON ANALİZİ
# ═══════════════════════════════════════════════════════════════════

class KorelasyonAnaliz:
    """
    Farklı enstrümanlar arasında günlük getiri korelasyonu.
    Tüm borsapy kaynaklarından dinamik enstrüman seçimi desteklenir.
    """

    @staticmethod
    def enstruman_sec() -> list:
        """
        Kullanıcıdan interaktif enstrüman listesi oluşturur.
        Dönüş: [(FinansalEnstruman, etiket), ...]
        """
        _panel(
            "  Enstrüman türünü ve sembolünü girin.\n"
            "  Boş bırakıp Enter → listeyi tamamla\n\n"
            "  Tür kısaltmaları:\n"
            "    [cyan]H[/cyan] = Hisse  [cyan]D[/cyan] = Döviz  [cyan]K[/cyan] = Kripto\n"
            "    [cyan]E[/cyan] = Emtia  [cyan]I[/cyan] = Endeks",
            "ENSTRÜMAN SEÇ", "blue")

        liste = []
        TUR_MAP = {
            "H": ("Hisse",  lambda s: Hisse(s)),
            "D": ("Döviz",  lambda s: Doviz(s)),
            "K": ("Kripto", lambda s: Kripto(s)),
            "E": ("Emtia",  lambda s: Emtia(s)),
            "I": ("Endeks", lambda s: Endeks(s)),
        }

        while True:
            tur = input(f"  Tür (H/D/K/E/I) [{len(liste)} eklendi — boş=bitir]: ").strip().upper()
            if not tur: break
            if tur not in TUR_MAP:
                console.print("  [red]H/D/K/E/I giriniz.[/red]"); continue

            tur_adi, nesne_fn = TUR_MAP[tur]
            sembol = input(f"  {tur_adi} sembolü: ").strip().upper()
            if not sembol: continue

            etiket = input(f"  Etiket [{sembol}]: ").strip() or sembol
            try:
                nesne = nesne_fn(sembol)
                liste.append((nesne, etiket))
                console.print(f"  [green]✓[/green] {tur_adi}: {sembol} ({etiket})")
            except Exception as e:
                console.print(f"  [red]Hata: {e}[/red]")

        return liste

    @staticmethod
    def hesapla(enstrumanlar: list, period="6ay") -> pd.DataFrame:
        """Günlük getiri korelasyon matrisi. Dönüş: DataFrame (n×n)."""
        veri = {}
        for nesne, etiket in enstrumanlar:
            try:
                df = nesne.gecmis_veri(period=period)
                if df_kontrol(df) and "Close" in df.columns:
                    veri[etiket] = df["Close"].pct_change().dropna()
            except Exception as e:
                console.print(f"  [yellow]{etiket}: {e}[/yellow]")
        if len(veri) < 2: return pd.DataFrame()
        combined = pd.DataFrame(veri).dropna()
        if len(combined) < 10: return pd.DataFrame()
        return combined.corr()

    @staticmethod
    def tablo_yazdir(corr: pd.DataFrame, baslik="Korelasyon Matrisi"):
        """Rich tablo olarak korelasyon matrisi."""
        t = Table(title=baslik, box=box.ROUNDED,
                  border_style="blue", show_lines=True)
        t.add_column("", style="bold", min_width=14)
        for col in corr.columns: t.add_column(str(col), justify="right", min_width=8)
        for idx in corr.index:
            row = [str(idx)]
            for col in corr.columns:
                v = corr.loc[idx, col]
                try:
                    f = float(v)
                    if idx == col:
                        row.append("[dim]1.00[/dim]")
                    elif f >= 0.7:
                        row.append(f"[bold green]{f:+.2f}[/bold green]")
                    elif f >= 0.3:
                        row.append(f"[green]{f:+.2f}[/green]")
                    elif f <= -0.7:
                        row.append(f"[bold red]{f:+.2f}[/bold red]")
                    elif f <= -0.3:
                        row.append(f"[red]{f:+.2f}[/red]")
                    else:
                        row.append(f"[yellow]{f:+.2f}[/yellow]")
                except: row.append("—")
            t.add_row(*row)
        console.print(t)
        console.print("\n  [dim]≥0.70[/dim] [bold green]Güçlü Pozitif[/bold green]  "
                      "  0.30-0.70 [green]Zayıf Pozitif[/green]  "
                      "  ±0.30 [yellow]Bağımsız[/yellow]  "
                      "  ≤-0.30 [red]Negatif[/red]  "
                      "  ≤-0.70 [bold red]Güçlü Negatif[/bold red]")

    @staticmethod
    def isi_haritasi(corr: pd.DataFrame, baslik="Korelasyon Isı Haritası"):
        """Matplotlib ısı haritası."""
        if not df_kontrol(corr): return
        n   = len(corr)
        fig, ax = plt.subplots(figsize=(max(6,n+2), max(5,n+1)))
        fig.patch.set_facecolor(_BG); ax.set_facecolor(_BG2)
        fig.suptitle(baslik, fontsize=13, color=C["line"], fontweight="bold")
        im = ax.imshow(corr.values, cmap="RdYlGn", vmin=-1, vmax=1, aspect="auto")
        ax.set_xticks(range(n)); ax.set_yticks(range(n))
        ax.set_xticklabels(corr.columns, rotation=45, ha="right", fontsize=9)
        ax.set_yticklabels(corr.index, fontsize=9)
        for i in range(n):
            for j in range(n):
                v = corr.values[i,j]
                try:
                    ax.text(j,i,f"{v:.2f}", ha="center", va="center",
                            fontsize=8, fontweight="bold",
                            color="black" if abs(v) > 0.4 else "white")
                except: pass
        plt.colorbar(im, ax=ax, label="Korelasyon Katsayısı")
        plt.tight_layout(); plt.show()


# ═══════════════════════════════════════════════════════════════════
#  BACKTEST
# ═══════════════════════════════════════════════════════════════════

class Backtest:
    """
    Kural tabanlı backtest motoru.
    Stratejiler: sma_cross | rsi_bands | macd_cross
    Minimum: 26 bar (MACD için)
    """

    @staticmethod
    def calistir(df: pd.DataFrame, strateji="sma_cross",
                 sermaye=100_000.0, **kw) -> dict:
        if not df_kontrol(df) or "Close" not in df.columns or len(df) < 26:
            return {}
        c   = df["Close"].values.astype(float)
        poz = 0.0; cap = sermaye; cap_s = [cap]
        islemler = []; maks = cap; dd = 0.0
        sin = np.zeros(len(df))
        try:
            if strateji == "sma_cross":
                h, y = kw.get("hizli",20), kw.get("yavas",50)
                sh = TeknikAnalizci.sma(df,h).values
                sy = TeknikAnalizci.sma(df,y).values
                with np.errstate(invalid="ignore"):
                    sin[sh>sy]=1; sin[sh<sy]=-1
            elif strateji == "rsi_bands":
                alt,ust = kw.get("alt",30), kw.get("ust",70)
                rsi = TeknikAnalizci.rsi(df).values
                with np.errstate(invalid="ignore"):
                    sin[rsi<alt]=1; sin[rsi>ust]=-1
            elif strateji == "macd_cross":
                md = TeknikAnalizci.macd(df)
                mv,sv = md["macd"].values, md["sinyal"].values
                with np.errstate(invalid="ignore"):
                    sin[mv>sv]=1; sin[mv<sv]=-1
        except: pass

        for i in range(1, len(df)):
            if sin[i]==1  and poz==0 and cap>0:
                poz=cap/(c[i]*1.001); cap=0.0; islemler.append(("AL",i,c[i]))
            elif sin[i]==-1 and poz>0:
                cap=poz*c[i]*0.999;  poz=0.0; islemler.append(("SAT",i,c[i]))
            deger = cap + (poz*c[i] if poz>0 else 0)
            cap_s.append(deger)
            maks = max(maks,deger)
            dd   = max(dd, (maks-deger)/maks*100 if maks>0 else 0)

        if poz>0: cap=poz*c[-1]
        toplam = (cap-sermaye)/sermaye*100
        yil    = max(len(df)/252, 1/252)
        cagr   = ((cap/sermaye)**(1/yil)-1)*100
        satis  = [(islemler[i],islemler[i-1])
                  for i in range(1,len(islemler),2) if islemler[i][0]=="SAT"]
        kaz    = sum(1 for s,a in satis if s[2]>a[2])
        oran   = kaz/len(satis)*100 if satis else 0

        return {
            "Veri"         : f"{len(df)} bar",
            "Başlangıç"    : f"{sayi_kisalt(sermaye)} TRY",
            "Son Değer"    : f"{sayi_kisalt(cap)} TRY",
            "Toplam Getiri": f"{toplam:+.2f}%",
            "CAGR"         : f"{cagr:+.2f}%",
            "Max Drawdown" : f"{dd:.2f}%",
            "İşlem Sayısı" : len(satis),
            "Kazanç Oranı" : f"{oran:.1f}%",
            "_cap_s": cap_s, "_islemler": islemler, "_idx": df.index.tolist(),
        }

    @staticmethod
    def grafik(sonuc: dict, sembol=""):
        if not sonuc or "_cap_s" not in sonuc: return
        seri = sonuc["_cap_s"]
        fig,ax = plt.subplots(figsize=(14,5))
        fig.patch.set_facecolor(_BG); ax.set_facecolor(_BG2)
        fig.suptitle(f"Backtest — {sembol}",fontsize=13,color=C["line"],fontweight="bold")
        ax.plot(range(len(seri)),seri,color=C["line"],lw=1.8,label="Portföy Değeri")
        ax.fill_between(range(len(seri)),seri,alpha=0.1,color=C["line"])
        for isl in sonuc["_islemler"]:
            try:
                pos=isl[1]
                if pos<len(seri):
                    rk=C["buy"] if isl[0]=="AL" else C["sell"]
                    mk="^" if isl[0]=="AL" else "v"
                    ax.scatter(pos,seri[pos],color=rk,s=70,zorder=5,marker=mk)
            except: pass
        ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x,_:sayi_kisalt(x)))
        ax.legend(fontsize=9,facecolor=_BG2); ax.grid(True,alpha=0.3)
        plt.tight_layout(); plt.show()


# ═══════════════════════════════════════════════════════════════════
#  TARAMA
# ═══════════════════════════════════════════════════════════════════

class Tarama:
    """BIST hisselerinde teknik koşul bazlı tarama."""

    KOSULLAR = {
        "1" : "RSI < 30  (Aşırı Satış)",
        "2" : "RSI > 70  (Aşırı Alış)",
        "3" : "Altın Kesişme: SMA20 > SMA50",
        "4" : "Ölüm Kesişmesi: SMA20 < SMA50",
        "5" : "MACD Pozitif Histogram",
        "6" : "Bollinger Alt Bandına Yakın",
        "7" : "52H Zirvesine Yakın (>%95)",
        "8" : "Hacim Patlaması (2× Ort.20g)",
        "9" : "CCI > 100  (Trend Gücü)",
        "10": "Williams %R < -80  (Aşırı Satış)",
    }

    @staticmethod
    def tara(semboller: list, kosul: str, period="3ay") -> pd.DataFrame:
        sonuclar = []
        for i, sembol in enumerate(semboller):
            try:
                df = Hisse(sembol).gecmis_veri(period=period)
                if not df_kontrol(df) or len(df) < 30: continue
                gecti = False; deger = None; aciklama = ""

                if kosul=="1":
                    r=TeknikAnalizci.rsi(df).iloc[-1]
                    if r<30: gecti=True; deger=round(r,2); aciklama=f"RSI={deger}"
                elif kosul=="2":
                    r=TeknikAnalizci.rsi(df).iloc[-1]
                    if r>70: gecti=True; deger=round(r,2); aciklama=f"RSI={deger}"
                elif kosul=="3":
                    s20=TeknikAnalizci.sma(df,20).iloc[-1]; s50=TeknikAnalizci.sma(df,50).iloc[-1]
                    if s20>s50: gecti=True; deger=round(s20-s50,2); aciklama=f"SMA20={s20:.2f} SMA50={s50:.2f}"
                elif kosul=="4":
                    s20=TeknikAnalizci.sma(df,20).iloc[-1]; s50=TeknikAnalizci.sma(df,50).iloc[-1]
                    if s20<s50: gecti=True; deger=round(s20-s50,2); aciklama=f"SMA20={s20:.2f} SMA50={s50:.2f}"
                elif kosul=="5":
                    hv=TeknikAnalizci.macd(df)["hist"].iloc[-1]
                    if hv>0: gecti=True; deger=round(hv,4); aciklama=f"Hist={deger}"
                elif kosul=="6":
                    bb=TeknikAnalizci.bollinger(df); alt=bb["alt"].iloc[-1]; cv=df["Close"].iloc[-1]
                    if cv<alt*1.01: gecti=True; deger=round(cv,2); aciklama=f"Close={cv:.2f} BB_alt={alt:.2f}"
                elif kosul=="7":
                    yuk=df["High"].max(); cv=df["Close"].iloc[-1]
                    if cv>yuk*0.95: gecti=True; deger=round(cv/yuk*100,1); aciklama=f"%{deger}"
                elif kosul=="8":
                    if "Volume" in df.columns:
                        ort=df["Volume"].rolling(20).mean().iloc[-1]; son=df["Volume"].iloc[-1]
                        if son>2*ort: gecti=True; deger=round(son/ort,2); aciklama=f"{deger}× ort"
                elif kosul=="9":
                    cv=TeknikAnalizci.cci(df).iloc[-1]
                    if cv>100: gecti=True; deger=round(cv,2); aciklama=f"CCI={deger}"
                elif kosul=="10":
                    wv=TeknikAnalizci.williams_r(df).iloc[-1]
                    if wv<-80: gecti=True; deger=round(wv,2); aciklama=f"W%R={deger}"

                if gecti:
                    sonuclar.append({"Sembol":sembol,"Değer":deger,"Açıklama":aciklama})
            except: pass
            if (i+1)%15==0 or i==len(semboller)-1:
                console.print(f"  [dim]{i+1}/{len(semboller)}[/dim]", end="\r")
        console.print()
        return pd.DataFrame(sonuclar) if sonuclar else pd.DataFrame()


# ═══════════════════════════════════════════════════════════════════
#  MENÜ FONKSİYONLARI
# ═══════════════════════════════════════════════════════════════════

def _emtia_tur_sec() -> tuple:
    for k,(ad,s) in Emtia.TURLER.items():
        console.print(f"  [cyan]{k:>2}[/cyan]  {ad}  [dim]({s})[/dim]")
    no = secim_al(list(Emtia.TURLER.keys()), "Tür no")
    return Emtia.TURLER[no]


# ── HİSSE ────────────────────────────────────────────────────────────────────

def menu_hisse():
    while True:
        _panel(
            "   [cyan]1[/cyan]  Hızlı bilgi\n"
            "   [cyan]2[/cyan]  Detaylı şirket bilgisi\n"
            "   [cyan]3[/cyan]  Fiyat geçmişi\n"
            "   [cyan]4[/cyan]  Tarih aralığında fiyat\n"
            "   [cyan]5[/cyan]  Grafik & Teknik Analiz\n"
            "   [cyan]6[/cyan]  Backtest\n"
            "  [bold cyan]── TEMEL ANALİZ ─────────────────────────[/bold cyan]\n"
            "   [cyan]7[/cyan]  Temel analiz rasyoları\n"
            "   [cyan]8[/cyan]  Sektör karşılaştırması\n"
            "  [bold cyan]── FİNANSAL TABLOLAR ──────────────────────[/bold cyan]\n"
            "   [cyan]9[/cyan]  Gelir tablosu\n"
            "  [cyan]10[/cyan]  Bilanço\n"
            "  [cyan]11[/cyan]  Nakit akış\n"
            "  [cyan]12[/cyan]  Son 12 ay (TTM) gelir\n"
            "  [cyan]13[/cyan]  Temettü / Sermaye artırımı\n"
            "  [bold cyan]── KURUMSAL & ANALİST ─────────────────────[/bold cyan]\n"
            "  [cyan]14[/cyan]  Ana ortaklar\n"
            "  [cyan]15[/cyan]  ETF sahipleri\n"
            "  [cyan]16[/cyan]  Analist hedef fiyat\n"
            "  [cyan]17[/cyan]  Analist tavsiyeler\n"
            "  [cyan]18[/cyan]  Tavsiye özeti\n"
            "  [cyan]19[/cyan]  KAP haberleri\n"
            "  [cyan]20[/cyan]  Takvim / Kazanç tarihleri\n"
            "  [cyan]21[/cyan]  ISIN kodu\n"
            "  [bold cyan]── GENEL ──────────────────────────────────[/bold cyan]\n"
            "  [cyan]22[/cyan]  Şirket arama\n"
            "  [cyan]23[/cyan]  Tüm BIST şirketleri\n"
            "  [cyan]24[/cyan]  Çoklu hisse indir\n"
            "  [cyan]25[/cyan]  Getiri karşılaştırma grafiği\n"
            "   [red]0[/red]   Ana Menü",
            "HİSSE SENEDİ", "cyan")

        secim = input("  Seçiminiz: ").strip()
        if secim == "0": break
        try:
            SEMBOL = {str(i) for i in range(1,26)} - {"22","23","24","25"}
            if secim in SEMBOL:
                kod = input("  Hisse kodu (örn. THYAO): ").strip().upper()

            if secim == "1":
                console.print(dict_to_rich(Hisse(kod).hizli_bilgi(), f"Hızlı Bilgi — {kod}"))

            elif secim == "2":
                h = Hisse(kod); bilgi = h.detayli_bilgi()
                if not bilgi:
                    console.print("  [yellow]info boş — fast_info gösteriliyor.[/yellow]")
                    console.print(dict_to_rich(h.hizli_bilgi(), f"Hızlı Bilgi — {kod}"))
                else:
                    ONCEL = ["last","previousClose","marketCap","trailingPE","forwardPE",
                             "priceToBook","dividendYield","roe","roa","netMargin",
                             "ebitdaMargin","grossMargin","debtToEquity","currentRatio",
                             "sector","industry","city","country","website",
                             "fullTimeEmployees","longBusinessSummary",
                             "return_1m","return_3m","return_6m","return_1y","return_ytd"]
                    temel = {k:bilgi[k] for k in ONCEL if k in bilgi}
                    kalan = {k:v for k,v in bilgi.items() if k not in temel}
                    if temel:
                        console.print(dict_to_rich(temel, f"Detaylı — {kod} (Temel)", renk="cyan"))
                    else:
                        console.print(dict_to_rich(bilgi, f"Detaylı — {kod}", renk="cyan"))
                        kalan = {}
                    if kalan and input("  Diğer alanları göster? (e/h): ").lower()=="e":
                        console.print(dict_to_rich(kalan, f"{kod} — Diğer", renk="blue"))

            elif secim == "3":
                h = Hisse(kod); period=period_sec(); interval=interval_sec()
                df=h.gecmis_veri(period=period, interval=interval)
                if df_kontrol(df):
                    console.print(df_to_rich(df.tail(30),
                        f"Fiyat Geçmişi — {kod} ({period}/{interval})",
                        kisalt=["Volume"]))
                else: console.print("  [red]Veri yok.[/red]")

            elif secim == "4":
                h=Hisse(kod)
                bas=input("  Başlangıç (YYYY-MM-DD): ").strip()
                bit=input("  Bitiş     (YYYY-MM-DD): ").strip()
                df=h.tarih_araliginda(bas,bit)
                if df_kontrol(df):
                    console.print(df_to_rich(df,
                        f"{kod} ({bas} → {bit})  [{len(df)} iş günü]",
                        kisalt=["Volume"]))
                else: console.print("  [red]Bu aralıkta veri yok.[/red]")

            elif secim == "5":
                h=Hisse(kod); period=period_sec()
                df=h.gecmis_veri(period=period)
                GrafikEkrani.ciz(df, sembol=kod, goster=GrafikEkrani.panel_sec())

            elif secim == "6":
                h=Hisse(kod); period=period_sec()
                df=h.gecmis_veri(period=period)
                if not df_kontrol(df):
                    console.print("  [red]Veri alınamadı.[/red]")
                else:
                    _panel("  [cyan]1[/cyan] SMA Kesişmesi\n"
                           "  [cyan]2[/cyan] RSI Bantları\n"
                           "  [cyan]3[/cyan] MACD Kesişmesi","Strateji","magenta")
                    st={"1":"sma_cross","2":"rsi_bands","3":"macd_cross"}.get(
                        input("  Strateji: ").strip(),"sma_cross")
                    sg=input("  Sermaye [100000 TRY]: ").strip()
                    sonuc=Backtest.calistir(df,strateji=st,sermaye=float(sg) if sg else 100_000)
                    if sonuc:
                        console.print(dict_to_rich(
                            {k:v for k,v in sonuc.items() if not k.startswith("_")},
                            f"Backtest — {kod}",renk="magenta"))
                        if input("  Grafik? (e/h): ").lower()=="e":
                            Backtest.grafik(sonuc,sembol=kod)
                    else: console.print("  [red]Yeterli veri yok (min 26 bar).[/red]")

            elif secim == "7":
                console.print(f"  [dim]Temel analiz yükleniyor: {kod}...[/dim]")
                TemelAnalizci.yazdir(kod, TemelAnalizci.hesapla(kod))

            elif secim == "8":
                console.print("  [cyan]1[/cyan] BIST30  [cyan]2[/cyan] Manuel liste  "
                              "[cyan]3[/cyan] Aynı sektör (otomatik)")
                alt=input("  Seçim (1/2/3): ").strip()
                if alt=="2":
                    girdi2=input("  Semboller (virgülle): ")
                    liste=[s.strip().upper() for s in girdi2.split(",") if s.strip()]
                elif alt=="3":
                    try:
                        inf2=Hisse(kod).detayli_bilgi() or {}
                        sek=inf2.get("sector","") or ""
                        if sek:
                            df_s=tum_sirketler()
                            if df_kontrol(df_s):
                                sek_c=next((c for c in df_s.columns
                                            if any(k in str(c).lower() for k in ("sektor","sector"))),None)
                                if sek_c:
                                    filtre=df_s[df_s[sek_c].astype(str).str.contains(sek,case=False,na=False)]
                                    liste=filtre.iloc[:,0].dropna().tolist()[:30]
                                else: liste=TemelAnalizci.BIST30
                            else: liste=TemelAnalizci.BIST30
                        else: liste=TemelAnalizci.BIST30
                    except: liste=TemelAnalizci.BIST30
                else: liste=TemelAnalizci.BIST30

                df_k=TemelAnalizci.sektor_karsilastir(kod, liste)
                if df_kontrol(df_k):
                    console.print(df_to_rich(df_k, f"Sektör Karşılaştırması — {kod}",
                                             renk="cyan", max_satir=35))
                else: console.print("  [yellow]Veri alınamadı.[/yellow]")

            elif secim in ("9","10","11","12"):
                h=Hisse(kod); ceyrek=False
                if secim in ("9","10","11"):
                    ceyrek=input("  Çeyreklik? (e/h): ").lower()=="e"
                if   secim=="9":  df,bsl=h.gelir_tablosu(ceyrek),"Gelir Tablosu"
                elif secim=="10": df,bsl=h.bilanco(ceyrek),"Bilanço"
                elif secim=="11": df,bsl=h.nakit_akis(ceyrek),"Nakit Akış"
                else:             df,bsl=h.ttm_gelir(),"TTM Gelir"
                if df_kontrol(df):
                    console.print(df_to_rich(df,f"{bsl} — {kod}",kisalt=kisalt_sutunlar(df)))
                else: console.print("  [red]Veri yok.[/red]")

            elif secim == "13":
                h=Hisse(kod)
                for fn,bsl in [(h.temettu,"Temettü"),(h.sermaye_artirimi,"Sermaye Artırımı")]:
                    try:
                        df=fn()
                        if df_kontrol(df):
                            console.print(df_to_rich(df.tail(20),
                                f"{bsl} — {kod}",kisalt=kisalt_sutunlar(df)))
                    except: pass

            elif secim == "14":
                df=Hisse(kod).ana_ortaklar()
                if df_kontrol(df): console.print(df_to_rich(df,f"Ana Ortaklar — {kod}"))

            elif secim == "15":
                df=Hisse(kod).etf_sahipleri()
                if df_kontrol(df): console.print(df_to_rich(df,f"ETF Sahipleri — {kod}"))
                else: console.print("  [yellow]ETF verisi yok.[/yellow]")

            elif secim == "16":
                d=Hisse(kod).analist_hedef()
                if dict_kontrol(d): console.print(dict_to_rich(d,f"Analist Hedef — {kod}"))

            elif secim == "17":
                df=Hisse(kod).analist_tavsiye()
                if df_kontrol(df): console.print(df_to_rich(df,f"Tavsiyeler — {kod}"))

            elif secim == "18":
                df=Hisse(kod).tavsiye_ozet()
                if df_kontrol(df): console.print(df_to_rich(df,f"Tavsiye Özeti — {kod}"))

            elif secim == "19":
                h=Hisse(kod); haberler=h.kap_haberleri()
                if not haberler:
                    try: isin_kodu=h.isin()
                    except: isin_kodu="—"
                    console.print(Panel(
                        "[yellow]KAP haberi alınamadı.[/yellow]\n\n"
                        "kap.org.tr → şirket → member_id bulun\n"
                        "[cyan]https://www.kap.org.tr/tr/api/memberDisclosureList/<id>[/cyan]\n\n"
                        f"ISIN: [cyan]{isin_kodu}[/cyan]",
                        title="KAP Bildirimleri", border_style="yellow"))
                else:
                    t=Table(title=f"KAP — {kod} ({len(haberler)} bildirim)",
                            box=box.ROUNDED,border_style="cyan",show_lines=True)
                    t.add_column("Tarih",width=24); t.add_column("Başlık",overflow="fold")
                    t.add_column("Link",overflow="fold",min_width=15)
                    TK=("Tarih","tarih","date","publishedAt","time","datetime","timestamp")
                    BK=("Başlık","Baslik","baslik","title","summary","headline","subject")
                    LK=("Link","link","url","Url","URL","href")
                    for hbr in haberler[:30]:
                        if not isinstance(hbr,dict): t.add_row("—",str(hbr)[:160],""); continue
                        tv=next((str(hbr[k])[:24] for k in TK if k in hbr and hbr[k]),"")
                        bv=next((str(hbr[k])[:160] for k in BK if k in hbr and hbr[k]),"")
                        lv=next((str(hbr[k])[:80]  for k in LK if k in hbr and hbr[k]),"")
                        if not bv:
                            bv="  |  ".join(f"{k}={str(v)[:30]}" for k,v in hbr.items()
                                            if k!="_key")[:200]
                        t.add_row(tv,bv,lv)
                    console.print(t)

            elif secim == "20":
                h=Hisse(kod)
                hersey_bos=True
                try:
                    takvim=h.takvim()
                    if isinstance(takvim,dict):
                        temiz={k:v for k,v in takvim.items()
                               if v is not None and "NaT" not in str(v) and str(v) not in ("nan","None","")}
                        if temiz: console.print(dict_to_rich(temiz,f"Takvim — {kod}")); hersey_bos=False
                except: pass
                try:
                    kaz=h.kazanc_tarihleri()
                    if df_kontrol(kaz):
                        kaz2=kaz.dropna(how="all")
                        if not kaz2.empty:
                            console.print(df_to_rich(kaz2.head(10),f"Kazanç Tarihleri — {kod}")); hersey_bos=False
                except: pass
                if hersey_bos: console.print("  [yellow]Takvim verisi bu hisse için mevcut değil.[/yellow]")

            elif secim == "21":
                try: console.print(f"\n  ISIN: [bold green]{Hisse(kod).isin()}[/bold green]")
                except Exception as e: console.print(f"  [red]{e}[/red]")

            elif secim == "22":
                arama=input("  Şirket adı / sektör: ").strip()
                df=sirket_ara(arama)
                if df_kontrol(df): console.print(df_to_rich(df,f"Arama: '{arama}'",max_satir=50))
                else: console.print("  [yellow]Sonuç bulunamadı.[/yellow]")

            elif secim == "23":
                df=tum_sirketler()
                if df_kontrol(df):
                    toplam=len(df); sb=40; sayfa=0
                    console.print(f"\n  [green]Toplam {toplam} şirket[/green] ({sb}/sayfa)")
                    while True:
                        b=sayfa*sb; e=min(b+sb,toplam)
                        console.print(df_to_rich(df.iloc[b:e],
                            f"BIST Şirketleri [{b+1}–{e}/{toplam}]",max_satir=sb))
                        if e>=toplam: console.print("  [green]Son sayfa.[/green]"); break
                        if input(f"  Sonraki {sb}? (Enter=evet/h=dur): ").lower()=="h": break
                        sayfa+=1

            elif secim == "24":
                girdi=input("  Kodlar (THYAO,GARAN,AKBNK): ")
                semboller=[s.strip().upper() for s in girdi.split(",") if s.strip()]
                period=period_sec()
                df=coklu_hisse(semboller,period=period)
                if df_kontrol(df):
                    console.print(df_to_rich(df.tail(15),f"Çoklu: {semboller}",
                        kisalt=[c for c in df.columns if "Volume" in str(c)]))

            elif secim == "25":
                girdi=input("  Kodlar (THYAO,USD,BTCTRY,XU100 karıştırılabilir): ")
                kodlar=[k.strip().upper() for k in girdi.split(",") if k.strip()]
                period=period_sec()
                try: el=bp.indices()
                except: el=[]
                enstr=[]
                for k in kodlar:
                    if k in el:                              enstr.append((Endeks(k),f"{k}(Endeks)"))
                    elif k.endswith("TRY") and len(k)>=6:   enstr.append((Kripto(k), f"{k}(Kripto)"))
                    elif len(k)<=4 and k.isalpha():          enstr.append((Doviz(k),  f"{k}(Döviz)"))
                    else:                                    enstr.append((Hisse(k),  f"{k}(Hisse)"))
                GrafikEkrani.normalize_karsilastirma(enstr,period=period)

        except Exception as e:
            console.print(f"\n  [bold red]Hata:[/bold red] {e}")
        geri_don()


# ── DÖVİZ ────────────────────────────────────────────────────────────────────

def menu_doviz():
    while True:
        _panel(
            "  [cyan]1[/cyan]  Güncel kur\n"
            "  [cyan]2[/cyan]  Geçmiş veriler\n"
            "  [cyan]3[/cyan]  Grafik & Teknik Analiz\n"
            "  [cyan]4[/cyan]  Kurum geçmişi  [dim](banka kur geçmişi)[/dim]\n"
            "  [cyan]5[/cyan]  Getiri karşılaştırma\n"
            "  [red]0[/red]  Ana Menü\n\n"
            "  [dim]Örn: USD EUR GBP CHF JPY SAR CAD AUD CNY RUB NOK SEK[/dim]",
            "DÖVİZ (doviz.com)", "green")
        secim=input("  Seçiminiz: ").strip()
        if secim=="0": break
        try:
            if secim in ("1","2","3","4"):
                kod=input("  Para birimi: ").strip().upper(); d=Doviz(kod)
            if secim=="1":
                fiyat=safe_float(d.guncel_fiyat())
                console.print(f"\n  [bold green]1 {d.sembol} = {sayi_kisalt(fiyat)} TRY[/bold green]")
                d.ozet_yazdir()
            elif secim=="2":
                period=period_sec(); df=d.gecmis_veri(period)
                if df_kontrol(df):
                    console.print(df_to_rich(df.tail(30),f"{d.sembol} ({period})",renk="green"))
            elif secim=="3":
                period=period_sec(); df=d.gecmis_veri(period)
                GrafikEkrani.ciz(df,sembol=f"Döviz: {d.sembol}",goster=GrafikEkrani.panel_sec())
            elif secim=="4":
                console.print("  [dim]Örn: akbank, garanti-bbva, isbankasi, "
                              "ziraatbankasi, vakifbank, denizbank[/dim]")
                kurum=input("  Kurum adı: ").strip().lower()
                period=period_sec(); df=d.kurum_gecmisi(kurum,period)
                if df_kontrol(df):
                    console.print(df_to_rich(df.tail(30),f"{d.sembol} — {kurum}",renk="green"))
                else: console.print("  [red]Veri alınamadı.[/red]")
            elif secim=="5":
                girdi=input("  Para birimleri (USD,EUR,GBP): ")
                kodlar=[k.strip().upper() for k in girdi.split(",") if k.strip()]
                period=period_sec()
                GrafikEkrani.normalize_karsilastirma([(Doviz(k),k) for k in kodlar],period=period)
        except Exception as e: console.print(f"\n  [bold red]Hata:[/bold red] {e}")
        geri_don()


# ── EMTİA ────────────────────────────────────────────────────────────────────

def menu_emtia():
    while True:
        _panel(
            "  [cyan]1[/cyan]  Güncel fiyat\n"
            "  [cyan]2[/cyan]  Geçmiş veriler\n"
            "  [cyan]3[/cyan]  Grafik & Teknik Analiz\n"
            "  [cyan]4[/cyan]  Kurum geçmişi  [dim](kuyumcu / banka)[/dim]\n"
            "  [cyan]5[/cyan]  Getiri karşılaştırma\n"
            "  [cyan]6[/cyan]  Desteklenen kurumlar  [dim](bp.metal_institutions)[/dim]\n"
            "  [red]0[/red]  Ana Menü\n\n"
            "  [dim]1, 2, 3, 4 seçince emtia türü ayrıca sorulacak.[/dim]",
            "ALTIN / KIYMETLİ MADEN / EMTİA", "yellow")
        secim=input("  Seçiminiz: ").strip()
        if secim=="0": break
        try:
            if secim in ("1","2","3","4"):
                console.print(); tur_adi,tur_s=_emtia_tur_sec(); em=Emtia(tur_s)
            if secim=="1":
                fiyat=safe_float(em.guncel_fiyat())
                console.print(f"\n  [bold yellow]{tur_adi}: {sayi_kisalt(fiyat)} TRY[/bold yellow]")
                if tur_s in Emtia.KURUM_DESTEKLI:
                    try:
                        rates=em._fx.institution_rates
                        if df_kontrol(rates):
                            console.print(df_to_rich(rates,f"{tur_adi} — Kurum Fiyatları",
                                                     renk="yellow",max_satir=30))
                    except: pass
            elif secim=="2":
                period=period_sec(); df=em.gecmis_veri(period)
                if df_kontrol(df):
                    console.print(df_to_rich(df.tail(30),f"{tur_adi} ({period})",renk="yellow"))
                else: console.print("  [red]Veri alınamadı.[/red]")
            elif secim=="3":
                period=period_sec(); df=em.gecmis_veri(period)
                GrafikEkrani.ciz(df,sembol=tur_adi,goster=GrafikEkrani.panel_sec())
            elif secim=="4":
                console.print("  [dim]Kuyumcular (OHLC): kapalicarsi, harem, altinkaynak[/dim]")
                console.print("  [dim]Bankalar (Close):  akbank, garanti-bbva, isbankasi, "
                              "ziraatbankasi, vakifbank[/dim]")
                kurum=input("  Kurum adı: ").strip().lower()
                period=period_sec(); df=em.kurum_gecmisi(kurum,period)
                if df_kontrol(df):
                    console.print(df_to_rich(df.tail(30),f"{tur_adi} — {kurum}",renk="yellow"))
                else: console.print("  [red]Veri alınamadı.[/red]")
            elif secim=="5":
                period=period_sec()
                GrafikEkrani.normalize_karsilastirma(
                    [(Emtia(s),ad) for _,(ad,s) in Emtia.TURLER.items()],period=period)
            elif secim=="6":
                try:
                    kurumlar=bp.metal_institutions()
                    t=Table(title="Metal Kurumları",box=box.ROUNDED,border_style="yellow")
                    t.add_column("Kurum ID")
                    for k in kurumlar: t.add_row(str(k))
                    console.print(t)
                except Exception as e: console.print(f"  [red]{e}[/red]")
        except Exception as e: console.print(f"\n  [bold red]Hata:[/bold red] {e}")
        geri_don()


# ── KRİPTO ───────────────────────────────────────────────────────────────────

def menu_kripto():
    while True:
        _panel(
            "  [cyan]1[/cyan]  Güncel fiyat\n"
            "  [cyan]2[/cyan]  Geçmiş veriler\n"
            "  [cyan]3[/cyan]  Grafik & Teknik Analiz\n"
            "  [cyan]4[/cyan]  Tüm BtcTurk çiftleri\n"
            "  [cyan]5[/cyan]  Getiri karşılaştırma\n"
            "  [red]0[/red]  Ana Menü\n\n"
            "  [dim]Örn: BTCTRY ETHTRY BNBTRY XRPTRY SOLTRY AVEXTRY[/dim]",
            "KRİPTO PARA (BtcTurk)", "magenta")
        secim=input("  Seçiminiz: ").strip()
        if secim=="0": break
        try:
            if secim in ("1","2","3"):
                cift=input("  Kripto çifti (BTCTRY vb.): ").strip().upper(); k=Kripto(cift)
            if secim=="1":
                fiyat=safe_float(k.guncel_fiyat())
                console.print(f"\n  [bold magenta]{k.sembol}: {sayi_kisalt(fiyat)} TRY[/bold magenta]")
                k.ozet_yazdir()
            elif secim=="2":
                period=period_sec(); df=k.gecmis_veri(period)
                if df_kontrol(df):
                    console.print(df_to_rich(df.tail(30),f"{k.sembol} ({period})",
                                             renk="magenta",kisalt=["Volume"]))
            elif secim=="3":
                period=period_sec(); df=k.gecmis_veri(period)
                GrafikEkrani.ciz(df,sembol=k.sembol,goster=GrafikEkrani.panel_sec())
            elif secim=="4":
                ciftler=kripto_ciftleri()
                t=Table(title="BtcTurk Çiftleri",box=box.ROUNDED,border_style="magenta")
                t.add_column("Sembol")
                for c in ciftler: t.add_row(str(c))
                console.print(t)
            elif secim=="5":
                girdi=input("  Çiftler (BTCTRY,ETHTRY,SOLTRY): ")
                kodlar=[k.strip().upper() for k in girdi.split(",") if k.strip()]
                period=period_sec()
                GrafikEkrani.normalize_karsilastirma([(Kripto(k),k) for k in kodlar],period=period)
        except Exception as e: console.print(f"\n  [bold red]Hata:[/bold red] {e}")
        geri_don()


# ── YATIRIM FONU ─────────────────────────────────────────────────────────────

def menu_fon():
    while True:
        _panel(
            "  [cyan]1[/cyan]  Fon bilgisi\n"
            "  [cyan]2[/cyan]  Geçmiş veriler\n"
            "  [cyan]3[/cyan]  Performans\n"
            "  [cyan]4[/cyan]  Varlık dağılımı\n"
            "  [cyan]5[/cyan]  Dağılım geçmişi\n"
            "  [cyan]6[/cyan]  Fon arama\n"
            "  [red]0[/red]  Ana Menü",
            "YATIRIM FONU (TEFAS)", "blue")
        secim=input("  Seçiminiz: ").strip()
        if secim=="0": break
        try:
            if secim in ("1","2","3","4","5"):
                kod=input("  Fon kodu (örn. AAK TRE GAF): ").strip().upper(); f=YatirimFonu(kod)
            if secim=="1":
                bilgi=f.bilgi()
                if dict_kontrol(bilgi): console.print(dict_to_rich(bilgi,f"Fon — {kod}",renk="blue"))
            elif secim=="2":
                period=period_sec(); df=f.gecmis_veri(period)
                if df_kontrol(df): console.print(df_to_rich(df.tail(30),f"{kod} ({period})",renk="blue"))
            elif secim=="3":
                perf=f.performans()
                if dict_kontrol(perf): console.print(dict_to_rich(perf,f"Performans — {kod}",renk="blue"))
            elif secim=="4":
                df=f.dagilim()
                if df_kontrol(df): console.print(df_to_rich(df,f"Dağılım — {kod}",renk="blue"))
            elif secim=="5":
                period=period_sec(); df=f.dagilim_gecmis(period)
                if df_kontrol(df): console.print(df_to_rich(df,f"Dağılım Geçmişi — {kod}",renk="blue"))
            elif secim=="6":
                arama=input("  Arama terimi: ").strip()
                df=fon_ara(arama)
                if df_kontrol(df): console.print(df_to_rich(df.head(25),f"Fon Arama: '{arama}'",renk="blue"))
        except Exception as e: console.print(f"\n  [bold red]Hata:[/bold red] {e}")
        geri_don()


# ── ENDEKs ───────────────────────────────────────────────────────────────────

def menu_endeks():
    while True:
        _panel(
            "  [cyan]1[/cyan]  Popüler endeks listesi  [dim](33 endeks)[/dim]\n"
            "  [cyan]2[/cyan]  Tüm BIST endeksleri     [dim](79 endeks)[/dim]\n"
            "  [cyan]3[/cyan]  Endeks bilgisi\n"
            "  [cyan]4[/cyan]  Geçmiş veriler\n"
            "  [cyan]5[/cyan]  Grafik & Teknik Analiz\n"
            "  [cyan]6[/cyan]  Endeks bileşenleri\n"
            "  [cyan]7[/cyan]  Getiri karşılaştırma\n"
            "  [red]0[/red]  Ana Menü\n\n"
            "  [dim]Örn: XU100 XU030 XBANK XUSIN XGIDA XHOLD XTEKS[/dim]",
            "ENDEKs", "red")
        secim=input("  Seçiminiz: ").strip()
        if secim=="0": break
        try:
            if secim in ("3","4","5","6"):
                kod=input("  Endeks kodu: ").strip().upper(); e=Endeks(kod)
            if secim=="1":
                try:
                    el=bp.indices(detailed=True)
                    t=Table(title="BIST Popüler Endeksler",box=box.ROUNDED,border_style="red")
                    if el and isinstance(el[0],dict):
                        t.add_column("Sembol"); t.add_column("Ad"); t.add_column("Hisse",justify="right")
                        for en in el: t.add_row(str(en.get("symbol","")),str(en.get("name","")),str(en.get("count","")))
                    else:
                        t.add_column("Kod")
                        for en in el: t.add_row(str(en))
                    console.print(t)
                except Exception as e2: console.print(f"  [red]{e2}[/red]")
            elif secim=="2":
                try:
                    el=bp.all_indices()
                    t=Table(title=f"Tüm BIST Endeksleri ({len(el)})",box=box.ROUNDED,border_style="red")
                    if el and isinstance(el[0],dict):
                        t.add_column("Sembol"); t.add_column("Ad"); t.add_column("Hisse",justify="right")
                        for en in el: t.add_row(str(en.get("symbol","")),str(en.get("name","")),str(en.get("count","")))
                    else:
                        t.add_column("Kod")
                        for en in el: t.add_row(str(en))
                    console.print(t)
                except Exception as e2: console.print(f"  [red]{e2}[/red]")
            elif secim=="3":
                fiyat=e.guncel_fiyat(); bilgi=e.bilgi()
                console.print(f"\n  [bold red]{kod} — Güncel: {sayi_kisalt(fiyat)}[/bold red]")
                if isinstance(bilgi,dict) and bilgi:
                    console.print(dict_to_rich(bilgi,f"Endeks Bilgisi — {kod}",renk="red"))
            elif secim=="4":
                period=period_sec(); df=e.gecmis_veri(period)
                if df_kontrol(df):
                    console.print(df_to_rich(df.tail(30),f"{kod} ({period})",renk="red",kisalt=["Volume"]))
            elif secim=="5":
                period=period_sec(); df=e.gecmis_veri(period)
                GrafikEkrani.ciz(df,sembol=f"Endeks: {kod}",goster=GrafikEkrani.panel_sec())
            elif secim=="6":
                df=e.bilesenler()
                if df_kontrol(df): console.print(df_to_rich(df,f"Bileşenler — {kod}",renk="red"))
                else: console.print("  [yellow]Bileşen verisi alınamadı.[/yellow]")
            elif secim=="7":
                girdi=input("  Endeksler (XU100,XU030,XBANK): ")
                kodlar=[k.strip().upper() for k in girdi.split(",") if k.strip()]
                period=period_sec()
                GrafikEkrani.normalize_karsilastirma([(Endeks(k),k) for k in kodlar],period=period)
        except Exception as e: console.print(f"\n  [bold red]Hata:[/bold red] {e}")
        geri_don()


# ── ENFLASYON ────────────────────────────────────────────────────────────────

def menu_enflasyon():
    while True:
        _panel(
            "  [cyan]1[/cyan]  Son TÜFE verisi\n"
            "  [cyan]2[/cyan]  TÜFE geçmişi\n"
            "  [cyan]3[/cyan]  ÜFE geçmişi\n"
            "  [cyan]4[/cyan]  TÜFE grafiği\n"
            "  [cyan]5[/cyan]  ÜFE grafiği\n"
            "  [cyan]6[/cyan]  Enflasyon hesaplayıcı\n"
            "  [red]0[/red]  Ana Menü",
            "ENFLASYON (TCMB)", "yellow")
        secim=input("  Seçiminiz: ").strip()
        if secim=="0": break
        try:
            enf=Enflasyon()
            if secim=="1":
                d=enf.son_tufe()
                if dict_kontrol(d): console.print(dict_to_rich(d,"Son TÜFE",renk="yellow"))
            elif secim=="2":
                df=enf.tufe_gecmis()
                if df_kontrol(df): console.print(df_to_rich(df.tail(24),"TÜFE Geçmişi",renk="yellow"))
            elif secim=="3":
                df=enf.ufe_gecmis()
                if df_kontrol(df): console.print(df_to_rich(df.tail(24),"ÜFE Geçmişi",renk="yellow"))
            elif secim=="4": GrafikEkrani.enflasyon(enf.tufe_gecmis(),"Türkiye TÜFE")
            elif secim=="5": GrafikEkrani.enflasyon(enf.ufe_gecmis(),"Türkiye ÜFE")
            elif secim=="6":
                tutar=float(input("  Tutar (TRY): ").strip())
                bas=input("  Başlangıç (YYYY-MM): ").strip()
                bit=input("  Bitiş     (YYYY-MM): ").strip()
                sonuc=enf.hesapla(tutar,bas,bit)
                if dict_kontrol(sonuc):
                    console.print(dict_to_rich(sonuc,"Enflasyon Hesaplayıcı",renk="yellow"))
        except Exception as e: console.print(f"\n  [bold red]Hata:[/bold red] {e}")
        geri_don()


# ── VİOP ─────────────────────────────────────────────────────────────────────

def menu_viop():
    while True:
        _panel(
            "  [cyan]1[/cyan]  Tüm vadeli işlemler\n"
            "  [cyan]2[/cyan]  Tüm opsiyonlar\n"
            "  [cyan]3[/cyan]  Pay vadeli\n"
            "  [cyan]4[/cyan]  Endeks vadeli\n"
            "  [cyan]5[/cyan]  Döviz vadeli\n"
            "  [cyan]6[/cyan]  Emtia vadeli\n"
            "  [cyan]7[/cyan]  Pay opsiyonları\n"
            "  [cyan]8[/cyan]  Endeks opsiyonları\n"
            "  [cyan]9[/cyan]  Sembole göre ara\n"
            "  [red]0[/red]  Ana Menü",
            "VİOP (İş Yatırım)", "cyan")
        secim=input("  Seçiminiz: ").strip()
        if secim=="0": break
        try:
            v=VIOP()
            harita={
                "1":(v.futures,"Tüm Vadeli"),
                "2":(v.options,"Tüm Opsiyonlar"),
                "3":(v.stock_futures,"Pay Vadeli"),
                "4":(v.index_futures,"Endeks Vadeli"),
                "5":(v.currency_futures,"Döviz Vadeli"),
                "6":(v.commodity_futures,"Emtia Vadeli"),
                "7":(v.stock_options,"Pay Opsiyonları"),
                "8":(v.index_options,"Endeks Opsiyonları"),
            }
            if secim in harita:
                df,bsl=harita[secim]
                if df_kontrol(df): console.print(df_to_rich(df.head(40),bsl))
                else: console.print("  [yellow]Veri yok.[/yellow]")
            elif secim=="9":
                s=input("  Underlying sembol (THYAO, XU030 vb.): ").strip().upper()
                df=v.sembole_gore(s)
                if df_kontrol(df): console.print(df_to_rich(df,f"VİOP — {s}"))
        except Exception as e: console.print(f"\n  [bold red]Hata:[/bold red] {e}")
        geri_don()


# ── PORTFÖY ──────────────────────────────────────────────────────────────────

def menu_portfoy():
    portfoy=Portfoy()
    while True:
        _panel(
            "  [cyan]1[/cyan]  Hisse ekle\n"
            "  [cyan]2[/cyan]  Yatırım fonu ekle\n"
            "  [cyan]3[/cyan]  Emtia/Altın ekle\n"
            "  [cyan]4[/cyan]  Kripto ekle\n"
            "  [cyan]5[/cyan]  Döviz ekle\n"
            "  [cyan]6[/cyan]  Portföy durumu  [dim](güncel değer + PnL)[/dim]\n"
            "  [cyan]7[/cyan]  Lot sil\n"
            "  [cyan]8[/cyan]  bp.Portfolio holdings  [dim](hisse/fon)[/dim]\n"
            "  [cyan]9[/cyan]  Benchmark ayarla\n"
            "  [red]0[/red]  Ana Menü",
            f"PORTFÖY — {portfoy.ad}", "green")
        secim=input("  Seçiminiz: ").strip()
        if secim=="0": break
        try:
            if secim=="1":
                s=input("  Hisse kodu: ").strip().upper()
                a=float(input("  Adet: "))
                m=input("  Maliyet/adet TRY (boş=atla): ").strip()
                t=input("  Alım tarihi YYYY-MM-DD (boş=atla): ").strip()
                portfoy.ekle_hisse(s,a,maliyet=float(m) if m else None,tarih=t if t else None)
            elif secim=="2":
                k=input("  Fon kodu: ").strip().upper()
                a=float(input("  Adet: "))
                m=input("  Maliyet/adet TRY (boş=atla): ").strip()
                portfoy.ekle_fon(k,a,maliyet=float(m) if m else None)
            elif secim=="3":
                console.print("  [dim]Örn: gram-altin, ceyrek-altin, gram-gumus, ons-altin[/dim]")
                s=input("  Emtia sembolü: ").strip()
                a=float(input("  Miktar: "))
                m=input("  Maliyet/birim TRY (boş=atla): ").strip()
                portfoy.ekle_emtia(s,a,maliyet=float(m) if m else None)
            elif secim=="4":
                s=input("  Kripto çifti (BTCTRY vb.): ").strip().upper()
                a=float(input("  Miktar: "))
                m=input("  Maliyet/adet TRY (boş=atla): ").strip()
                portfoy.ekle_kripto(s,a,maliyet=float(m) if m else None)
            elif secim=="5":
                s=input("  Döviz kodu (USD EUR vb.): ").strip().upper()
                a=float(input("  Miktar: "))
                m=input("  Maliyet/birim TRY (boş=atla): ").strip()
                portfoy.ekle_doviz(s,a,maliyet=float(m) if m else None)
            elif secim=="6":
                portfoy.ozet()
            elif secim=="7":
                portfoy.ozet()
                n_str=input("\n  Silmek istediğiniz lot no (boş=iptal): ").strip()
                if n_str: portfoy.lot_sil(int(n_str))
            elif secim=="8":
                df=portfoy.bp_holdings()
                if df_kontrol(df):
                    kst=[c for c in df.columns if any(k in str(c).lower() for k in ("value","cost","pnl","weight"))]
                    console.print(df_to_rich(df,"bp.Portfolio Holdings",kisalt=kst))
                else: console.print("  [dim]bp.Portfolio boş (hisse/fon eklenmemiş).[/dim]")
            elif secim=="9":
                e=input("  Benchmark endeksi [XU100]: ").strip() or "XU100"
                portfoy.benchmark_ayarla(e)
        except Exception as e: console.print(f"\n  [bold red]Hata:[/bold red] {e}")
        geri_don()


# ── TARAMA & KORELASYON ──────────────────────────────────────────────────────

def menu_tarama():
    while True:
        kosul_satiri="\n".join(f"  [cyan]{k:>2}[/cyan]  {v}" for k,v in Tarama.KOSULLAR.items())
        _panel(
            kosul_satiri +
            "\n\n  [bold cyan]────────────────────────────────────────[/bold cyan]\n"
            "  [cyan]11[/cyan]  Korelasyon Analizi  [dim](hisse/döviz/kripto/emtia/endeks)[/dim]\n\n"
            "  [red]0[/red]  Ana Menü",
            "BIST TARAMA & KORELASYON ANALİZİ", "blue")
        secim=input("  Seçim: ").strip()
        if secim=="0": break
        if secim=="11":
            menu_korelasyon(); continue
        if secim not in Tarama.KOSULLAR:
            console.print("  [red]Geçersiz seçim.[/red]"); geri_don(); continue
        try:
            period=period_sec()
            _panel("  [cyan]1[/cyan] BIST30\n  [cyan]2[/cyan] BIST100\n  [cyan]3[/cyan] Manuel liste","Kapsam","blue")
            kaynak=input("  Kaynak (1/2/3): ").strip()
            if kaynak=="1":
                semboller=TemelAnalizci.BIST30
            elif kaynak=="2":
                df_s=tum_sirketler()
                if df_kontrol(df_s): semboller=df_s.iloc[:,0].dropna().tolist()[:100]
                else: semboller=TemelAnalizci.BIST30
            else:
                girdi=input("  Semboller (virgülle): ")
                semboller=[s.strip().upper() for s in girdi.split(",") if s.strip()]
            console.print(f"\n  [dim]Taranıyor: {len(semboller)} hisse...[/dim]")
            df_r=Tarama.tara(semboller,secim,period=period)
            if df_kontrol(df_r):
                console.print(df_to_rich(df_r,f"Tarama: {Tarama.KOSULLAR[secim]}",renk="blue"))
            else:
                console.print("  [yellow]Hiç hisse koşulu geçmedi.[/yellow]")
        except Exception as e: console.print(f"\n  [bold red]Hata:[/bold red] {e}")
        geri_don()


def menu_korelasyon():
    while True:
        _panel(
            "  [cyan]1[/cyan]  Özel enstrüman seçimi\n"
            "  [cyan]2[/cyan]  Hızlı: BIST30 (ilk 10 hisse)\n"
            "  [cyan]3[/cyan]  Hızlı: Kripto  [dim](BTC/ETH/SOL/BNB/XRP)[/dim]\n"
            "  [cyan]4[/cyan]  Hızlı: Emtia   [dim](Gram/Ons Altın, Gümüş)[/dim]\n"
            "  [cyan]5[/cyan]  Hızlı: Dövizler [dim](USD/EUR/GBP/CHF/JPY)[/dim]\n"
            "  [red]0[/red]  Geri",
            "KORELASYON ANALİZİ", "blue")
        secim=input("  Seçiminiz: ").strip()
        if secim=="0": break
        try:
            if secim=="1":
                enstr=KorelasyonAnaliz.enstruman_sec()
                if len(enstr)<2:
                    console.print("  [yellow]En az 2 enstrüman gerekli.[/yellow]")
                    geri_don(); continue
                period=period_sec()
                console.print("  [dim]Veri indiriliyor...[/dim]")
                corr=KorelasyonAnaliz.hesapla(enstr,period=period)
            elif secim=="2":
                period=period_sec()
                bist10=["THYAO","GARAN","AKBNK","ISCTR","YKBNK","EREGL","KCHOL","BIMAS","FROTO","TUPRS"]
                enstr=[(Hisse(s),s) for s in bist10]
                console.print("  [dim]BIST10 korelasyonu hesaplanıyor...[/dim]")
                corr=KorelasyonAnaliz.hesapla(enstr,period=period)
            elif secim=="3":
                period=period_sec()
                enstr=[(Kripto("BTCTRY"),"BTC"),(Kripto("ETHTRY"),"ETH"),
                       (Kripto("SOLTRY"),"SOL"),(Kripto("BNBTRY"),"BNB"),(Kripto("XRPTRY"),"XRP")]
                console.print("  [dim]Kripto korelasyonu hesaplanıyor...[/dim]")
                corr=KorelasyonAnaliz.hesapla(enstr,period=period)
            elif secim=="4":
                period=period_sec()
                enstr=[(Emtia("gram-altin"),"Gram Altın"),(Emtia("ons-altin"),"Ons Altın"),
                       (Emtia("gram-gumus"),"Gram Gümüş"),(Emtia("gram-platin"),"Gram Platin")]
                console.print("  [dim]Emtia korelasyonu hesaplanıyor...[/dim]")
                corr=KorelasyonAnaliz.hesapla(enstr,period=period)
            elif secim=="5":
                period=period_sec()
                enstr=[(Doviz("USD"),"USD"),(Doviz("EUR"),"EUR"),(Doviz("GBP"),"GBP"),
                       (Doviz("CHF"),"CHF"),(Doviz("JPY"),"JPY")]
                console.print("  [dim]Döviz korelasyonu hesaplanıyor...[/dim]")
                corr=KorelasyonAnaliz.hesapla(enstr,period=period)
            else:
                geri_don(); continue

            if df_kontrol(corr):
                baslik={"1":"Korelasyon Matrisi","2":"BIST10 Korelasyon",
                        "3":"Kripto Korelasyon","4":"Emtia Korelasyon",
                        "5":"Döviz Korelasyon"}.get(secim,"Korelasyon Matrisi")
                KorelasyonAnaliz.tablo_yazdir(corr, baslik)
                if input("\n  Isı haritası göster? (e/h): ").lower()=="e":
                    KorelasyonAnaliz.isi_haritasi(corr, baslik)
            else:
                console.print("  [red]Yeterli ortak veri bulunamadı.[/red]")
        except Exception as e: console.print(f"\n  [bold red]Hata:[/bold red] {e}")
        geri_don()


# ═══════════════════════════════════════════════════════════════════
#  ANA MENÜ
# ═══════════════════════════════════════════════════════════════════

def ana_menu():
    while True:
        temizle()
        _panel(
            "   [cyan]1[/cyan]  Hisse Senedi       [dim]bp.Ticker — Grafik, Temel Analiz, Backtest[/dim]\n"
            "   [cyan]2[/cyan]  Döviz              [dim]bp.FX (65+ kur, doviz.com)[/dim]\n"
            "   [cyan]3[/cyan]  Altın & Emtia      [dim]bp.FX (gram/ons altın, gümüş, platin)[/dim]\n"
            "   [cyan]4[/cyan]  Kripto Para        [dim]bp.Crypto (BtcTurk)[/dim]\n"
            "   [cyan]5[/cyan]  Yatırım Fonu       [dim]bp.Fund (TEFAS)[/dim]\n"
            "   [cyan]6[/cyan]  Endeks             [dim]bp.Index (79 BIST endeksi)[/dim]\n"
            "   [cyan]7[/cyan]  Enflasyon          [dim]bp.Inflation (TCMB)[/dim]\n"
            "   [cyan]8[/cyan]  VİOP               [dim]bp.VIOP (İş Yatırım)[/dim]\n"
            "   [cyan]9[/cyan]  Portföy            [dim]bp.Portfolio + çoklu lot izleme[/dim]\n"
            "  [cyan]10[/cyan]  Tarama & Korelasyon [dim]Teknik tarama + korelasyon analizi[/dim]\n"
            "   [red]0[/red]  Çıkış",
            "BORSA OTOMASYONU  ▸  borsapy OOP Terminali  v5.0", "cyan")

        secim=input("  Seçiminiz: ").strip()
        yonlendirme={
            "1":menu_hisse,  "2":menu_doviz,      "3":menu_emtia,
            "4":menu_kripto, "5":menu_fon,         "6":menu_endeks,
            "7":menu_enflasyon,"8":menu_viop,      "9":menu_portfoy,
            "10":menu_tarama,
        }
        if secim=="0":
            console.print("\n  [bold green]Görüşürüz![/bold green]\n"); break
        elif secim in yonlendirme:
            yonlendirme[secim]()
        else:
            console.print("  [red]Geçersiz seçim.[/red]")
            geri_don()


if __name__ == "__main__":
    ana_menu()