"""Sea navigation: an ocean mask built from the world coastline (Natural Earth 110m land, bundled with the app), real canal/strait corridors
(Suez, Panama, Malacca, Gibraltar, Dover, Danish straits, Bosphorus, Hormuz, Sunda, Lombok...) and Dijkstra routing over a 1 degree water grid.
Routes are then straightened with a line-of-sight check on a finer 0.25 degree mask, so no leg crosses land. Everything is pure numpy/scipy."""
import os, json, math, heapq, threading
import numpy as np
from matplotlib.path import Path as MPath
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import dijkstra, connected_components

HERE = os.path.dirname(os.path.abspath(__file__))
TOPO = [os.path.join(HERE, "static", "vendor", "world.topo.json")]
R_NM = 3440.065
ACCESS = {   # river / bay / canal-side ports: where a ship actually enters open water (lat, lon). Matched on the port name.
    "wuhan": (31.2, 122.6), "nanjing": (31.2, 122.6), "taicang": (31.3, 122.4), "shanghai": (31.1, 122.4), "guangzhou": (22.0, 114.0), "dongguan": (22.0, 114.0), "zhuhai": (21.9, 113.8),
    "tokyo": (34.9, 139.9), "yokohama": (34.9, 139.9), "chiba": (34.9, 139.9), "nagoya": (34.2, 137.0), "osaka": (34.2, 135.0), "kobe": (34.2, 135.0), "hamburg": (54.1, 8.2), "antwerp": (51.45, 3.4),
    "houston": (29.1, -94.6), "new orleans": (28.9, -89.3), "baltimore": (37.0, -75.9), "norfolk": (36.9, -75.9), "montreal": (49.3, -66.0), "palembang": (-2.0, 105.4), "yangon": (15.7, 96.3), "mongla": (21.6, 89.5), "kolkata": (21.6, 88.2),
    "ho chi minh": (10.3, 107.1), "kandla": (22.8, 69.6), "navlakhi": (22.9, 70.0), "dahej": (21.7, 72.0), "hazira": (21.0, 72.4), "ambarli": (40.9, 28.3), "izmir": (38.4, 26.6), "amsterdam": (52.5, 4.3), "london gateway": (51.5, 1.2),
    "oslo": (59.2, 10.6), "douala": (3.9, 9.4), "fuzhou": (26.0, 119.9), "lianyungang": (34.7, 119.6), "port klang": (2.9, 101.0), "belawan": (4.1, 98.6), "rotterdam": (51.95, 3.9), "buenos aires": (-35.0, -57.0), "montevideo": (-35.0, -56.2), "guayaquil": (-2.8, -80.4),
    "seattle": (47.9, -122.7), "tacoma": (47.8, -122.8), "vancouver": (49.2, -123.4), "oakland": (37.8, -122.6), "kuching": (2.0, 110.3), "bangkok": (13.3, 100.6), "haikou": (20.3, 110.3), "port said": (31.4, 32.3), "ain sokhna": (29.6, 32.6), "aqaba": (28.9, 34.9),
}
CORRIDORS = {   # name -> centre line (lat, lon); cells along it (and 0.3 degree either side) are forced to water
    "Suez Canal": [(31.9, 32.3), (31.3, 32.33), (30.6, 32.34), (30.0, 32.55), (29.4, 32.55), (28.9, 32.8), (28.3, 33.2)],
    "Panama Canal": [(9.9, -79.95), (9.35, -79.88), (9.05, -79.6), (8.6, -79.5), (8.0, -79.4)],
    "Strait of Malacca": [(1.1, 104.3), (1.25, 103.7), (1.9, 102.6), (2.7, 101.5), (3.6, 100.5), (4.6, 99.9), (5.6, 99.0), (6.3, 97.5)],
    "Singapore Strait": [(1.2, 104.0), (1.4, 104.6), (2.2, 105.5)],
    "Strait of Gibraltar": [(36.5, -7.0), (36.0, -5.8), (36.0, -5.3), (36.2, -4.5), (36.4, -3.5)],
    "Dover Strait": [(49.6, -6.0), (49.8, -3.0), (50.4, -0.5), (50.9, 1.1), (51.4, 2.1), (52.0, 3.0)],
    "Danish Straits": [(57.7, 7.5), (57.8, 10.3), (57.0, 11.6), (56.2, 12.5), (55.5, 12.8), (55.0, 13.0), (54.9, 14.0), (55.2, 16.0), (56.0, 18.0), (57.5, 19.7), (58.8, 21.0), (59.6, 23.5), (59.9, 26.0), (60.0, 29.0)],
    "Bosphorus": [(39.9, 25.9), (40.2, 26.5), (40.7, 27.7), (41.0, 28.9), (41.4, 29.15), (42.0, 29.4), (42.8, 29.8)],
    "Strait of Hormuz": [(24.5, 58.6), (25.7, 56.8), (26.5, 56.3), (26.4, 54.8), (26.6, 52.8), (27.4, 51.0), (28.8, 49.8), (29.6, 48.9)],
    "Bab-el-Mandeb": [(12.0, 43.9), (12.7, 43.3), (13.6, 42.6)],
    "Sunda Strait": [(-5.7, 105.9), (-6.1, 105.8), (-6.8, 105.3)],
    "Lombok Strait": [(-7.6, 115.7), (-8.4, 115.7), (-9.2, 115.6)],
    "Messina": [(38.4, 15.6), (38.0, 15.6), (37.5, 15.3)],
    "Seto Inland Sea": [(33.9, 135.0), (34.4, 134.9), (34.5, 135.1)],
    "Korea Strait": [(35.0, 129.2), (34.3, 129.8), (33.5, 130.3)],
    "Aegean": [(36.2, 22.8), (36.6, 24.0), (37.5, 24.2), (38.5, 24.6), (39.5, 24.6), (40.0, 25.8)],
    "Adriatic": [(39.8, 18.9), (41.0, 18.7), (42.5, 17.5), (43.8, 15.3), (45.0, 13.5), (45.6, 13.4)],
    "Red Sea": [(27.5, 34.2), (24.0, 36.2), (20.0, 38.4), (16.0, 41.2), (13.5, 42.8)],
    "Gulf of Aden": [(12.5, 43.5), (12.0, 47.0), (12.4, 51.5), (12.0, 54.5)],
    "Persian Gulf": [(24.5, 58.6), (25.5, 56.7), (26.4, 54.5), (27.0, 52.0), (28.0, 50.5), (29.3, 48.8)],
    "Gulf of Mexico": [(24.0, -84.0), (23.0, -87.0), (26.5, -90.0), (28.0, -91.0), (28.0, -95.0), (26.0, -97.0), (21.0, -97.0), (19.0, -95.0)],
    "Baltic South": [(54.2, 18.9), (54.6, 19.5)],
}
BLOCK_GROUPS = {"suez": ["Suez Canal"], "panama": ["Panama Canal"], "malacca": ["Strait of Malacca"], "hormuz": ["Strait of Hormuz"], "bosphorus": ["Bosphorus"]}
CHOKE_LABEL = {"Suez Canal": "Suez Canal", "Panama Canal": "Panama Canal", "Strait of Malacca": "Strait of Malacca", "Strait of Gibraltar": "Gibraltar", "Dover Strait": "English Channel", "Strait of Hormuz": "Hormuz", "Bab-el-Mandeb": "Bab-el-Mandeb", "Bosphorus": "Bosphorus", "Danish Straits": "Danish Straits", "Sunda Strait": "Sunda Strait", "Lombok Strait": "Lombok Strait"}

