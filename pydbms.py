import sqlite3
import json
from datetime import datetime
from flask import Flask, request, jsonify, render_template

app = Flask(__name__)
DB_PATH = "moksha.db"

GET_DB = lambda: sqlite3.connect(DB_PATH)


def init_db():
    with app.app_context():
        conn = GET_DB()
        cursor = conn.cursor()

        with open("schema (1).sql", "r") as f:
            sql_script = f.read()

        for t in ["COLLEGE", "PARTICIPANT", "EVENT", "REGISTRATION", "ENTRY_PASS", "VENDOR", "STALL_BOOKING", "STALL", "SPONSORSHIP", "SPONSORSHIP_TIER", "FEEDBACK"]:
            cursor.execute(f"DROP TABLE IF EXISTS {t}")
        cursor.executescript(sql_script)
        conn.commit()
        conn.close()


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/events", methods=["GET"])
def api_events():
    conn = GET_DB()
    cursor = conn.cursor()
    cursor.execute("SELECT event_id, name, category, venue, event_date, fee, max_seats FROM EVENT")
    rows = cursor.fetchall()
    events = []
    for r in rows:
        event_id = r[0]
        cursor.execute("SELECT COUNT(*) FROM REGISTRATION WHERE event_id = ?", (event_id,))
        registered = cursor.fetchone()[0]
        seats_left = max(0, r[6] - registered)
        events.append({
            "event_id": event_id, "name": r[1], "category": r[2], "venue": r[3],
            "event_date": r[4], "fee": r[5], "max_seats": r[6], "seats_left": seats_left
        })
    conn.close()
    return jsonify(events)


@app.route("/api/stalls", methods=["GET"])
def api_stalls():
    conn = GET_DB()
    cursor = conn.cursor()
    cursor.execute("SELECT stall_id, location, size, price, status FROM STALL")
    rows = cursor.fetchall()
    conn.close()
    stalls = [{"stall_id": r[0], "location": r[1], "size": r[2], "price": r[3], "status": r[4]} for r in rows]
    return jsonify(stalls)


@app.route("/api/tiers", methods=["GET"])
def api_tiers():
    conn = GET_DB()
    cursor = conn.cursor()
    cursor.execute("SELECT tier_id, name, amount, benefits FROM SPONSORSHIP_TIER")
    rows = cursor.fetchall()
    conn.close()
    tiers = [{"tier_id": r[0], "name": r[1], "amount": r[2], "benefits": r[3]} for r in rows]
    return jsonify(tiers)


