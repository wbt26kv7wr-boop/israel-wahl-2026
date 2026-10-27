"""Aktualisiert die Dashboard-Daten aus der Live-Karte der Wahlkommission (CEC).
Aufruf: python3 scripts/refresh.py   (schreibt nach data/)
Geometrie wird nur mit --geo neu erzeugt (braucht shapely und den Topojson-Cache).
"""
import csv, json, math, os, sys, urllib.request, io, datetime

BASE = "https://mapvotes.bechirot.gov.il/data/votes"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "data")
DL = os.path.join(ROOT, ".cache")
os.makedirs(OUT, exist_ok=True)
os.makedirs(DL, exist_ok=True)

def get(url, path):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36", "Accept": "application/json,text/plain,*/*", "Accept-Language": "he-IL,he;q=0.9,en;q=0.8", "Referer": "https://mapvotes.bechirot.gov.il/"})
    with urllib.request.urlopen(req, timeout=60) as r:
        data = r.read()
    open(path, "wb").write(data)
    return data

# ---------- 2022 results by locality ----------
p25 = os.path.join(DL, "expc25.csv")
if not os.path.exists(p25):
    get("https://media25.bechirot.gov.il/files/expc.csv", p25)
rows25 = list(csv.DictReader(io.open(p25, encoding="utf-8-sig")))
def n(v):
    try: return float(v)
    except: return 0.0
R22 = {}
elig_tot = vot_tot = 0
for r in rows25:
    code = int(n(r["סמל ישוב"]))
    e, v, k = n(r["בזב"]), n(r["מצביעים"]), n(r["כשרים"])
    elig_tot += e; vot_tot += v
    if e <= 0 or k <= 0: continue
    sh = lambda *ls: sum(n(r.get(l, 0)) for l in ls) / k * 100
    R22[code] = dict(name22=r["שם ישוב"].strip(), elig22=e, turnout22=round(v / e * 100, 1),
        likud=sh("מחל"), rz=sh("ט"), shas=sh("שס"), utj=sh("ג"), yesh=sh("פה"), nu=sh("כן"), yb=sh("ל"),
        labor=sh("אמת"), meretz=sh("מרצ"), raam=sh("עם"), hadash=sh("ום"), balad=sh("ד"))
NAT22 = round(vot_tot / elig_tot * 100, 2)

def camp_of(s):
    arab = s["raam"] + s["hadash"] + s["balad"]
    nb = s["likud"] + s["rz"] + s["shas"] + s["utj"]
    cb = s["yesh"] + s["nu"] + s["yb"] + s["labor"] + s["meretz"]
    if arab >= 50:
        return ("raam" if s["raam"] >= s["hadash"] + s["balad"] else "joint"), nb, cb, arab
    if s["shas"] + s["utj"] >= 40: return "haredi", nb, cb, arab
    if nb - cb >= 10: return "rechts", nb, cb, arab
    if cb - nb >= 10: return "mitte-links", nb, cb, arab
    return "swing", nb, cb, arab

# ---------- live turnout (municipal) ----------
live_raw = get(BASE + "/latest/municipal_data.json", os.path.join(DL, "municipal_live.json"))
live = json.loads(live_raw)
src_time = live.get("time", "")  # e.g. 12:57:47 = file time; CEC hour is the drop hour
tot = live["total"]
nat_now = float(tot["percent"]); nat_prev = tot.get("prev_percent")
# CEC drops are on even hours 10,12,14,16,18,20; the file published after hour H carries H
hh = int(src_time[:2]) if src_time else datetime.datetime.utcnow().hour + 2
HOUR = hh if hh % 2 == 0 else hh - 1
if int(src_time[:2]) % 2 == 0 and int(src_time[3:5]) >= 40:
    HOUR = hh  # published ~:50 after the hour
PREV = HOUR - 2

# ---------- history ----------
hist_p = os.path.join(OUT, "history.json")
hist = json.load(open(hist_p)) if os.path.exists(hist_p) else {"national": {}, "muni": {}}
hist["national"][str(HOUR)] = nat_now
# Landeswerte, die die CEC schon gemeldet hat, bevor die Kartendatei aktualisiert wurde (Quelle: Medien)
_mp = os.path.join(OUT, "manual_national.json")
if os.path.exists(_mp):
    for _h, _v in json.load(open(_mp)).items():
        if _h not in hist["national"] or int(_h) > HOUR: hist["national"][_h] = _v
if nat_prev is not None and str(PREV) not in hist["national"]:
    hist["national"][str(PREV)] = float(nat_prev)
for code, f in live["features"].items():
    m = hist["muni"].setdefault(code, {})
    m[str(HOUR)] = f.get("percent")
    # prev_percent der Ortsdatei ist ein unvollständiger Zwischenstand, nicht mit dem Landeswert vergleichbar -> nur 10 Uhr behalten
    if f.get("prev_percent") is not None and str(PREV) not in m and PREV == 10:
        m[str(PREV)] = f["prev_percent"]
json.dump(hist, open(hist_p, "w"))

# ---------- municipalities dataset ----------
DE = {3000:"Jerusalem",5000:"Tel Aviv",4000:"Haifa",8300:"Rishon LeZion",7400:"Netanya",7900:"Petah Tikva",70:"Aschdod",
 9000:"Beer Sheva",6600:"Holon",8600:"Ramat Gan",7100:"Aschkelon",6200:"Bat Yam",8400:"Rehovot",6100:"Bnei Brak",6400:"Herzlia",
 2610:"Beit Schemesch",6500:"Hadera",1200:"Modiin",8700:"Raanana",6900:"Kfar Saba",7000:"Lod",7300:"Nazareth",9100:"Naharija",
 8500:"Ramla",2630:"Kiryat Gat",3797:"Modiin Illit",1161:"Rahat",2600:"Eilat",3570:"Ariel",3616:"Maale Adumim",2200:"Dimona",
 2800:"Kiryat Schmona",6700:"Tiberias",1031:"Sderot",7500:"Sachnin",2620:"Kiryat Ono",1304:"Schoham",6300:"Givatayim",
 2650:"Ramat HaScharon",31:"Ofakim",246:"Netivot",6800:"Kiryat Ata",2640:"Rosch HaAjin",1139:"Karmiel",874:"Migdal HaEmek",
 9700:"Hod HaScharon",2560:"Arad",2100:"Tirat Carmel",1034:"Kiryat Malachi",2300:"Kiryat Tivon",7600:"Akko",8000:"Safed",
 2710:"Umm al-Fahm",8800:"Schefar'am",9500:"Kiryat Bialik",6800:"Kiryat Ata",1015:"Mevaseret Zion",3780:"Beitar Illit",1309:"Elad",
 2034:"Hatzor HaGlilit",1054:"Tel Sheva",9200:"Bet She'an",1063:"Ma'alot-Tarschicha",8200:"Kiryat Motzkin",2400:"Or Yehuda",7700:"Afula",
 1020:"Or Akiva",2500:"Nescher",8900:"Tamra",9400:"Yehud",2660:"Yavne",9600:"Kiryat Yam",1066:"Bnei Ayisch",2730:"Tayibe",
 494:"Daliyat al-Karmel",4100:"Kazrin",1247:"Harish",1271:"Lehavim",3611:"Kiryat Arba",3650:"Efrat",3760:"Oranit",3640:"Karnei Schomron"}

muni = []
for code, f in live["features"].items():
    c = int(code)
    s = R22.get(c)
    row = dict(code=c, name=DE.get(c) or f.get("שם ישוב") or (s or {}).get("name22") or str(c), name_he=f.get("שם ישוב"),
               eligible=int(f.get("בזב") or 0), kalpis=f.get("kalpis"), updated=f.get("updated"))
    if s:
        camp, nb, cb, ar = camp_of(s)
        row.update(camp=camp, turnout22=s["turnout22"], nbloc22=round(nb, 1), cbloc22=round(cb, 1), arab22=round(ar, 1),
                   likud22=round(s["likud"], 1), yesh22=round(s["yesh"], 1), haredi22=round(s["shas"] + s["utj"], 1),
                   raam22=round(s["raam"], 1), joint22=round(s["hadash"] + s["balad"], 1))
    else:
        row.update(camp="n.v.", turnout22=None)
    muni.append(row)

turn = []
for code, hs in hist["muni"].items():
    for h, p in hs.items():
        if p is not None:
            turn.append(dict(code=int(code), hour=int(h), turnout=p))

nat22_hours = {10: 15.9, 12: 28.4, 14: 38.9, 16: 47.5, 18: 57.7, 20: 66.3, 22: NAT22}
HH = json.load(open(os.path.join(OUT, "hist_hours.json")))
def nat_estimate(hour, now_pct):
    pts = [(e["hours"][str(hour)] if str(hour) in e["hours"] else e["hours"].get(hour), e["final"]) for e in HH
           if e["date"] >= "2003" and not str(e["key"]).startswith('"pm')]
    pts = [(x, y) for x, y in pts if x is not None]
    d = len(pts)
    if d < 5: return None
    mx = sum(x for x, _ in pts) / d; my = sum(y for _, y in pts) / d
    sxx = sum((x - mx) ** 2 for x, _ in pts); g = sum((x - mx) * (y - my) for x, y in pts) / sxx; b = my - g * mx
    se = (sum((y - (b + g * x)) ** 2 for x, y in pts) / (d - 2)) ** 0.5
    tq = {4:1.533,5:1.476,6:1.44,7:1.415,8:1.397,9:1.383,10:1.372,11:1.363,12:1.356}.get(d - 2, 1.35)
    y = b + g * now_pct; w = tq * se * (1 + 1 / d + (now_pct - mx) ** 2 / sxx) ** 0.5
    return dict(est=round(max(now_pct, y), 1), lo=round(max(now_pct, y - w), 1), hi=round(min(100, y + w), 1), n=d)
_NH = max(int(h) for h, v in hist["national"].items() if v is not None and int(h) < 22)
NEST = nat_estimate(_NH, float(hist["national"][str(_NH)]))
national = [dict(hour=h, y2026=hist["national"].get(str(h)), y2022=v,
                 est=(NEST["est"] if h == 22 and NEST else None), lo=(NEST["lo"] if h == 22 and NEST else None),
                 hi=(NEST["hi"] if h == 22 and NEST else None)) for h, v in nat22_hours.items()]

json.dump(muni, open(os.path.join(OUT, "muni.json"), "w"), ensure_ascii=False)
json.dump(turn, open(os.path.join(OUT, "turnout.json"), "w"), ensure_ascii=False)
json.dump(national, open(os.path.join(OUT, "national.json"), "w"), ensure_ascii=False)
json.dump(dict(generated=datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"), hour=HOUR, src_time=src_time, nat_now=nat_now, nat22=NAT22, n_muni=len(muni),
               n_join=sum(1 for m in muni if m.get("turnout22"))), open(os.path.join(OUT, "status.json"), "w"))
print("hour", HOUR, "src", src_time, "nat", nat_now, "nat22", NAT22, "muni", len(muni),
      "joined", sum(1 for m in muni if m.get("turnout22")))

# ---------- geometry (once) ----------
if "--geo" in sys.argv:
    from shapely.geometry import Polygon, MultiPolygon, mapping
    from shapely.ops import unary_union
    t = json.load(open(os.path.join(DL, "latest_municipal_geometry.topojson")))
    sx, sy = t["transform"]["scale"]; tx, ty = t["transform"]["translate"]
    arcs = []
    for a in t["arcs"]:
        x = y = 0; pts = []
        for dx, dy in a:
            x += dx; y += dy
            X = x * sx + tx; Y = y * sy + ty
            lon = X / 6378137 * 180 / math.pi
            lat = (2 * math.atan(math.exp(Y / 6378137)) - math.pi / 2) * 180 / math.pi
            pts.append((lon, lat))
        arcs.append(pts)
    def ring(ix):
        out = []
        for i in ix:
            seg = arcs[i] if i >= 0 else arcs[~i][::-1]
            out.extend(seg if not out else seg[1:])
        return out
    live_ids = set(live["features"].keys())
    shapes = []
    for g in t["objects"]["municipal"]["geometries"]:
        pid = str(g["properties"].get("id"))
        if g["type"] == "Polygon":
            polys = [Polygon(ring(g["arcs"][0]), [ring(h) for h in g["arcs"][1:]])]
        elif g["type"] == "MultiPolygon":
            polys = [Polygon(ring(p[0]), [ring(h) for h in p[1:]]) for p in g["arcs"]]
        else:
            continue
        geom = unary_union([p.buffer(0) for p in polys]).simplify(0.0012, preserve_topology=True)
        if geom.is_empty: continue
        def rnd(o):
            if isinstance(o, (list, tuple)):
                if o and isinstance(o[0], (int, float)): return [round(o[0], 4), round(o[1], 4)]
                return [rnd(x) for x in o]
            return o
        gj = mapping(geom)
        shapes.append(dict(code=int(pid) if pid.isdigit() else pid, live=pid in live_ids,
                           geometry=json.dumps({"type": gj["type"], "coordinates": rnd(gj["coordinates"])}, separators=(",", ":"))))
    json.dump(shapes, open(os.path.join(OUT, "shapes.json"), "w"), ensure_ascii=False, separators=(",", ":"))
    print("shapes", len(shapes), os.path.getsize(os.path.join(OUT, "shapes.json")))


# ---------- Tagesprofile 2022 (Anteil der Endbeteiligung, der zur Stunde erreicht war) ----------
# national: CEC; arabisch: 12 h ~12 % (Hadash-Ta'al), 14/16/18/20 h 17/23/30/44 % (aChord-Zentrum, Hebräische Univ., Modell + Stichprobe); Ende 53,2 % (IDI).
# Jüdisch: aus national und arabisch zurückgerechnet (Anteil arabischer Wahlberechtigter ~16 %).
NAT22H = {10: 15.9, 12: 28.4, 14: 38.9, 16: 47.5, 18: 57.7, 20: 66.3}
AR22H = {12: 12.0, 14: 17.0, 16: 23.0, 18: 30.0, 20: 44.0}
AR_SRC = {12: "Hadash-Ta'al", 14: "aChord (HU)", 16: "aChord (HU)", 18: "aChord (HU)", 20: "aChord (HU)"}
AR22F, WA = 53.2, 0.16
JE22F = (NAT22 - WA * AR22F) / (1 - WA)
prof = []
for h, n in NAT22H.items():
    prof.append(dict(group="national", hour=h, same22=n, final22=NAT22, share=round(n / NAT22, 4), source="CEC"))
    if h in AR22H:
        a = AR22H[h]; j = (n - WA * a) / (1 - WA)
        prof.append(dict(group="arab", hour=h, same22=a, final22=AR22F, share=round(a / AR22F, 4), source=AR_SRC[h]))
        prof.append(dict(group="jewish", hour=h, same22=round(j, 1), final22=round(JE22F, 1), share=round(j / JE22F, 4), source="abgeleitet"))
json.dump(prof, open(os.path.join(OUT, "profiles.json"), "w"), ensure_ascii=False)
PROF = {(p["group"], p["hour"]): p["share"] for p in prof}

# ---------- Zeitbereinigte Indizes je Stimmbezirk (Meldezeit jeder Urne berücksichtigt) ----------
def _hm(s):
    try:
        h, m = s.split(":"); return int(h) + int(m) / 60
    except Exception:
        return None
def _interp(pts, t):
    pts = sorted(pts)
    if t <= pts[0][0]: return pts[0][1]
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        if t <= x1: return y0 + (y1 - y0) * (t - x0) / (x1 - x0)
    return pts[-1][1]
N22 = [(7, 0.0)] + sorted(NAT22H.items()) + [(22, NAT22)]
_n26 = {int(h): float(v) for h, v in hist["national"].items() if v is not None and int(h) < 22}
N26 = [(7, 0.0)] + sorted(_n26.items())
_last = max(_n26)
def nat26_at(t):
    if t <= _last: return _interp(N26, t)
    return _n26[_last] * _interp(N22, t) / _interp(N22, _last)
AR = [(7, 0.0)] + sorted((h, v / AR22F) for h, v in AR22H.items()) + [(22, 1.0)]
def prof_at(g, t):
    n = _interp(N22, t) / NAT22
    if g == "national": return n
    a = _interp(AR, t)
    if g == "arab": return a
    return (n * NAT22 - WA * a * AR22F) / ((1 - WA) * JE22F)
def tod_idx(stations, final22, g):
    """stations: list of (eligible, pct, updated). Liefert (idx_ende, idx_uhrzeit, mittlere Meldezeit)."""
    num = den_e = den_t = w = tw = 0.0
    for E, pct, up in stations:
        t = _hm(up or "")
        if t is None or not E or pct is None: continue
        n26 = nat26_at(t); n22 = _interp(N22, t)
        if n26 <= 0 or n22 <= 0: continue
        num += E * pct
        den_e += E * final22 * n26 / NAT22
        den_t += E * final22 * prof_at(g, t) * n26 / n22
        w += E; tw += E * t
    if not w or not den_e: return None, None, None
    mt = tw / w
    return round(num / den_e, 2), round(num / den_t, 2), "%02d:%02d" % (int(mt), round((mt % 1) * 60) % 60)
# ---------- sectors (station level, votes26.com assignment) ----------
SEC_DE = {"right":"Rechte Hochburgen","left":"Mitte-links-Hochburgen","secular":"Säkular","national_religious":"National-religiös",
 "judea_samaria":"Judäa & Samaria","haredi":"Haredi","arab":"Arabisch","druze":"Drusisch","fsu":"Ex-UdSSR-Einwanderer",
 "ethiopian":"Äthiopische Einwanderer","north":"Nordgrenze","gaza":"Gaza-Umland","bedouin_north":"Beduinen Nord","bedouin_south":"Beduinen Negev","christian":"Christlich"}
sp = os.path.join(DL, "v26", "sectors.json")
if not os.path.exists(sp):
    os.makedirs(os.path.dirname(sp), exist_ok=True); get("https://votes26.com/data/sectors.json", sp)
secdef = json.load(open(sp))
kal = json.loads(get(BASE + "/latest/kalpi_data.json", os.path.join(DL, "kalpi_live.json")))["features"]
nat_same22 = {10: 15.9, 12: 28.4, 14: 38.9, 16: 47.5, 18: 57.7}.get(HOUR)
nat_proj = NAT22 * nat_now / nat_same22 if nat_same22 else None
def clampf(v, lo, hi):
    return round(min(hi, max(lo, v)), 1)
sec_rows = []
for sid, s in secdef["sectors"].items():
    E = V = n = tot = 0
    _st = []
    for loc, sts in s["k26_by_loc"].items():
        for st in sts:
            tot += 1; f = kal.get(f"{loc}|{st}")
            if f: E += f["בזב"]; V += f["מצביעים"]; n += 1; _st.append((f["בזב"], f.get("percent"), f.get("updated")))
    t22 = s["by_election"]["25"]["turnout"] * 100
    _g = "arab" if sid in ("arab", "bedouin_north", "bedouin_south", "christian", "druze") else "jewish"
    _ie, _it, _mt = tod_idx(_st, t22, _g)
    sh = s["by_election"]["25"]["share"]
    now = V / E * 100 if E else None
    j = _ie
    sec_rows.append(dict(sector=sid, label=SEC_DE.get(sid, sid), hour=HOUR, stations=n, stations_total=tot, eligible=E,
        t_now=round(now, 1) if now else None, turnout22=round(t22, 1), idx=_ie, idx_tod=_it, rep_time=_mt, profile=_g,
        est=clampf(t22 * j * NEST["est"] / NAT22, now, 100) if j and NEST else None,
        lo=clampf(t22 * j * NEST["lo"] / NAT22 - 1.5, now, clampf(t22 * j * NEST["est"] / NAT22, now, 100)) if j and NEST else None,
        hi=clampf(t22 * j * NEST["hi"] / NAT22 + 1.5, clampf(t22 * j * NEST["est"] / NAT22, now, 100), 100) if j and NEST else None,
        right22=round((sh["likud"] + sh["rz"] + sh["shas"] + sh["utj"]) * 100, 1),
        center_left22=round((sh["yb"] + sh["center"] + sh["left"]) * 100, 1), arab22=round(sh["arab"] * 100, 1)))
json.dump(sec_rows, open(os.path.join(OUT, "sectors.json"), "w"), ensure_ascii=False)
print("sectors", [(r["sector"], r["idx"]) for r in sec_rows])

soc = []
for sid, sdef in secdef["sectors"].items():
    for el, e in sdef["by_election"].items():
        r = dict(sector=sid, election=int(el), stations=e["stations"], eligible=e["eligible"], turnout=round(e["turnout"] * 100, 1))
        r.update({k: round(v * 100, 1) for k, v in e["share"].items()})
        soc.append(r)
json.dump(soc, open(os.path.join(OUT, "society.json"), "w"), ensure_ascii=False)
print("national est", NEST, "society rows", len(soc))

# ---------- Orte: zeitbereinigte Indizes aus den Stimmbezirken ----------
_by = {}
for key, f in kal.items():
    _by.setdefault(int(f.get("code") or key.split("|")[0]), []).append((f["בזב"], f.get("percent"), f.get("updated")))
for row in muni:
    s22 = R22.get(row["code"])
    if not s22 or row["code"] not in _by: continue
    g = "arab" if row.get("camp") in ("raam", "joint") else "jewish"
    ie, it, mt = tod_idx(_by[row["code"]], s22["turnout22"], g)
    _t = _hm(mt) if mt else None
    row.update(idx_end=ie, idx_tod=it, rep_time=mt, profile=g,
               same22=round(s22["turnout22"] * prof_at(g, _t), 1) if _t else None,
               nat26_t=round(nat26_at(_t), 1) if _t else None, nat22_t=round(_interp(N22, _t), 1) if _t else None)
json.dump(muni, open(os.path.join(OUT, "muni.json"), "w"), ensure_ascii=False)
print("tod", [(m["name"], m.get("idx_end"), m.get("idx_tod")) for m in muni if m["code"] in (5000, 3000, 6100, 1161, 7300, 7400)])