def _hav(a, b):
    la1, lo1, la2, lo2 = map(math.radians, (a[0], a[1], b[0], b[1])); h = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return R_NM * 2 * math.asin(min(1.0, math.sqrt(h)))

def _land_polys():
    p = next((x for x in TOPO if os.path.exists(x)), None)
    if not p: raise FileNotFoundError("world.topo.json (bundled with the app) not found")
    t = json.load(open(p)); sx, sy = t["transform"]["scale"]; tx, ty = t["transform"]["translate"]; arcs = []
    for a in t["arcs"]:
        x = y = 0; pts = []
        for dx, dy in a: x += dx; y += dy; pts.append((x * sx + tx, y * sy + ty))
        arcs.append(pts)
    def ring(idx):
        out = []
        for i in idx:
            seg = arcs[i] if i >= 0 else arcs[~i][::-1]; out += seg if not out else seg[1:]
        return out
    polys = []
    def geoms(o):
        if o["type"] == "GeometryCollection":
            for g in o["geometries"]: yield from geoms(g)
        else: yield o
    for g in geoms(t["objects"]["land"]):
        pl = g["arcs"] if g["type"] == "MultiPolygon" else [g["arcs"]]
        for poly in pl: polys.append([_unwrap_ring(ring(r)) for r in poly])        # [outer, holes...]
    return polys
