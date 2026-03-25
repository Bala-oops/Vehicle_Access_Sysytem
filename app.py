# app.py - Updated for Supabase PostgreSQL (minimal changes to your existing project)

from flask import (
    Flask, render_template, request, redirect, url_for,
    flash, session, jsonify, send_file
)
import os
import io

import psycopg2
from dotenv import load_dotenv

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

# -------------------------
# CONFIG - Supabase PostgreSQL
# -------------------------
load_dotenv()

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres.bbtyjzupkszhuffqqzkp:%2F77SB4P9ST7Ds%40%2F@aws-1-ap-south-1.pooler.supabase.com:6543/postgres?sslmode=require"
)

def get_conn():
    return psycopg2.connect(DATABASE_URL)


# -------------------------
# FLASK APP
# -------------------------
app = Flask(__name__)
app.secret_key = "change_this_secret_in_production"

# -------------------------
# Utility helpers
# -------------------------
def fetch_request_by_id(cursor, request_id):
    cursor.execute(
        """
        SELECT RequestId, RequestedBy, VehicleType, TypeOfVehicle, AccessLocation,
               VehicleNo, EngineNo, ChassisNo, Model, OwnerUsername, Address, ContactNo,
               DriverName, DriverAddress, FromDate, ToDate, HODApproval, SecurityApproval
        FROM VehicleAccessRequests
        WHERE RequestId=%s
        """,
        (request_id,),
    )
    return cursor.fetchone()


def require_login():
    return "DomainId" in session


def require_role(role):
    return session.get("Role") == role


# -------------------------
# ROUTES
# -------------------------
@app.route("/")
def home():
    return render_template("login.html")


# ---- LOGIN ----
@app.route("/login", methods=["POST"])
def login():
    domain_id = request.form.get("domain_id")
    password = request.form.get("password")

    if not domain_id or not password:
        flash("Please provide Domain ID and Password")
        return redirect(url_for("home"))

    conn = None
    cursor = None
    try:
        conn = get_conn()
        cursor = conn.cursor()

        # RegisteredEmployees
        cursor.execute(
            "SELECT DomainId FROM RegisteredEmployees WHERE DomainId=%s AND Password=%s",
            (domain_id, password),
        )
        if cursor.fetchone():
            session["DomainId"] = domain_id
            session["Role"] = "Registered"
            flash("Login Successful - Registered Employee")
            return redirect(url_for("enter_details"))

        # HOD
        cursor.execute(
            "SELECT DomainId FROM HOD WHERE DomainId=%s AND Password=%s",
            (domain_id, password),
        )
        if cursor.fetchone():
            session["DomainId"] = domain_id
            session["Role"] = "HOD"
            flash("Login Successful - HOD")
            return redirect(url_for("hod"))

        # Security
        cursor.execute(
            "SELECT DomainId FROM Security WHERE DomainId=%s AND Password=%s",
            (domain_id, password),
        )
        if cursor.fetchone():
            session["DomainId"] = domain_id
            session["Role"] = "Security"
            flash("Login Successful - Security")
            return redirect(url_for("security"))

        # Admin
        cursor.execute(
            "SELECT DomainId FROM Admin WHERE DomainId=%s AND Password=%s",
            (domain_id, password),
        )
        if cursor.fetchone():
            session["DomainId"] = domain_id
            session["Role"] = "Admin"
            flash("Login Successful - Admin")
            return redirect(url_for("admin"))

        flash("Invalid Domain ID or Password")
        return redirect(url_for("home"))
    except Exception as e:
        flash(f"Login Error: {str(e)}")
        return redirect(url_for("home"))
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


# ---- LOGOUT ----
@app.route("/logout")
def logout():
    session.clear()
    flash("Logged out successfully.")
    return redirect(url_for("home"))


