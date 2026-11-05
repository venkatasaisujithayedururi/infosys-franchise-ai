import random, sqlite3, datetime
import pandas as pd
from db import get_conn

BASE_PORTS = [
    ("JNPT Nhava Sheva (Mumbai)", "India", 3.4, 4, 18.95, 72.95, "Asia"),
    ("Mundra Port", "India", 2.8, 3, 22.84, 69.70, "Asia"),
    ("Chennai Port", "India", 3.1, 4, 13.10, 80.30, "Asia"),
    ("Tuticorin VOC Port", "India", 2.5, 3, 8.75, 78.18, "Asia"),
    ("Cochin Port", "India", 2.2, 3, 9.96, 76.26, "Asia"),
    ("Visakhapatnam Port", "India", 2.9, 3, 17.68, 83.28, "Asia"),
    ("Kolkata Haldia Port", "India", 3.5, 5, 22.03, 88.11, "Asia"),
    ("Kandla Deendayal Port", "India", 3.0, 4, 23.01, 70.22, "Asia"),
    ("New Mangalore Port", "India", 2.3, 3, 12.92, 74.81, "Asia"),
    ("Paradip Port", "India", 3.2, 4, 20.26, 86.67, "Asia"),
    ("Shanghai Port", "China", 4.2, 5, 31.23, 121.47, "Asia"),
    ("Singapore Port", "Singapore", 1.2, 2, 1.29, 103.85, "Asia"),
    ("Busan Port", "South Korea", 1.8, 3, 35.10, 129.04, "Asia"),
    ("Tokyo Port", "Japan", 2.2, 3, 35.62, 139.77, "Asia"),
    ("Colombo Port", "Sri Lanka", 2.7, 3, 6.94, 79.84, "Asia"),
    ("Dubai Jebel Ali Port", "UAE", 1.9, 2, 25.20, 55.27, "Middle East"),
    ("Rotterdam Port", "Netherlands", 1.5, 2, 51.92, 4.47, "Europe"),
    ("Antwerp Port", "Belgium", 2.6, 3, 51.22, 4.40, "Europe"),
    ("Hamburg Port", "Germany", 2.5, 3, 53.55, 9.99, "Europe"),
    ("Los Angeles Port", "USA", 3.6, 4, 33.74, -118.27, "Americas")
]

def safe_exec(conn, sql, params=()):
    try:
        conn.execute(sql, params)
    except Exception as e:
        pass