def _unwrap_ring(pts):
    """Rings that cross the antimeridian jump by ~360 degrees between two points; make the longitude continuous (it may then exceed +-180)."""
    out = [pts[0]]
    for x, y in pts[1:]:
        px = out[-1][0]
        while x - px > 180: x -= 360
        while x - px < -180: x += 360
        out.append((x, y))
    return out

def gc_arr(a, b, step_nm=60.0, include_ends=True):
    """Vectorised great-circle sampling: (lat array, lon array); longitudes continuous with a's."""
    la1, lo1, la2, lo2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    v1 = np.array([math.cos(la1) * math.cos(lo1), math.cos(la1) * math.sin(lo1), math.sin(la1)]); v2 = np.array([math.cos(la2) * math.cos(lo2), math.cos(la2) * math.sin(lo2), math.sin(la2)])
    om = math.acos(max(-1.0, min(1.0, float(v1 @ v2)))); n = max(1, int(om * R_NM / step_nm)); k = np.arange(0 if include_ends else 1, n + 1 if include_ends else n); t = k / n
    if om > 1e-9: w1 = np.sin((1 - t) * om) / math.sin(om); w2 = np.sin(t * om) / math.sin(om)
    else: w1, w2 = 1 - t, t
    v = w1[:, None] * v1[None, :] + w2[:, None] * v2[None, :]; la = np.degrees(np.arcsin(np.clip(v[:, 2], -1, 1))); lo = np.degrees(np.arctan2(v[:, 1], v[:, 0]))
    lo = a[1] + (((lo - a[1]) + 180) % 360 - 180)          # continuous with a's longitude
    return la, lo
def gc_points(a, b, step_nm=60.0, include_ends=True):
    """Points along the great circle from a to b (lat, lon), spaced about step_nm apart; longitudes continuous with a's."""
    la, lo = gc_arr(a, b, step_nm, include_ends); out = list(zip(la.tolist(), lo.tolist()))
    for q in range(1, len(out)):          # keep successive longitudes continuous (no jumps > 180)
        while out[q][1] - out[q - 1][1] > 180: out[q] = (out[q][0], out[q][1] - 360)
        while out[q][1] - out[q - 1][1] < -180: out[q] = (out[q][0], out[q][1] + 360)
    return out