# ---- REGISTER ----
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        domain_id = request.form.get("domain_id")
        domain_name = request.form.get("domain_name")
        email = request.form.get("email")
        password = request.form.get("password")
        mobile_number = request.form.get("mobile_number")

        if not all([domain_id, domain_name, email, password, mobile_number]):
            flash("All fields are required!")
            return redirect(url_for("register"))

        conn = None
        cursor = None
        try:
            conn = get_conn()
            cursor = conn.cursor()

            # verify domain exists in RelianceEmployees
            cursor.execute(
                "SELECT DomainId FROM RelianceEmployees WHERE DomainId=%s",
                (domain_id,),
            )
            if not cursor.fetchone():
                flash("Domain ID does not exist in RelianceEmployees")
                return redirect(url_for("register"))

            cursor.execute(
                "SELECT DomainId FROM RegisteredEmployees WHERE DomainId=%s",
                (domain_id,),
            )
            if cursor.fetchone():
                cursor.execute(
                    """
                    UPDATE RegisteredEmployees
                    SET DomainName=%s, Email=%s, Password=%s, MobileNumber=%s
                    WHERE DomainId=%s
                    """,
                    (domain_name, email, password, mobile_number, domain_id),
                )
                flash("Registration Updated Successfully.")
            else:
                cursor.execute(
                    """
                    INSERT INTO RegisteredEmployees
                    (DomainId, DomainName, Email, Password, MobileNumber)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (domain_id, domain_name, email, password, mobile_number),
                )
                flash("Registration Successful! You can now login.")
            conn.commit()
            return redirect(url_for("home"))
        except Exception as e:
            flash(f"Registration Error: {str(e)}")
            return redirect(url_for("register"))
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()

    return render_template("register.html")


# ---- ENTER DETAILS (employee page) ----
@app.route("/enter_details")
def enter_details():
    if not require_login():
        flash("Please login first.")
        return redirect(url_for("home"))
    return render_template("enter_details.html")


# ---- SUBMIT VEHICLE PASS ----
@app.route("/submit_vehicle_pass", methods=["POST"])
def submit_vehicle_pass():
    if not require_login():
        flash("Please login first.")
        return redirect(url_for("home"))

    domain_id = session.get("DomainId")
    form = request.form
    conn = None
    cursor = None
    try:
        conn = get_conn()
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO VehicleAccessRequests (
                RequestedBy, VehicleType, TypeOfVehicle, AccessLocation, VehicleNo,
                EngineNo, ChassisNo, Model, OwnerUsername, Address, ContactNo,
                DriverName, DriverAddress, FromDate, ToDate, HODApproval, SecurityApproval
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'Pending', 'Pending')
            """,
            (
                domain_id,
                form.get("vehicle_type") or form.get("VehicleType"),
                form.get("type_of_vehicle") or form.get("TypeOfVehicle"),
                form.get("access_location") or form.get("AccessLocation"),
                form.get("vehicle_no") or form.get("VehicleNo"),
                form.get("engine_no") or form.get("EngineNo"),
                form.get("chassis_no") or form.get("ChassisNo"),
                form.get("model") or form.get("Model"),
                form.get("owner_username") or form.get("OwnerUsername"),
                form.get("address") or form.get("Address"),
                form.get("contact_no") or form.get("ContactNo"),
                form.get("driver_name") or form.get("DriverName"),
                form.get("driver_address") or form.get("DriverAddress"),
                form.get("from_date") or form.get("FromDate"),
                form.get("to_date") or form.get("ToDate"),
            ),
        )
        conn.commit()
        flash("Pass Request Generated")
        return redirect(url_for("enter_details"))
    except Exception as e:
        flash(f"Error submitting request: {str(e)}")
        return redirect(url_for("enter_details"))
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