def seed_all():
    with get_conn() as conn:
        # 1. Ports
        safe_exec(conn, "DELETE FROM ports;")
        for i, p in enumerate(BASE_PORTS, 1):
            safe_exec(conn,
                "INSERT OR REPLACE INTO ports (port_id, port_name, country, congestion_index, avg_dwell_days, lat, lon, region) VALUES (?, ?, ?, ?, ?, ?, ?, ?);",
                (f"PORT-{i:03d}", p[0], p[1], p[2], p[3], p[4], p[5], p[6])
            )

        # 2. User accounts are created by accounts.py (signup, admin dashboard and the seeded Admin); no demo passwords live in the code.

        # 3. Shipments
        safe_exec(conn, "DELETE FROM shipments;")
        carriers_list = ["Maersk Line", "MSC Cargo", "CMA CGM", "COSCO Shipping", "Hapag-Lloyd", "ONE Ocean Express"]
        statuses = ["In Transit", "Customs Hold", "Delivered", "Port Congestion Delay", "Anchorage Pending"]
        cargos = ["Electronics", "Pharmaceuticals", "Automotive Parts", "Textiles", "Heavy Machinery", "Perishables"]

        for i in range(1, 101):
            p1 = BASE_PORTS[i % len(BASE_PORTS)][0]
            p2 = BASE_PORTS[(i+3) % len(BASE_PORTS)][0]
            shp_id = f"SHP-{i:04d}"
            weight = round(random.uniform(500.0, 45000.0), 1)
            dist = round(random.uniform(800.0, 18000.0), 1)
            sev = random.randint(1, 5)
            ch_prob = round(random.uniform(0.02, 0.45), 2)
            cong = round(random.uniform(1.0, 4.8), 1)
            d_risk = round((cong / 5.0) * 0.5 + (ch_prob) * 0.3 + (sev / 5.0) * 0.2, 2)
            co2 = round(weight * dist * 0.00012, 1)
            margin = round(random.uniform(8.5, 28.0), 1)
            dwell = random.randint(1, 8)
            cargo = random.choice(cargos)
            hs = f"HS-{random.randint(8400, 8900)}"

            safe_exec(conn,
                "INSERT OR REPLACE INTO shipments (shipment_id, origin_port, dest_port, carrier, status, weight_kg, distance_km, weather_severity, customs_hold_prob, congestion_index, predicted_delay_risk, co2_emissions_kg, freight_margin, port_dwell_days, cargo_type, hs_code) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);",
                (shp_id, p1, p2, random.choice(carriers_list), random.choice(statuses), weight, dist, sev, ch_prob, cong, d_risk, co2, margin, dwell, cargo, hs)
            )

        # 4. Weather Risks
        safe_exec(conn, "DELETE FROM weather_risks;")
        for i in range(1, 21):
            pname = BASE_PORTS[(i - 1) % len(BASE_PORTS)][0]
            sev = random.randint(1, 4)
            fore = "Category 3 Typhoon Warning" if sev >= 3 else "Clear Maritime Conditions"
            w_spd = round(random.uniform(12.0, 58.0), 1)
            wv_ht = round(random.uniform(0.8, 5.5), 1)
            temp = round(random.uniform(14.0, 38.0), 1)
            safe_exec(conn,
                "INSERT OR REPLACE INTO weather_risks (port_name, current_severity, forecast, wind_speed, wave_height, temperature) VALUES (?, ?, ?, ?, ?, ?);",
                (pname, sev, fore, w_spd, wv_ht, temp)
            )

        # 5. Alerts
        safe_exec(conn, "DELETE FROM alerts;")
        categories = ["Customs Hold", "Typhoon Storm", "Port Congestion", "Vessel Mechanical", "Bunker Fuel Surcharge"]
        severities = ["Critical", "High", "Medium", "Low"]
        for i in range(1, 51):
            shp_id = f"SHP-{i:04d}"
            sev = random.choice(severities)
            cat = random.choice(categories)
            msg = f"Alert #{i:03d}: Severe {cat} operational delay reported on {shp_id}."
            safe_exec(conn,
                "INSERT INTO alerts (shipment_id, severity, category, message, date, resolved) VALUES (?, ?, ?, ?, ?, ?);",
                (shp_id, sev, cat, msg, "2024-08-11", 0)
            )

        # 6. Carriers
        safe_exec(conn, "DELETE FROM carriers;")
        for idx, name in enumerate(carriers_list, 1):
            safe_exec(conn,
                "INSERT OR REPLACE INTO carriers (carrier_id, name, rating, on_time_pct, avg_cost_index, risk_level) VALUES (?, ?, ?, ?, ?, ?);",
                (f"CAR-{idx:03d}", name, round(random.uniform(3.8, 4.9), 2), round(random.uniform(78, 96), 1), round(random.uniform(0.86, 1.18), 2), "Low")
            )

        # 7. Customers
        safe_exec(conn, "DELETE FROM customers;")
        for i in range(1, 25):
            safe_exec(conn,
                "INSERT OR REPLACE INTO customers (customer_id, name, industry, priority_tier, credit_risk) VALUES (?, ?, ?, ?, ?);",
                (f"CUST-{i:03d}", f"Corporate Client {i:03d}", random.choice(["Food Service", "Retail", "QSR", "Hospitality"]), random.choice(["Platinum", "Gold", "Silver"]), round(random.uniform(0.02, 0.18), 2))
            )

        # 8. Freight Quotes
        safe_exec(conn, "DELETE FROM freight_quotes;")
        for i in range(1, 51):
            base = round(random.uniform(1200, 9000), 2)
            margin_pct = round(random.uniform(9, 24), 1)
            final = round(base * (1 + margin_pct / 100), 2)
            safe_exec(conn,
                "INSERT OR REPLACE INTO freight_quotes (quote_id, shipment_id, customer_id, base_cost, insurance, customs_fee, fuel_surcharge, final_price, margin_pct, status, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);",
                (f"QTE-{i:04d}", f"SHP-{random.randint(1, 50):04d}", f"CUST-{random.randint(1, 20):03d}", base, round(base * 0.02, 2), round(random.uniform(100, 600), 2), round(base * 0.08, 2), final, margin_pct, random.choice(["Draft", "Accepted", "Submitted"]), datetime.date.today().isoformat())
            )

        # 9. Customs Tariffs
        safe_exec(conn, "DELETE FROM customs_tariffs;")
        for i, cargo in enumerate(cargos, 1):
            safe_exec(conn,
                "INSERT OR REPLACE INTO customs_tariffs (tariff_id, hs_code, cargo_type, origin_country, destination_country, duty_rate, clearance_risk, required_docs, advisory) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);",
                (f"TAR-{i:03d}", f"HS-{8400 + i * 31}", cargo, "India", "UAE", round(random.uniform(4, 16), 2), round(random.uniform(0.08, 0.42), 2), "Commercial invoice, packing list, bill of lading", "Validate HS code and pre-clear high-risk lanes.")
            )

        # 10. Outlets (FranchiseOps)
        outlet_cities = ["Chennai", "Bengaluru", "Hyderabad", "Mumbai", "Pune", "Delhi", "Kochi", "Coimbatore", "Ahmedabad", "Kolkata"]
        tiers = ["Metro Flagship", "Urban", "Express", "Mall"]
        safe_exec(conn, "DELETE FROM outlets;")
        for i in range(1, 51):
            revenue = round(random.uniform(850000, 6400000), 2)
            cost = round(revenue * random.uniform(0.58, 0.82), 2)
            safe_exec(conn,
                "INSERT OR REPLACE INTO outlets (outlet_id, outlet_name, location, tier, revenue, operating_costs, customer_satisfaction, staff_headcount) VALUES (?, ?, ?, ?, ?, ?, ?, ?);",
                (f"OUT-{i:03d}", f"Franchise Outlet {i:03d}", random.choice(outlet_cities), random.choice(tiers), revenue, cost, round(random.uniform(3.2, 4.9), 2), random.randint(12, 55))
            )

        # 11. Staff
        roles = ["Store Manager", "Shift Lead", "Crew", "Chef", "Cashier", "Inventory Associate"]
        safe_exec(conn, "DELETE FROM staff;")
        for i in range(1, 151):
            satisfaction = random.randint(1, 5)
            overtime = round(random.uniform(0, 42), 1)
            attrition = min(0.95, max(0.03, 0.55 - satisfaction * 0.08 + overtime * 0.009 + random.uniform(-0.08, 0.08)))
            safe_exec(conn,
                "INSERT OR REPLACE INTO staff (staff_id, outlet_id, name, role, salary, overtime_hrs, job_satisfaction, age, tenure_years, work_life_balance, predicted_attrition_prob) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);",
                (f"STF-{i:04d}", f"OUT-{random.randint(1, 50):03d}", f"Employee {i:04d}", random.choice(roles), round(random.uniform(18000, 95000), 2), overtime, satisfaction, random.randint(19, 56), random.randint(0, 14), random.randint(1, 5), round(attrition, 2))
            )

        # 12. Inventory
        skus = ["Buns", "Cheese", "Sauce", "Chicken", "Paneer", "Coffee Beans", "Packaging", "Oil", "Frozen Fries", "Dessert Mix"]
        safe_exec(conn, "DELETE FROM inventory;")
        for i in range(1, 151):
            demand = round(random.uniform(20, 420), 1)
            threshold = random.randint(30, 180)
            stock = random.randint(5, 420)
            risk = min(0.95, max(0.02, (threshold - stock) / max(threshold, 1) + random.uniform(0.05, 0.28)))
            safe_exec(conn,
                "INSERT OR REPLACE INTO inventory (record_id, outlet_id, sku_name, category, current_stock, reorder_threshold, weekly_demand, lead_time_days, stockout_risk_prob) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);",
                (f"INV-{i:04d}", f"OUT-{random.randint(1, 50):03d}", random.choice(skus), random.choice(["Food", "Beverage", "Packaging", "Consumable"]), stock, threshold, demand, random.randint(1, 9), round(risk, 2))
            )

        # 13. Marketing
        channels = ["Digital Ads", "Social Media", "Local Print", "Influencer Campaign", "Radio Spots"]
        safe_exec(conn, "DELETE FROM marketing;")
        for i in range(1, 51):
            budget = round(random.uniform(15000, 120000), 2)
            roi = round(random.uniform(1.8, 5.4), 2)
            safe_exec(conn,
                "INSERT OR REPLACE INTO marketing (campaign_id, outlet_id, campaign_name, channel, budget, actual_roi, reach, conversions, start_date, end_date) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);",
                (f"CMP-{i:03d}", f"OUT-{random.randint(1, 50):03d}", f"Campaign {i:03d}", random.choice(channels), budget, roi, random.randint(5000, 80000), random.randint(200, 4500), "2024-01-01", "2024-12-31")
            )

        # 14. Feedback
        safe_exec(conn, "DELETE FROM feedback;")
        comments = ["Great food!", "Slow service", "Clean ambience", "Polite staff", "Average experience"]
        for i in range(1, 101):
            rating = random.randint(1, 5)
            sentiment = round((rating - 3) / 2.0, 2)
            safe_exec(conn,
                "INSERT OR REPLACE INTO feedback (feedback_id, outlet_id, rating, comment, date, sentiment_score) VALUES (?, ?, ?, ?, ?, ?);",
                (f"FB-{i:04d}", f"OUT-{random.randint(1, 50):03d}", rating, random.choice(comments), "2024-08-01", sentiment)
            )

        # 15. Audits
        safe_exec(conn, "DELETE FROM audits;")
        categories_audit = ["Food Safety", "Hygiene & Sanitation", "Fire & Safety", "Financial Compliance"]
        for i in range(1, 51):
            score = round(random.uniform(65, 99), 1)
            status = "Pass" if score >= 85 else ("Conditional Pass" if score >= 75 else "Action Required")
            safe_exec(conn,
                "INSERT OR REPLACE INTO audits (audit_id, outlet_id, audit_date, score, violations, category, status, notes) VALUES (?, ?, ?, ?, ?, ?, ?, ?);",
                (f"AUD-{i:03d}", f"OUT-{random.randint(1, 50):03d}", "2024-08-01", score, int((100-score)/5), random.choice(categories_audit), status, "Audit completed cleanly.")
            )

        conn.commit()
