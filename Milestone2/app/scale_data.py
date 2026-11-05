"""Scale both apps to production-like volume. Idempotent: only tops tables up to the target counts.
Coordinates are approximate (1-2 decimals): replace/extend through the Data Feeder with UN/LOCODE or World Port Index data."""
import random, datetime, math
from live_engine import conn, _DB_LOCK, now

PORTS = {
"China": "Dalian 38.9 121.7;Xiamen 24.5 118.1;Fuzhou 26.0 119.4;Lianyungang 34.7 119.4;Yantai 37.6 121.4;Rizhao 35.4 119.5;Nanjing 32.1 118.8;Zhanjiang 21.2 110.4;Haikou 20.0 110.3;Zhuhai 22.2 113.6;Taicang 31.5 121.2;Wuhan 30.6 114.3;Shantou 23.4 116.7;Dongguan 22.9 113.6",
"Japan": "Yokohama 35.4 139.7;Nagoya 35.1 136.9;Osaka 34.6 135.4;Kobe 34.7 135.2;Hakata 33.6 130.4;Chiba 35.6 140.1",
"South Korea": "Incheon 37.4 126.6;Gwangyang 34.9 127.7;Ulsan 35.5 129.4;Pyeongtaek 36.9 126.8",
"Taiwan": "Keelung 25.1 121.7;Taichung 24.3 120.5", "Vietnam": "Hai Phong 20.8 106.7;Da Nang 16.1 108.2;Vung Tau 10.4 107.1;Quy Nhon 13.8 109.3",
"Thailand": "Bangkok 13.7 100.6;Songkhla 7.2 100.6", "Malaysia": "Penang 5.4 100.3;Johor 1.4 103.9;Kuantan 3.97 103.4;Kuching 1.6 110.3",
"Indonesia": "Surabaya -7.2 112.7;Semarang -6.9 110.4;Belawan 3.8 98.7;Makassar -5.1 119.4;Balikpapan -1.3 116.8;Palembang -3.0 104.8;Bitung 1.4 125.2",
"Philippines": "Cebu 10.3 123.9;Davao 7.1 125.6;Subic Bay 14.8 120.3", "Myanmar": "Yangon 16.8 96.2", "Cambodia": "Sihanoukville 10.6 103.5",
"Bangladesh": "Chittagong 22.3 91.8;Mongla 22.5 89.6", "Sri Lanka": "Hambantota 6.1 81.1;Galle 6.0 80.2", "Pakistan": "Port Qasim 24.8 67.3;Gwadar 25.1 62.3", "Iran": "Chabahar 25.3 60.6",
"India": "Mormugao 15.4 73.8;Pipavav 20.9 71.5;Hazira 21.1 72.6;Ennore 13.2 80.3;Krishnapatnam 14.3 80.1;Kakinada 16.9 82.3;Gangavaram 17.6 83.2;Dahej 21.7 72.5;Mumbai Port 18.9 72.8;Navlakhi 22.9 70.5;Karaikal 10.9 79.9;Kamarajar 13.3 80.3;Vizhinjam 8.4 77.0;Okha 22.5 69.1;Porbandar 21.6 69.6",
"UAE": "Khalifa Port 24.8 54.6;Port Rashid 25.3 55.3;Fujairah 25.1 56.4;Khor Fakkan 25.3 56.4", "Oman": "Sohar 24.5 56.6;Duqm 19.7 57.7",
"Saudi Arabia": "Dammam 26.5 50.2;King Abdullah Port 22.5 39.1;Yanbu 24.1 38.1", "Qatar": "Hamad Port 25.0 51.6", "Kuwait": "Shuwaikh 29.4 47.9", "Bahrain": "Khalifa Bin Salman 26.2 50.6",
"Iraq": "Umm Qasr 30.0 47.9", "Jordan": "Aqaba 29.5 35.0", "Israel": "Haifa 32.8 35.0;Ashdod 31.8 34.6", "Turkey": "Mersin 36.8 34.6;Ambarli 41.0 28.7;Izmir 38.4 27.1",
"Yemen": "Aden 12.8 45.0", "Djibouti": "Djibouti 11.6 43.1", "Sudan": "Port Sudan 19.6 37.2",
"Germany": "Bremerhaven 53.6 8.5", "Belgium": "Zeebrugge 51.3 3.2", "Netherlands": "Amsterdam 52.4 4.9", "United Kingdom": "Southampton 50.9 -1.4;London Gateway 51.5 0.5;Liverpool 53.4 -3.0",
"Ireland": "Dublin 53.3 -6.2", "France": "Marseille Fos 43.4 4.9", "Spain": "Barcelona 41.4 2.2;Bilbao 43.3 -3.0", "Portugal": "Lisbon 38.7 -9.1;Sines 37.9 -8.9",
"Italy": "Naples 40.8 14.3;La Spezia 44.1 9.8;Livorno 43.6 10.3;Trieste 45.6 13.8;Gioia Tauro 38.4 15.9;Taranto 40.5 17.2", "Slovenia": "Koper 45.5 13.7", "Croatia": "Rijeka 45.3 14.4",
"Greece": "Thessaloniki 40.6 22.9", "Romania": "Constanta 44.2 28.7", "Bulgaria": "Varna 43.2 27.9", "Ukraine": "Odesa 46.5 30.7", "Sweden": "Gothenburg 57.7 11.9", "Denmark": "Aarhus 56.2 10.2",
"Norway": "Oslo 59.9 10.7", "Finland": "Helsinki 60.2 25.0", "Poland": "Gdynia 54.5 18.5", "Lithuania": "Klaipeda 55.7 21.1", "Latvia": "Riga 57.0 24.1", "Estonia": "Tallinn 59.4 24.8",
"Russia": "St Petersburg 59.9 30.2;Novorossiysk 44.7 37.8", "Malta": "Marsaxlokk 35.8 14.5", "Cyprus": "Limassol 34.7 33.0",
"Egypt": "Alexandria 31.2 29.9;Port Said 31.3 32.3;Damietta 31.5 31.8;Ain Sokhna 29.6 32.4", "Libya": "Tripoli 32.9 13.2", "Tunisia": "Rades 36.8 10.3", "Algeria": "Algiers 36.8 3.1",
"Morocco": "Casablanca 33.6 -7.6", "Senegal": "Dakar 14.7 -17.4", "Ivory Coast": "Abidjan 5.3 -4.0", "Ghana": "Tema 5.6 0.0", "Togo": "Lome 6.1 1.3", "Benin": "Cotonou 6.4 2.4",
"Nigeria": "Onne 4.7 7.2", "Cameroon": "Douala 4.0 9.7", "Angola": "Luanda -8.8 13.2", "Namibia": "Walvis Bay -22.9 14.5", "South Africa": "Cape Town -33.9 18.4;Ngqura -33.8 25.7",
"Mozambique": "Maputo -25.97 32.6;Beira -19.8 34.9", "Tanzania": "Dar es Salaam -6.8 39.3", "Kenya": "Mombasa -4.1 39.7", "Somaliland": "Berbera 10.4 45.0", "Mauritius": "Port Louis -20.2 57.5", "Madagascar": "Toamasina -18.1 49.4",
"USA": "Oakland 37.8 -122.3;Seattle 47.6 -122.3;Tacoma 47.3 -122.4;Houston 29.7 -95.3;New Orleans 29.9 -90.1;Miami 25.8 -80.2;Charleston 32.8 -79.9;Norfolk 36.9 -76.3;Baltimore 39.3 -76.6;Boston 42.4 -71.0",
"Canada": "Vancouver 49.3 -123.1;Prince Rupert 54.3 -130.3;Halifax 44.6 -63.6;Montreal 45.5 -73.5", "Mexico": "Manzanillo 19.1 -104.3;Veracruz 19.2 -96.1;Lazaro Cardenas 17.9 -102.2",
"Panama": "Balboa 8.95 -79.6;Colon 9.35 -79.9", "Colombia": "Cartagena 10.4 -75.5;Buenaventura 3.9 -77.1", "Peru": "Callao -12.05 -77.15", "Ecuador": "Guayaquil -2.3 -79.9",
"Chile": "San Antonio -33.6 -71.6;Valparaiso -33.0 -71.6", "Argentina": "Buenos Aires -34.6 -58.4", "Uruguay": "Montevideo -34.9 -56.2",
"Brazil": "Santos -23.98 -46.3;Paranagua -25.5 -48.5;Rio Grande -32.0 -52.1;Itajai -26.9 -48.7;Suape -8.4 -35.0;Pecem -3.5 -38.8", "Jamaica": "Kingston 17.97 -76.8", "Dominican Republic": "Caucedo 18.4 -69.6", "Bahamas": "Freeport 26.5 -78.8",
"Australia": "Sydney -33.9 151.2;Melbourne -37.8 144.9;Brisbane -27.4 153.2;Fremantle -32.05 115.7;Adelaide -34.8 138.5;Port Hedland -20.3 118.6", "New Zealand": "Auckland -36.8 174.8;Tauranga -37.65 176.2;Lyttelton -43.6 172.7",
"Fiji": "Suva -18.1 178.4", "New Caledonia": "Noumea -22.3 166.4", "Papua New Guinea": "Port Moresby -9.5 147.1"}
CARRIERS = ["Evergreen Marine","HMM","Yang Ming","ZIM Integrated","Pacific International Lines","Wan Hai Lines","OOCL","APL","Hamburg Sud","Matson","SM Line","Sinokor","KMTC","Namsung Shipping","SITC",
"X-Press Feeders","Gold Star Line","Arkas Line","Turkon Line","Grimaldi Lines","Messina Line","CCNI","Seaboard Marine","Crowley Maritime","Tropical Shipping","Swire Shipping","Hoegh Autoliners",
"Wallenius Wilhelmsen","NYK Line","Mitsui OSK Lines","K Line","Safmarine","Emirates Shipping Line","Shipping Corporation of India","Great Eastern Shipping","Samudera Shipping","Salam Pacific",
"Interasia Lines","Heung-A Line","Unifeeder","Containerships","Finnlines","DFDS","Stena Line","Atlantic Container Line","King Ocean","Bengal Tiger Line","Transworld Shipping","Sealand Maersk Asia","Pan Ocean","Cosco Hong Kong"]
def region_of(lat, lon):
    if -170 < lon < -30: return "Americas"
    if -30 <= lon < 50 and lat > 12: return "Europe/Mediterranean" if lat > 30 else "Africa"
    if -30 <= lon < 52 and lat <= 12: return "Africa"
    if 112 < lon and lat < -10: return "Oceania"
    if 25 < lon < 60 and 12 < lat < 33: return "Middle East"
    return "Asia"