# ---- CHECK PASS STATUS (employee) ----
@app.route("/check_pass_status")
def check_pass_status():
    if not require_login():
        flash("Please login first.")
        return redirect(url_for("home"))

    domain_id = session.get("DomainId")
    conn = None
    cursor = None
    requests = []
    try:
        conn = get_conn()
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT RequestId, RequestedBy, VehicleType, TypeOfVehicle, AccessLocation,
                   VehicleNo, EngineNo, ChassisNo, Model, OwnerUsername, Address, ContactNo,
                   DriverName, DriverAddress, FromDate, ToDate, HODApproval, SecurityApproval
            FROM VehicleAccessRequests
            WHERE RequestedBy=%s
            ORDER BY RequestId DESC
            """,
            (domain_id,),
        )
        rows = cursor.fetchall()
        for r in rows:
            requests.append({
                "RequestId": r[0], "RequestedBy": r[1], "VehicleType": r[2],
                "TypeOfVehicle": r[3], "AccessLocation": r[4], "VehicleNo": r[5],
                "EngineNo": r[6], "ChassisNo": r[7], "Model": r[8],
                "OwnerUsername": r[9], "Address": r[10], "ContactNo": r[11],
                "DriverName": r[12], "DriverAddress": r[13],
                "FromDate": r[14], "ToDate": r[15],
                "HODApproval": r[16], "SecurityApproval": r[17],
            })
    except Exception as e:
        flash(f"Error fetching status: {str(e)}")
        return redirect(url_for("enter_details"))
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

    return render_template("pass.html", requests=requests)


# ---- DOWNLOAD PDF (employee/admin) ----
@app.route("/download_pdf")
def download_pdf():
    request_id = request.args.get("request_id") or request.args.get("id")
    if not request_id:
        flash("Missing request id.")
        return redirect(url_for("home"))
    try:
        request_id = int(request_id)
    except Exception:
        flash("Invalid request id.")
        return redirect(url_for("home"))

    conn = None
    cursor = None
    try:
        conn = get_conn()
        cursor = conn.cursor()
        row = fetch_request_by_id(cursor, request_id)
        if not row:
            flash("Request not found.")
            return redirect(url_for("home"))
        if row[16] != "Approved" or row[17] != "Approved":
            flash("Pass is not fully approved yet.")
            return redirect(url_for("home"))

        buffer = io.BytesIO()
        p = canvas.Canvas(buffer, pagesize=A4)
        p.setFont("Helvetica-Bold", 16)
        p.drawString(50, 800, "Vehicle Access Pass")
        p.setFont("Helvetica", 11)
        y = 770
        pairs = [
            ("RequestId", row[0]), ("RequestedBy", row[1]), ("VehicleType", row[2]),
            ("TypeOfVehicle", row[3]), ("AccessLocation", row[4]), ("VehicleNo", row[5]),
            ("EngineNo", row[6]), ("ChassisNo", row[7]), ("Model", row[8]),
            ("OwnerUsername", row[9]), ("Address", row[10]), ("ContactNo", row[11]),
            ("DriverName", row[12]), ("DriverAddress", row[13]),
            ("FromDate", row[14]), ("ToDate", row[15]),
            ("HODApproval", row[16]), ("SecurityApproval", row[17])
        ]
        for label, val in pairs:
            p.drawString(50, y, f"{label}: {val}")
            y -= 18
            if y < 50:
                p.showPage()
                y = 800
        p.showPage()
        p.save()
        buffer.seek(0)
        filename = f"vehicle_pass_{request_id}.pdf"
        return send_file(buffer, as_attachment=True, download_name=filename, mimetype="application/pdf")
    except Exception as e:
        flash(f"Error generating PDF: {str(e)}")
        return redirect(url_for("home"))
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


# -------------------------
# HOD: profile & requests
# -------------------------
@app.route("/hod")
def hod():
    if not require_login() or not require_role("HOD"):
        flash("Access denied. HOD only.")
        return redirect(url_for("home"))
    return render_template("hod.html")


@app.route("/hod_details")
def hod_details():
    if not require_login() or not require_role("HOD"):
        flash("Access denied.")
        return redirect(url_for("home"))
    domain = session.get("DomainId")
    conn = None
    cursor = None
    try:
        conn = get_conn()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT DomainId, DomainName, Department, Email, MobileNumber FROM HOD WHERE DomainId=%s",
            (domain,),
        )
        row = cursor.fetchone()
        hod = None
        if row:
            hod = {
                "DomainId": row[0], "DomainName": row[1],
                "Department": row[2], "Email": row[3], "MobileNumber": row[4]
            }
        return render_template("hod_details.html", hod=hod)
    except Exception as e:
        flash(f"Error loading HOD details: {str(e)}")
        return redirect(url_for("hod"))
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


@app.route("/hod_requests")
def hod_requests():
    if not require_login() or not require_role("HOD"):
        flash("Access denied. HOD only.")
        return redirect(url_for("home"))
    conn = None
    cursor = None
    requests = []
    try:
        conn = get_conn()
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT RequestId, RequestedBy, VehicleType, AccessLocation, FromDate, ToDate, HODApproval
            FROM VehicleAccessRequests
            WHERE HODApproval='Pending'
            ORDER BY RequestId DESC
            """
        )
        for r in cursor.fetchall():
            requests.append({
                "RequestId": r[0], "RequestedBy": r[1], "VehicleType": r[2],
                "AccessLocation": r[3], "FromDate": r[4], "ToDate": r[5], "HODApproval": r[6]
            })
        return render_template("hod_requests.html", requests=requests)
    except Exception as e:
        flash(f"Error loading HOD requests: {str(e)}")
        return redirect(url_for("hod"))
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