class Sea:
    def __init__(self, step=1.0, fine=0.25, latmin=-78.0, latmax=82.0):
        self.step, self.fine, self.latmin, self.latmax = step, fine, latmin, latmax
        self.lats = np.arange(latmin + step / 2, latmax, step); self.lons = np.arange(-180 + step / 2, 180, step); self.nlat, self.nlon = len(self.lats), len(self.lons)
        self.flats = np.arange(latmin + fine / 2, latmax, fine); self.flons = np.arange(-180 + fine / 2, 180, fine)
        polys = _land_polys(); self.land = self._raster(polys, self.lats, self.lons); self.fland = self._raster(polys, self.flats, self.flons)
        self.corr_cells = {}                                                   # corridor name -> set of coarse node ids
        for name, line in CORRIDORS.items(): self._carve(name, line)
        pol = (self.lats < -52) | (self.lats > 76); drake = (self.lons > -82) & (self.lons < -48)
        self.land[np.ix_(pol & (self.lats < 0), ~drake)] = True; self.land[np.ix_(self.lats > 76, np.ones(self.nlon, bool))] = True
        fpol = (self.flats < -52); fdrake = (self.flons > -82) & (self.flons < -48); self.fland[np.ix_(fpol, ~fdrake)] = True; self.fland[self.flats > 76, :] = True
        self.ocean = ~self.land; self.nid = -np.ones(self.land.shape, int); self.nid[self.ocean] = np.arange(int(self.ocean.sum()))
        self.nodes = np.argwhere(self.ocean); self.n = len(self.nodes); self._build_graph()
        self._cache = {}; self._variants = {}; self._lock = threading.RLock()
    def _raster(self, polys, lats, lons):
        LON, LAT = np.meshgrid(lons, lats); pts = np.c_[LON.ravel(), LAT.ravel()]; inside = np.zeros(len(pts), bool)
        for rings in polys:
            outer = np.array(rings[0]); x0, y0 = outer.min(0); x1, y1 = outer.max(0)
            for off in (0, 360, -360):
                mo = (pts[:, 0] + off >= x0) & (pts[:, 0] + off <= x1) & (pts[:, 1] >= y0) & (pts[:, 1] <= y1)
                if not mo.any(): continue
                idx = np.where(mo)[0]; q = pts[idx] + np.array([off, 0]); ins = MPath(outer).contains_points(q)
                for h in rings[1:]: ins &= ~MPath(np.array(h)).contains_points(q)
                inside[idx[ins]] = True
        return inside.reshape(len(lats), len(lons))
    def _carve(self, name, line):
        cells = set()
        for (a, b) in zip(line[:-1], line[1:]):
            n = max(2, int(_hav(a, b) / 8))
            for t in np.linspace(0, 1, n):
                la, lo = a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t
                i = int((la - self.latmin) / self.step); j = int((lo + 180) / self.step) % self.nlon
                if 0 <= i < self.nlat: self.land[i, j] = False; cells.add((i, j))
                fi = int((la - self.latmin) / self.fine); fj = int((lo + 180) / self.fine) % len(self.flons)
                for di in (-1, 0, 1):
                    for dj in (-1, 0, 1):
                        a_, b_ = fi + di, (fj + dj) % len(self.flons)
                        if 0 <= a_ < len(self.flats): self.fland[a_, b_] = False
        self.corr_cells[name] = cells
    def _build_graph(self):
        rows, cols, w = [], [], []
        for k, (i, j) in enumerate(self.nodes):
            for di in (-1, 0, 1):
                for dj in (-1, 0, 1):
                    if di == 0 and dj == 0: continue
                    a, b = i + di, (j + dj) % self.nlon
                    if not (0 <= a < self.nlat) or not self.ocean[a, b]: continue
                    if di != 0 and dj != 0 and not (self.ocean[i, b] or self.ocean[a, j]): continue         # no diagonal squeeze between two land cells
                    rows.append(k); cols.append(self.nid[a, b]); w.append(_hav((self.lats[i], self.lons[j]), (self.lats[a], self.lons[b])))
        self.A = csr_matrix((w, (rows, cols)), shape=(self.n, self.n))
        nc, lab = connected_components(self.A, directed=False); self.main = lab == np.bincount(lab).argmax(); self.comp = lab
    # ------------------------------------------------------------ helpers
    def is_land(self, la, lo):
        i = int((la - self.latmin) / self.fine); j = int(((lo + 180) % 360) / self.fine)
        return bool(self.fland[i, j]) if 0 <= i < len(self.flats) else True
    def dist_to_water_nm(self, la, lo, maxr=2.0):
        """Distance in nm from a point to the nearest water cell of the fine mask (0 if the point is in water)."""
        i0 = int((la - self.latmin) / self.fine); j0 = int(((lo + 180) % 360) / self.fine); r = int(maxr / self.fine); best = None
        for di in range(-r, r + 1):
            for dj in range(-r, r + 1):
                i, j = i0 + di, (j0 + dj) % len(self.flons)
                if 0 <= i < len(self.flats) and not self.fland[i, j]:
                    d = _hav((la, lo), (self.flats[i], self.flons[j])); best = d if best is None or d < best else best
        return best
    def _clear(self, a, b, ends=0.6):
        la, lo = gc_arr(a, b, 7.0)
        keep = ~(((np.abs(la - a[0]) < ends) & (np.abs(lo - a[1]) < ends)) | ((np.abs(la - b[0]) < ends) & (np.abs(lo - b[1]) < ends)))
        la, lo = la[keep], lo[keep]
        if not len(la): return True
        i = ((la - self.latmin) / self.fine).astype(int); j = (((lo + 180) % 360) / self.fine).astype(int); ok = (i >= 0) & (i < len(self.flats))
        if not ok.all(): return False
        return not bool(self.fland[i, j].any())
    def _near_nodes(self, la, lo, k=12, main_only=True):
        d = (self.lats[self.nodes[:, 0]] - la) ** 2 + ((((self.lons[self.nodes[:, 1]] - lo + 180) % 360) - 180) * math.cos(math.radians(la))) ** 2
        if main_only: d = np.where(self.main, d, 1e9)
        return np.argsort(d)[:k]
    def _snap(self, la, lo):
        near = self._near_nodes(la, lo)
        for k in near:
            p = (float(self.lats[self.nodes[k, 0]]), float(self.lons[self.nodes[k, 1]]))
            if self._clear((la, lo), p, 0.45): return int(k)
        return int(near[0])
    def _graph_for(self, blocked):
        key = tuple(sorted(blocked))
        if not key: return self.A
        with self._lock:
            if key in self._variants: return self._variants[key]
            ok = np.ones(self.n, bool)
            for g in key:
                for name in BLOCK_GROUPS.get(g, [g]):
                    for (i, j) in self.corr_cells.get(name, ()):
                        if self.nid[i, j] >= 0: ok[self.nid[i, j]] = False
            D = csr_matrix(ok.astype(float)).T if False else None
            A = self.A.multiply(ok[:, None]).multiply(ok[None, :]).tocsr(); A.eliminate_zeros(); self._variants[key] = A; return A
    # ------------------------------------------------------------ public API
    def route(self, o, d, blocked=(), storms=(), oa=None, da=None):
        """o, d = (lat, lon). Returns {"pts": [(lat, lon), ...] (longitudes unwrapped), "nm": float, "via": [names]} or None."""
        key = (round(o[0], 2), round(o[1], 2), round(d[0], 2), round(d[1], 2), oa, da, tuple(sorted(blocked)), tuple((round(s[0]), round(s[1]), round(s[2])) for s in storms))
        with self._lock:
            if key in self._cache: return self._cache[key]
        A = self._graph_for(blocked)
        if storms:
            ok = np.ones(self.n, bool)
            for (sla, slo, rn) in storms:
                dd = np.array([_hav((sla, slo), (self.lats[i], self.lons[j])) for i, j in self.nodes]) if False else None
                la_ = self.lats[self.nodes[:, 0]]; lo_ = self.lons[self.nodes[:, 1]]
                dist = R_NM * np.arccos(np.clip(np.sin(np.radians(la_)) * math.sin(math.radians(sla)) + np.cos(np.radians(la_)) * math.cos(math.radians(sla)) * np.cos(np.radians(lo_ - slo)), -1, 1)); ok &= dist > rn
            A = A.multiply(ok[:, None]).multiply(ok[None, :]).tocsr(); A.eliminate_zeros()
        s, t = self._snap(*(oa or o)), self._snap(*(da or d))
        dist, pred = dijkstra(A, directed=True, indices=s, return_predecessors=True)
        if not np.isfinite(dist[t]): res = None
        else:
            path = [t]
            while path[-1] != s: path.append(pred[path[-1]])
            path.reverse(); pts = [o] + ([oa] if oa else []) + [(float(self.lats[self.nodes[k, 0]]), float(self.lons[self.nodes[k, 1]])) for k in path] + ([da] if da else []) + [d]; pts = self._unwrap(self._straighten(pts)); pts = self._densify(pts)
            res = {"pts": [(round(a, 3), round(b, 3)) for a, b in pts], "nm": round(sum(_hav(pts[i], pts[i + 1]) for i in range(len(pts) - 1)), 1), "via": self._via(pts)}
        with self._lock: self._cache[key] = res
        return res
    def _straighten(self, pts):
        out = [pts[0]]; i = 0
        while i < len(pts) - 1:
            j = len(pts) - 1
            while j > i + 1 and not self._clear(pts[i], pts[j], 0.5): j -= 1
            out.append(pts[j]); i = j
        return out
    @staticmethod
    def _densify(pts, step=90.0):
        out = [pts[0]]
        for a, b in zip(pts[:-1], pts[1:]): out += gc_points(a, b, step)[1:]
        return out
    @staticmethod
    def _unwrap(pts):
        out = [pts[0]]
        for la, lo in pts[1:]:
            prev = out[-1][1]
            while lo - prev > 180: lo -= 360
            while lo - prev < -180: lo += 360
            out.append((la, lo))
        return out
    def _via(self, pts):
        names = []; dense = []
        for a, b in zip(pts[:-1], pts[1:]):
            for t in np.linspace(0, 1, max(2, int(_hav(a, b) / 15))): dense.append((a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t))
        order = []
        for la, lo in dense:
            i = int((la - self.latmin) / self.step); j = int(((lo + 180) % 360) / self.step) % self.nlon
            for name, cells in self.corr_cells.items():
                if name in CHOKE_LABEL and (i, j) in cells and CHOKE_LABEL[name] not in order: order.append(CHOKE_LABEL[name])
        if any(-47 < la < -30 and 10 < (lo % 360 if lo < 0 else lo) < 35 for la, lo in dense): order.append("Cape of Good Hope")
        if any(la < -50 and (-80 < lo < -55) for la, lo in dense): order.append("Cape Horn / Drake Passage")
        return order
    def options(self, o, d, blocked=(), storms=(), oa=None, da=None):
        """Up to three sea routes: shortest, and the alternatives that avoid Suez / Panama / Malacca when the shortest uses them."""
        base = self.route(o, d, tuple(blocked), storms, oa, da); out = []
        if not base: return out
        def label(r):
            v = r["via"]; return ("via " + " + ".join(v[:3])) if v else "direct sea route"
        out.append({"name": label(base), "pts": base["pts"], "nm": base["nm"], "via": base["via"]})
        for g, nm_ in (("suez", "Suez Canal"), ("panama", "Panama Canal"), ("malacca", "Strait of Malacca")):
            if nm_ in base["via"] and g not in blocked:
                alt = self.route(o, d, tuple(blocked) + (g,), storms, oa, da)
                if alt and abs(alt["nm"] - base["nm"]) > 50 and all(abs(alt["nm"] - x["nm"]) > 50 for x in out): out.append({"name": label(alt) + f" (without {nm_})", "pts": alt["pts"], "nm": alt["nm"], "via": alt["via"]})
        return out

def access_for(name):
    n = (name or "").lower()
    for k, v in ACCESS.items():
        if k in n: return v
    return None
_SEA = None; _SL = threading.Lock(); _VER = "v5"
def _cache_path():
    d = os.environ.get("APP_DATA_DIR") or os.path.dirname(os.path.abspath(__file__)); return os.path.join(d, f"seanav_{_VER}.pkl")
def sea():
    """Singleton. The raster + graph (about 6 s to build) is pickled next to the database, so later starts load in well under a second."""
    global _SEA
    with _SL:
        if _SEA is None:
            import pickle
            p = _cache_path()
            try:
                with open(p, "rb") as f: _SEA = pickle.load(f)
                _SEA._cache = {}; _SEA._variants = {}; _SEA._lock = threading.RLock()
            except Exception:
                _SEA = Sea()
                try:
                    st = {k: v for k, v in _SEA.__dict__.items() if k not in ("_lock", "_cache", "_variants")}
                    class _P: pass
                    o = Sea.__new__(Sea); o.__dict__.update(st)
                    with open(p + ".tmp", "wb") as f: pickle.dump(o, f, protocol=4)
                    os.replace(p + ".tmp", p)
                except Exception: pass
    return _SEA