def scale_freight(target_ports=220, target_carriers=110, target_shipments=400):
    R = random.Random(42)
    with _DB_LOCK, conn() as c:
        have = {r[0].lower() for r in c.execute("SELECT port_name FROM ports")}; n = c.execute("SELECT COUNT(*) FROM ports").fetchone()[0]
        for ctry, spec in PORTS.items():
            for e in spec.split(";"):
                if n >= target_ports + 40: break
                nm, la, lo = e.rsplit(" ", 2); name = f"{nm} Port"
                if name.lower() in have: continue
                n += 1; have.add(name.lower())
                c.execute("INSERT OR REPLACE INTO ports(port_id,port_name,country,congestion_index,avg_dwell_days,lat,lon,region) VALUES(?,?,?,?,?,?,?,?)",
                          (f"PORT-{n:03d}", name, ctry, round(R.uniform(1.0, 4.6), 1), round(R.uniform(1.5, 7.0), 1), float(la), float(lo), region_of(float(la), float(lo))))
        k = c.execute("SELECT COUNT(*) FROM carriers").fetchone()[0]; names = {r[0] for r in c.execute("SELECT name FROM carriers")}
        pool = [x for x in CARRIERS if x not in names] + [f"Regional Feeder Line {i:02d}" for i in range(1, 80)]
        for nm in pool:
            if k >= target_carriers: break
            k += 1
            c.execute("INSERT OR REPLACE INTO carriers(carrier_id,name,rating,on_time_pct,avg_cost_index,risk_level) VALUES(?,?,?,?,?,?)",
                      (f"CAR-{k:03d}", nm, round(R.uniform(3.2, 4.9), 2), round(R.uniform(68, 97), 1), round(R.uniform(.8, 1.25), 2), R.choice(["Low", "Low", "Medium", "High"])))
        ports = c.execute("SELECT port_name FROM ports").fetchall(); cars = [r[0] for r in c.execute("SELECT name FROM carriers")]
        s = c.execute("SELECT COUNT(*) FROM shipments").fetchone()[0]
        while s < target_shipments:
            s += 1; a, b = R.sample(ports, 2)
            c.execute("INSERT OR REPLACE INTO shipments(shipment_id,origin_port,dest_port,carrier,status,eta,weight_kg,hs_code,predicted_delay_risk) VALUES(?,?,?,?,?,?,?,?,?)",
                      (f"SHP-{s:04d}", a[0], b[0], R.choice(cars), R.choices(["In Transit", "Delivered", "Customs Hold", "Port Congestion Delay", "Anchorage Pending"], [55, 20, 8, 10, 7])[0],
                       (datetime.date.today() + datetime.timedelta(days=R.randint(2, 40))).isoformat(), round(R.uniform(800, 28000), 1), f"HS-{R.choice([30,84,85,87,10,62,27,39,72,22])}{R.randint(10,99)}", round(R.uniform(.03, .6), 2)))