@app.route("/approve_request/<int:request_id>", methods=["POST"])
def approve_request(request_id):
    if not require_login() or not require_role("HOD"):
        flash("Access denied.")
        return redirect(url_for("home"))
    new_status = request.form.get("status") or "Approved"
    if new_status not in ("Pending", "Approved"):
        flash("Invalid status.")
        return redirect(url_for("hod_requests"))

    conn = None
    cursor = None
    try:
        conn = get_conn()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE VehicleAccessRequests SET HODApproval=%s WHERE RequestId=%s",
            (new_status, request_id),
        )
        conn.commit()
        flash(f"HOD status updated to {new_status} for request {request_id}")
        return redirect(url_for("hod_requests"))
    except Exception as e:
        flash(f"Error updating HOD status: {str(e)}")
        return redirect(url_for("hod_requests"))
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


@app.route("/delete_request/<int:request_id>", methods=["POST"])
def delete_request(request_id):
    if not require_login():
        flash("Please login first.")
        return redirect(url_for("home"))

    domain = session.get("DomainId")
    role = session.get("Role")
    conn = None
    cursor = None
    try:
        conn = get_conn()
        cursor = conn.cursor()

        cursor.execute(
            "SELECT RequestedBy FROM VehicleAccessRequests WHERE RequestId=%s",
            (request_id,),
        )
        row = cursor.fetchone()
        if not row:
            flash("Request not found.")
            return redirect(url_for("home"))
        owner = row[0]
        if role in ("Admin", "HOD", "Security") or owner == domain:
            cursor.execute(
                "DELETE FROM VehicleAccessRequests WHERE RequestId=%s",
                (request_id,),
            )
            conn.commit()
            flash(f"Request {request_id} deleted.")
            if role == "HOD":
                return redirect(url_for("hod_requests"))
            if role == "Security":
                return redirect(url_for("security_requests"))
            if role == "Admin":
                return redirect(url_for("admin"))
            return redirect(url_for("enter_details"))
        else:
            flash("You are not authorized to delete this request.")
            return redirect(url_for("home"))
    except Exception as e:
        flash(f"Error deleting request: {str(e)}")
        return redirect(url_for("home"))
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


# -------------------------
# SECURITY
# -------------------------
@app.route("/security")
def security():
    if not require_login() or not require_role("Security"):
        flash("Access denied. Security only.")
        return redirect(url_for("home"))
    return render_template("security.html")


@app.route("/security_details")
def security_details():
    if not require_login() or not require_role("Security"):
        flash("Access denied.")
        return redirect(url_for("home"))
    domain = session.get("DomainId")
    conn = None
    cursor = None
    try:
        conn = get_conn()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT DomainId, DomainName, Email, MobileNumber FROM Security WHERE DomainId=%s",
            (domain,),
        )
        row = cursor.fetchone()
        security = None
        if row:
            security = {"DomainId": row[0], "DomainName": row[1], "Email": row[2], "MobileNumber": row[3]}
        return render_template("security_details.html", security=security)
    except Exception as e:
        flash(f"Error loading security details: {str(e)}")
        return redirect(url_for("security"))
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