@app.route("/api/register", methods=["POST"])
def api_register():
    try:
        data = request.get_json()
        conn = GET_DB()
        cursor = conn.cursor()

        # Ensure college exists or insert it
        college_name = data.get("college_name", "").strip()
        college_id = None
        if college_name:
            row = cursor.execute("SELECT college_id FROM COLLEGE WHERE name=?", (college_name,)).fetchone()
            if row:
                college_id = row[0]
            else:
                cursor.execute("INSERT INTO COLLEGE (name, city, is_nsut) VALUES (?, ?, ?)",
                               (college_name, data.get("college_city", ""), 1 if college_name == "NSUT" else 0))
                college_id = cursor.lastrowid

        cursor.execute(
            """INSERT INTO PARTICIPANT (full_name, email, phone, age, gender, college_id, enrollment_no, year_of_study, course_branch, state, emergency_name, emergency_phone, dietary_pref, tshirt_size, accommodation, id_proof_type, how_heard, participant_role, special_needs)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (data.get("full_name"), data.get("email"), data.get("phone"), data.get("age"), data.get("gender"),
             college_id, data.get("enrollment_no"), data.get("year_of_study"), data.get("course_branch"),
             data.get("state"), data.get("emergency_name", "Not provided"), data.get("emergency_phone", "0000000000"), data.get("dietary_pref"),
             data.get("tshirt_size"), data.get("accommodation", "No"), data.get("id_proof_type"),
             data.get("how_heard"), data.get("participant_role"), data.get("special_needs", "None")))
        participant_id = cursor.lastrowid

        event_ids = data.get("event_ids", [])
        team_name = data.get("team_name", "")
        team_size = data.get("team_size")
        experience_level = data.get("experience_level", "")
        pass_type = data.get("pass_type", "All Days")

        for eid in event_ids:
            cursor.execute(
                "INSERT INTO REGISTRATION (participant_id, event_id, team_name, team_size, experience_level) VALUES (?, ?, ?, ?, ?)",
                (participant_id, int(eid), team_name if team_name else None,
                 int(team_size) if team_size else None, experience_level if experience_level else None))

        # If no events selected, still create a registration row for tracking if needed,
        # but keep existing behavior. Instead just save entry pass.
        # Save entry pass with user-selected pass_type
        fee = 0
        # Try to get fee from selected events; if none selected, default to 0 or use a default
        if event_ids:
            placeholders = ",".join("?" * len(event_ids))
            cursor.execute(f"SELECT fee FROM EVENT WHERE event_id IN ({placeholders})", event_ids)
            fees = [r[0] for r in cursor.fetchall()]
            fee = sum(fees) if fees else 0
        price = data.get("fee", fee)
        # Use provided fee if user sends it; else computed fee
        final_price = price if price else 0
        cursor.execute(
            "INSERT INTO ENTRY_PASS (participant_id, pass_type, price) VALUES (?, ?, ?)",
            (participant_id, pass_type if pass_type else "All Days", float(final_price)))

        conn.commit()
        conn.close()
        return jsonify({"ok": True, "participant_id": participant_id})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/vendor", methods=["POST"])
def api_vendor():
    data = request.get_json()
    conn = GET_DB()
    cursor = conn.cursor()

    cursor.execute(
        """INSERT INTO VENDOR (company_name, contact_person, email, phone, business_type, website, social_handle, address, city, gst_number, fssai_no, years_in_business, alt_phone)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (data.get("company_name"), data.get("contact_person"), data.get("email"), data.get("phone"),
         data.get("business_type"), data.get("website"), data.get("social_handle"), data.get("address"),
         data.get("city"), data.get("gst_number"), data.get("fssai_no"), data.get("years_in_business"),
         data.get("alt_phone")))
    vendor_id = cursor.lastrowid

    # Stall booking
    stall_id = data.get("stall_id")
    if stall_id and str(stall_id).strip() != "":
        cursor.execute(
            """INSERT INTO STALL_BOOKING (vendor_id, stall_id, products_description, staff_count, power_required_kw, equipment_needed, preferred_days, status)
               VALUES (?, ?, ?, ?, ?, ?, ?, 'Pending')""",
            (vendor_id, int(stall_id), data.get("products_description"), data.get("staff_count"),
             data.get("power_required_kw"), data.get("equipment_needed"), data.get("preferred_days")))
        cursor.execute("UPDATE STALL SET status='Booked' WHERE stall_id=?", (int(stall_id),))

    # Sponsorship
    tier_id = data.get("tier_id")
    event_id = data.get("event_id")
    if tier_id and str(tier_id).strip() != "":
        event_id_int = int(event_id) if event_id and str(event_id).strip() != "" else None
        cursor.execute(
            """INSERT INTO SPONSORSHIP (vendor_id, tier_id, event_id, sponsor_type, proposed_amount, brand_objective, promo_requirements, status)
               VALUES (?, ?, ?, ?, ?, ?, ?, 'Pending')""",
            (vendor_id, int(tier_id), event_id_int, data.get("sponsor_type"),
             data.get("proposed_amount"), data.get("brand_objective"), data.get("promo_requirements")))

    conn.commit()
    conn.close()
    return jsonify({"ok": True, "vendor_id": vendor_id})


@app.route("/api/feedback", methods=["GET"])
def api_feedback():
    conn = GET_DB()
    cursor = conn.cursor()
    cursor.execute("SELECT feedback_id, name, email, role, category, message, created_at FROM FEEDBACK ORDER BY created_at DESC")
    rows = cursor.fetchall()
    conn.close()
    return jsonify([{"feedback_id": r[0], "name": r[1], "email": r[2], "role": r[3], "category": r[4], "message": r[5], "created_at": r[6]} for r in rows])


@app.route("/api/feedback", methods=["POST"])
def api_feedback_post():
    try:
        data = request.get_json()
        conn = GET_DB()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO FEEDBACK (name, email, role, category, message) VALUES (?, ?, ?, ?, ?)",
            (data.get("name"), data.get("email"), data.get("role", "Participant"), data.get("category", "Feedback"), data.get("message")))
        conn.commit()
        feedback_id = cursor.lastrowid
        conn.close()
        return jsonify({"ok": True, "feedback_id": feedback_id})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"ok": False, "error": str(e)}), 500


if __name__ == "__main__":
    init_db()
    app.run(debug=True, port=5000)