CITIES = {"Mumbai": (19.08, 72.88), "Delhi": (28.61, 77.21), "Bengaluru": (12.97, 77.59), "Chennai": (13.08, 80.27), "Hyderabad": (17.39, 78.49), "Pune": (18.52, 73.86), "Ahmedabad": (23.03, 72.57),
"Jaipur": (26.91, 75.79), "Kolkata": (22.57, 88.36), "Surat": (21.17, 72.83), "Kochi": (9.93, 76.27), "Coimbatore": (11.02, 76.96), "Lucknow": (26.85, 80.95), "Nagpur": (21.15, 79.09), "Indore": (22.72, 75.86),
"Bhopal": (23.26, 77.41), "Patna": (25.59, 85.14), "Chandigarh": (30.73, 76.78), "Visakhapatnam": (17.69, 83.22), "Vadodara": (22.31, 73.18), "Thiruvananthapuram": (8.52, 76.94), "Mysuru": (12.30, 76.64),
"Guwahati": (26.14, 91.74), "Bhubaneswar": (20.30, 85.82), "Ranchi": (23.34, 85.31), "Raipur": (21.25, 81.63), "Dehradun": (30.32, 78.03), "Goa": (15.50, 73.83), "Madurai": (9.93, 78.12), "Nashik": (19.99, 73.79)}
SKUS = [("Buns", "Food"), ("Cooking Oil", "Food"), ("Sauce", "Food"), ("Frozen Fries", "Food"), ("Chicken", "Food"), ("Cheese", "Food"), ("Lettuce", "Food"), ("Packaging", "Supplies"), ("Beverage Syrup", "Beverage"), ("Potatoes", "Food"), ("Flour", "Food"), ("Spice Mix", "Food")]
def scale_franchise(outlets=120, staff=1250, per_outlet_sku=12):
    R = random.Random(42)
    with _DB_LOCK, conn() as c:
        c.executescript("""CREATE TABLE IF NOT EXISTS outlet_geo(outlet_id TEXT PRIMARY KEY, lat REAL, lon REAL);
        CREATE TABLE IF NOT EXISTS customers_fr(customer_id TEXT PRIMARY KEY, outlet_id TEXT, total_spend_90d REAL, visit_freq REAL, avg_order_value REAL, days_since_last_visit INT);""")
        n = c.execute("SELECT COUNT(*) FROM outlets").fetchone()[0]; tiers = ["Metro Flagship", "Urban", "Suburban", "Highway"]; cities = list(CITIES)
        while n < outlets:
            n += 1; oid = f"OUT-{n:03d}"; city = R.choice(cities); rev = R.uniform(900000, 5200000)
            c.execute("INSERT OR REPLACE INTO outlets VALUES(?,?,?,?,?,?,?,?)", (oid, f"Franchise Outlet {n:03d}", city, R.choice(tiers), rev, rev * R.uniform(.55, .82), round(R.uniform(3.0, 4.9), 2), R.randint(12, 30)))
        for oid, city in c.execute("SELECT outlet_id, location FROM outlets").fetchall():
            if not c.execute("SELECT 1 FROM outlet_geo WHERE outlet_id=?", (oid,)).fetchone():
                la, lo = CITIES.get(city, CITIES["Mumbai"]); c.execute("INSERT INTO outlet_geo VALUES(?,?,?)", (oid, la + R.uniform(-.06, .06), lo + R.uniform(-.06, .06)))
        s = c.execute("SELECT COUNT(*) FROM staff").fetchone()[0]; oids = [r[0] for r in c.execute("SELECT outlet_id FROM outlets")]
        while s < staff:
            s += 1; sal = R.uniform(18000, 80000); sat = R.randint(1, 5); ot = R.uniform(0, 35)
            p = max(.05, min(.95, .9 - sal / 100000 - sat / 10 + ot / 100))
            c.execute("INSERT OR REPLACE INTO staff VALUES(?,?,?,?,?,?,?,?,?,?,?)", (f"STF-{s:04d}", R.choice(oids), f"Employee {s:04d}", R.choice(["Crew", "Crew", "Cashier", "Cook", "Shift Lead", "Store Manager"]), sal, round(ot, 1), sat, R.randint(19, 58), R.randint(0, 12), R.randint(1, 5), round(p, 2)))
        for oid in oids:
            have = {r[0] for r in c.execute("SELECT sku_name FROM inventory WHERE outlet_id=?", (oid,))}
            for sku, cat in SKUS[:per_outlet_sku]:
                if sku in have or sku in {"Oil"} and "Cooking Oil" == sku: continue
                wk = R.uniform(80, 700); lead = R.randint(2, 9)
                c.execute("INSERT OR REPLACE INTO inventory VALUES(?,?,?,?,?,?,?,?,?)", (f"INV-{oid[4:]}-{sku[:3].upper()}", oid, sku, cat, int(wk / 7 * (lead + R.uniform(2, 12))), int(wk / 7 * lead), round(wk, 1), lead, .1))
            if c.execute("SELECT COUNT(*) FROM marketing WHERE outlet_id=?", (oid,)).fetchone()[0] < 2:
                for j in range(2):
                    c.execute("INSERT OR REPLACE INTO marketing VALUES(?,?,?,?,?,?,?,?,?,?)", (f"CMP-{oid[4:]}-{j}", oid, f"Campaign {oid[4:]}-{j}", R.choice(["Social", "Email", "Influencer", "Offline"]), R.uniform(20000, 120000), round(R.uniform(1.2, 5.2), 2), R.randint(8000, 60000), R.randint(200, 2500), "2024-01-01", "2024-12-31"))
            if c.execute("SELECT COUNT(*) FROM audits WHERE outlet_id=?", (oid,)).fetchone()[0] < 2:
                for j in range(2):
                    sc = max(40, min(100, R.gauss(84, 10)))
                    c.execute("INSERT OR REPLACE INTO audits VALUES(?,?,?,?,?,?,?,?)", (f"AUD-{oid[4:]}-{j}", oid, (datetime.date.today() - datetime.timedelta(days=30 * (j + 1))).isoformat(), sc, int((100 - sc) / 6), R.choice(["Food Safety", "Hygiene", "SOP Compliance"]), "Pass" if sc >= 80 else "Warning" if sc >= 60 else "Fail", "Monthly audit"))
            if c.execute("SELECT COUNT(*) FROM feedback WHERE outlet_id=?", (oid,)).fetchone()[0] < 8:
                for j in range(8):
                    r = R.choices([1, 2, 3, 4, 5], [5, 8, 15, 35, 37])[0]
                    c.execute("INSERT OR REPLACE INTO feedback VALUES(?,?,?,?,?,?)", (f"FB-{oid[4:]}-{j}", oid, r, R.choice(["Great taste", "Slow service", "Clean ambience", "Staff was rude", "Cold food", "Good value", "Long wait time", "Dirty tables"]), datetime.date.today().isoformat(), (r - 3) / 2))
            if c.execute("SELECT COUNT(*) FROM customers_fr WHERE outlet_id=?", (oid,)).fetchone()[0] < 30:
                for j in range(30):
                    seg = R.choices(["hv", "freq", "churn"], [.2, .4, .4])[0]
                    f = {"hv": (6, 12), "freq": (3, 8), "churn": (.2, 1.5)}[seg]; aov = R.uniform(250, 900) if seg == "hv" else R.uniform(150, 450)
                    fr = R.uniform(*f); c.execute("INSERT OR REPLACE INTO customers_fr VALUES(?,?,?,?,?,?)", (f"C-{oid[4:]}-{j}", oid, round(fr * aov * 3, 0), round(fr, 1), round(aov, 0), R.randint(60, 120) if seg == "churn" else R.randint(1, 20)))