@app.route("/security_requests")
def security_requests():
    if not require_login() or not require_role("Security"):
        flash("Access denied. Security only.")
        return redirect(url_for("home"))
    conn = None
    cursor = None
    requests = []
    try:
        conn = get_conn()
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT RequestId, RequestedBy, VehicleType, AccessLocation, FromDate, ToDate, HODApproval, SecurityApproval
            FROM VehicleAccessRequests
            WHERE HODApproval='Approved' AND SecurityApproval='Pending'
            ORDER BY RequestId DESC
            """
        )
        for r in cursor.fetchall():
            requests.append({
                "RequestId": r[0], "RequestedBy": r[1], "VehicleType": r[2],
                "AccessLocation": r[3], "FromDate": r[4], "ToDate": r[5],
                "HODApproval": r[6], "SecurityApproval": r[7]
            })
        return render_template("security_requests.html", requests=requests)
    except Exception as e:
        flash(f"Error loading Security requests: {str(e)}")
        return redirect(url_for("security"))
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


@app.route("/security_approve/<int:request_id>", methods=["POST"])
def security_approve(request_id):
    if not require_login() or not require_role("Security"):
        flash("Access denied.")
        return redirect(url_for("home"))
    new_status = request.form.get("status") or "Approved"
    if new_status not in ("Pending", "Approved"):
        flash("Invalid status.")
        return redirect(url_for("security_requests"))
    conn = None
    cursor = None
    try:
        conn = get_conn()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE VehicleAccessRequests SET SecurityApproval=%s WHERE RequestId=%s",
            (new_status, request_id),
        )
        conn.commit()
        flash(f"Security status updated to {new_status} for request {request_id}")
        return redirect(url_for("security_requests"))
    except Exception as e:
        flash(f"Error updating Security status: {str(e)}")
        return redirect(url_for("security_requests"))
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


# -------------------------
# ADMIN
# -------------------------
@app.route("/admin")
def admin():
    if not require_login() or not require_role("Admin"):
        flash("Access denied. Admin only.")
        return redirect(url_for("home"))

    conn = None
    cursor = None
    stats = {}
    recent = []
    employees = []
    try:
        conn = get_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM VehicleAccessRequests")
        stats["total_requests"] = cursor.fetchone()[0] or 0
        cursor.execute("SELECT COUNT(*) FROM VehicleAccessRequests WHERE HODApproval='Pending'")
        stats["hod_pending"] = cursor.fetchone()[0] or 0
        cursor.execute("SELECT COUNT(*) FROM VehicleAccessRequests WHERE HODApproval='Approved' AND SecurityApproval='Pending'")
        stats["security_pending"] = cursor.fetchone()[0] or 0
        cursor.execute("SELECT COUNT(*) FROM VehicleAccessRequests WHERE SecurityApproval='Approved'")
        stats["approved"] = cursor.fetchone()[0] or 0
        cursor.execute("SELECT COUNT(*) FROM VehicleAccessRequests WHERE HODApproval='Rejected' OR SecurityApproval='Rejected'")
        stats["rejected"] = cursor.fetchone()[0] or 0

        cursor.execute(
            """
            SELECT RequestId, RequestedBy, VehicleNo, FromDate, ToDate, HODApproval, SecurityApproval
            FROM VehicleAccessRequests
            ORDER BY RequestId DESC
            LIMIT 20
            """
        )
        for r in cursor.fetchall():
            recent.append({
                "RequestId": r[0], "RequestedBy": r[1], "VehicleNo": r[2],
                "FromDate": r[3], "ToDate": r[4], "HODApproval": r[5], "SecurityApproval": r[6]
            })

        cursor.execute("SELECT DomainId, DomainName, Email, MobileNumber FROM RegisteredEmployees")
        for e in cursor.fetchall():
            employees.append({"DomainId": e[0], "DomainName": e[1], "Email": e[2], "MobileNumber": e[3]})

        return render_template("admin.html", stats=stats, requests=recent, employees=employees)
    except Exception as e:
        flash(f"Error loading admin data: {str(e)}")
        return redirect(url_for("home"))
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


@app.route("/details")
@app.route("/details/<int:request_id>")
def details(request_id=None):
    if not require_login() or not require_role("Admin"):
        flash("Access denied. Admin only.")
        return redirect(url_for("home"))

    req = None
    if request_id:
        conn = None
        cursor = None
        try:
            conn = get_conn()
            cursor = conn.cursor()
            r = fetch_request_by_id(cursor, request_id)
            if r:
                req = {
                    "RequestId": r[0], "RequestedBy": r[1], "VehicleType": r[2],
                    "TypeOfVehicle": r[3], "AccessLocation": r[4], "VehicleNo": r[5],
                    "EngineNo": r[6], "ChassisNo": r[7], "Model": r[8],
                    "OwnerUsername": r[9], "Address": r[10], "ContactNo": r[11],
                    "DriverName": r[12], "DriverAddress": r[13],
                    "FromDate": r[14], "ToDate": r[15], "HODApproval": r[16],
                    "SecurityApproval": r[17]
                }
        except Exception as e:
            flash(f"Error loading request detail: {str(e)}")
            return redirect(url_for("admin"))
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()

    return render_template("details.html", req=req)


@app.route("/dashboard")
def dashboard():
    if not require_login():
        flash("Please login first.")
        return redirect(url_for("home"))
    return render_template("dashboard.html")



@app.route("/get_table_data/<table>")
def get_table_data(table):

    conn = get_conn()
    cur = conn.cursor()

    try:
        # 🔥 IMPORTANT: use quotes (your tables are case-sensitive)
        query = f'SELECT * FROM "{table}"'
        print("Executing:", query)  # debug

        cur.execute(query)

        columns = [desc[0] for desc in cur.description]
        rows = cur.fetchall()

        result = [dict(zip(columns, row)) for row in rows]

        return jsonify(result)

    except Exception as e:
        print("ERROR:", e)   # 👈 YOU MUST CHECK THIS
        return jsonify({"error": str(e)})

    finally:
        cur.close()
        conn.close()

@app.route("/update_table", methods=["POST"])
def update_table():
    data = request.json
    table = data["table"]
    rows = data["rows"]

    conn = get_conn()
    cur = conn.cursor()

    try:

        # -----------------------------
        # RegisteredEmployees
        # -----------------------------
        if table == "RegisteredEmployees":
            for row in rows:
                domain_id = row.get("DomainId", "").strip()
                if not domain_id:
                    continue

                cur.execute("""SELECT COUNT(*) FROM "RegisteredEmployees" WHERE "DomainId"=%s""", (domain_id,))
                exists = cur.fetchone()[0]

                if exists == 0:
                    cur.execute("""
                        INSERT INTO "RegisteredEmployees"
                        ("DomainId","DomainName","Email","Password","MobileNumber")
                        VALUES (%s,%s,%s,%s,%s)
                    """, (
                        domain_id,
                        row.get("DomainName",""),
                        row.get("Email",""),
                        "default123",
                        row.get("MobileNumber","")
                    ))
                    print("INSERTED EMP:", domain_id)
                else:
                    cur.execute("""
                        UPDATE "RegisteredEmployees"
                        SET "DomainName"=%s,
                            "Email"=%s,
                            "MobileNumber"=%s
                        WHERE "DomainId"=%s
                    """, (
                        row.get("DomainName",""),
                        row.get("Email",""),
                        row.get("MobileNumber",""),
                        domain_id
                    ))
                    print("UPDATED EMP:", domain_id)

        # -----------------------------
        # RelianceEmployees
        # -----------------------------
        elif table == "RelianceEmployees":
            for row in rows:
                domain_id = row.get("DomainId", "").strip()
                if not domain_id:
                    continue

                cur.execute("""SELECT COUNT(*) FROM "RelianceEmployees" WHERE "DomainId"=%s""", (domain_id,))
                exists = cur.fetchone()[0]

                if exists == 0:
                    cur.execute("""
                        INSERT INTO "RelianceEmployees" ("DomainId")
                        VALUES (%s)
                    """, (domain_id,))
                    print("INSERTED REL:", domain_id)

        # -----------------------------
        # Admin
        # -----------------------------
        elif table == "Admin":
            for row in rows:
                domain_id = row.get("DomainId","").strip()
                if not domain_id:
                    continue

                cur.execute("""
                    UPDATE "Admin"
                    SET "DomainName"=%s,
                        "Email"=%s,
                        "MobileNumber"=%s
                    WHERE "DomainId"=%s
                """, (
                    row.get("DomainName",""),
                    row.get("Email",""),
                    row.get("MobileNumber",""),
                    domain_id
                ))
                print("UPDATED ADMIN:", domain_id)

        # -----------------------------
        # HOD
        # -----------------------------
        elif table == "HOD":
            for row in rows:
                user_id = row.get("UserId")

                cur.execute("""SELECT COUNT(*) FROM "HOD" WHERE "UserId"=%s""", (user_id,))
                exists = cur.fetchone()[0]

                if exists == 0:
                    cur.execute("""
                        INSERT INTO "HOD"
                        ("DomainId","DomainName","Password","Department","Email","MobileNumber")
                        VALUES (%s,%s,%s,%s,%s,%s)
                    """, (
                        row.get("DomainId",""),
                        row.get("DomainName",""),
                        row.get("Password",""),
                        row.get("Department",""),
                        row.get("Email",""),
                        row.get("MobileNumber","")
                    ))
                    print("INSERTED HOD")
                else:
                    cur.execute("""
                        UPDATE "HOD"
                        SET "DomainId"=%s,
                            "DomainName"=%s,
                            "Password"=%s,
                            "Department"=%s,
                            "Email"=%s,
                            "MobileNumber"=%s
                        WHERE "UserId"=%s
                    """, (
                        row.get("DomainId",""),
                        row.get("DomainName",""),
                        row.get("Password",""),
                        row.get("Department",""),
                        row.get("Email",""),
                        row.get("MobileNumber",""),
                        user_id
                    ))
                    print("UPDATED HOD:", user_id)

        # -----------------------------
        # Security
        # -----------------------------
        elif table == "Security":
            for row in rows:
                user_id = row.get("UserId")

                cur.execute("""SELECT COUNT(*) FROM "Security" WHERE "UserId"=%s""", (user_id,))
                exists = cur.fetchone()[0]

                if exists == 0:
                    cur.execute("""
                        INSERT INTO "Security"
                        ("DomainId","DomainName","Password","Email","MobileNumber")
                        VALUES (%s,%s,%s,%s,%s)
                    """, (
                        row.get("DomainId",""),
                        row.get("DomainName",""),
                        row.get("Password",""),
                        row.get("Email",""),
                        row.get("MobileNumber","")
                    ))
                    print("INSERTED SECURITY")
                else:
                    cur.execute("""
                        UPDATE "Security"
                        SET "DomainId"=%s,
                            "DomainName"=%s,
                            "Password"=%s,
                            "Email"=%s,
                            "MobileNumber"=%s
                        WHERE "UserId"=%s
                    """, (
                        row.get("DomainId",""),
                        row.get("DomainName",""),
                        row.get("Password",""),
                        row.get("Email",""),
                        row.get("MobileNumber",""),
                        user_id
                    ))
                    print("UPDATED SECURITY:", user_id)

        # -----------------------------
        # VehicleAccessRequests
        # -----------------------------
        elif table == "VehicleAccessRequests":
            for row in rows:
                request_id = row.get("RequestId")

                cur.execute("""SELECT COUNT(*) FROM "VehicleAccessRequests" WHERE "RequestId"=%s""", (request_id,))
                exists = cur.fetchone()[0]

                if exists == 0:
                    cur.execute("""
                        INSERT INTO "VehicleAccessRequests"
                        ("RequestedBy","VehicleType","TypeOfVehicle","AccessLocation","VehicleNo",
                         "EngineNo","ChassisNo","Model","OwnerUsername","Address","ContactNo",
                         "DriverName","DriverAddress","FromDate","ToDate","HODApproval","SecurityApproval")
                        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                    """, (
                        row.get("RequestedBy",""),
                        row.get("VehicleType",""),
                        row.get("TypeOfVehicle",""),
                        row.get("AccessLocation",""),
                        row.get("VehicleNo",""),
                        row.get("EngineNo",""),
                        row.get("ChassisNo",""),
                        row.get("Model",""),
                        row.get("OwnerUsername",""),
                        row.get("Address",""),
                        row.get("ContactNo",""),
                        row.get("DriverName",""),
                        row.get("DriverAddress",""),
                        row.get("FromDate"),
                        row.get("ToDate"),
                        row.get("HODApproval","Pending"),
                        row.get("SecurityApproval","Pending")
                    ))
                    print("INSERTED REQUEST")
                else:
                    cur.execute("""
                        UPDATE "VehicleAccessRequests"
                        SET "HODApproval"=%s,
                            "SecurityApproval"=%s
                        WHERE "RequestId"=%s
                    """, (
                        row.get("HODApproval",""),
                        row.get("SecurityApproval",""),
                        request_id
                    ))
                    print("UPDATED REQUEST:", request_id)

        conn.commit()
        print("COMMIT SUCCESS ✅")

        return jsonify({"status": "success"})

    except Exception as e:
        print("ERROR ❌:", e)
        return jsonify({"error": str(e)})

    finally:
        cur.close()
        conn.close()
























# -------------------------
# RUN
# -------------------------
if __name__ == "__main__":
    app.run(debug=True)





