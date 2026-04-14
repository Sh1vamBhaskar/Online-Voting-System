from flask import Flask, render_template, request, redirect, session
from flask_mail import Mail, Message
from datetime import datetime
import random
import sqlite3
import os


app = Flask(__name__)
app.secret_key = "college_voting_secret"
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'shivamayush2023@gmail.com'
app.config['MAIL_PASSWORD'] = 'trskagvrdntgoqoh'

mail = Mail(app)
ADMIN_USER = "admin"
ADMIN_PASS = "@dmin123"
ELECTION_END = "2026-12-31 23:59:59"

DB_PATH = os.path.join(os.path.dirname(__file__), "database.db")


def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # Students table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS students(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            roll_no TEXT UNIQUE,
            password TEXT,
            has_voted INTEGER DEFAULT 0
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS vote_audit (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT,
            voted_at TEXT
        )
    """)

    # Candidates table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS candidates(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            image TEXT,
            votes INTEGER DEFAULT 0
        )
    """)

    # Seed 50 students (101-150)
    students = [(str(i), f"pass{i}") for i in range(101, 201)]
    for s in students:
        try:
            cur.execute(
                "INSERT INTO students (roll_no, password) VALUES (?, ?)",
                s,
            )
        except sqlite3.IntegrityError:
            pass

    #CREATE TABLE IF NOT EXISTS candidate_requests
    cur.execute("""
        CREATE TABLE IF NOT EXISTS candidate_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name TEXT,
            reg_no TEXT,
            email TEXT,
            course TEXT,
            branch TEXT,
            specialization TEXT,
            position TEXT,
            photo TEXT,
            status TEXT DEFAULT 'Pending'
        )
        """)
     
    # Seed 10 candidates with custom names + images
    candidate_data = [
                        ("Aman Sharma", "aman.jpg"),
                        ("Vaibhav Raj", "vaibhav.jpg"),
                        ("Priya Mishra", "priya.jpg"),
                        ("Pravesh Sahu", "pravesh.jpg"),
                        ("Shubhra Jha", "shubhra.jpg"),
                        ("Aarohi Jain", "aarohi.jpg"),
                        ("Rohit Saxena", "rohit.jpg"),
                        ("Prem Kashyap", "prem.jpg"),
                        ("Swati Shree", "swati.jpg"),
                        ("Tanshika Bhratacharya", "Tanishka.jpg"),
                    ]

    cur.execute("SELECT COUNT(*) FROM candidates")
    count = cur.fetchone()[0]

    if count == 0:
        for name, image in candidate_data:
            cur.execute(
            "INSERT INTO candidates (name, image) VALUES (?, ?)",
            (name, image)
        )

    conn.commit()
    conn.close()


init_db()


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        roll_no = request.form["roll_no"]
        password = request.form["password"]
        email = request.form["email"]
        if not email.endswith("@srmist.edu.in"):
            return render_template(
                "message.html",
                title="📧 Invalid Email",
                message="Please use your official college email ID.",
                back_url="/login",
            )

        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute(
            "SELECT * FROM students WHERE roll_no=? AND password=?",
            (roll_no, password),
        )
        student = cur.fetchone()
        conn.close()

        if student:
            otp = str(random.randint(100000, 999999))
            session["pending_roll_no"] = roll_no
            session["pending_email"] = email
            session["otp"] = otp

            msg = Message(
                "College Voting OTP",
                sender=app.config["MAIL_USERNAME"],
                recipients=[email]
            )
            msg.body = f"Your OTP for voting login is: {otp}"
            mail.send(msg)
            print("OTP SENT:", otp)

            return redirect("/verify_otp")

        return render_template(
            "message.html",
            title="❌ Login Failed",
            message="Invalid credentials. Please check roll number and password.",
            back_url="/login",
            )

    return render_template("login.html")

#adding BACKEND ROUTE to Save candidate request

@app.route("/candidate_register", methods=["GET", "POST"])
def candidate_register():
    if request.method == "POST":
        full_name = request.form["full_name"]
        reg_no = request.form["reg_no"]
        email = request.form["email"]
        course = request.form["course"]
        branch = request.form["branch"]
        specialization = request.form["specialization"]
        position = request.form["position"]

        photo = request.files["photo"]
        filename = photo.filename
        photo.save(os.path.join("static/candidates_images", filename))

        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO candidate_requests
            (full_name, reg_no, email, course, branch, specialization, position, photo)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            full_name,
            reg_no,
            email,
            course,
            branch,
            specialization,
            position,
            filename
        ))
        conn.commit()
        conn.close()

        return redirect("/candidate_success")

    return render_template("candidate_register.html")
@app.route("/candidate_success")
def candidate_success():
    return render_template(
        "message.html",
        title="✅ Request Submitted",
        message="Your request has been submitted successfully. Wait for admin approval.",
        back_url="/candidate_register"
    )

@app.route("/verify_otp", methods=["GET", "POST"])
def verify_otp():
    if request.method == "POST":
        entered_otp = request.form["otp"]

        if entered_otp == session.get("otp"):
            session["roll_no"] = session.get("pending_roll_no")
            session["email"] = session.get("pending_email")
            session.pop("otp", None)
            session.pop("pending_roll_no", None)
            session.pop("pending_email", None)
            return redirect("/vote")

        return render_template(
                "message.html",
                title="🔐 OTP Failed",
                message="The OTP entered is incorrect. Please try again.",
                back_url="/verify_otp",
            )

    return render_template("verify_otp.html")


@app.route("/vote", methods=["GET", "POST"])
def vote():
    if "roll_no" not in session:
        return redirect("/login")

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute(
        "SELECT has_voted FROM students WHERE roll_no=?",
        (session["roll_no"],),
    )
    voted = cur.fetchone()[0]

    if voted:
        conn.close()
        return redirect("/result")

    if request.method == "POST":
        candidate_id = request.form["candidate"]

        cur.execute(
            "UPDATE candidates SET votes = votes + 1 WHERE id=?",
            (candidate_id,),
        )
        cur.execute(
            "UPDATE students SET has_voted=1 WHERE roll_no=?",
            (session["roll_no"],),
        )
        email = session.get("email")

        cur.execute(
            "INSERT INTO vote_audit (email, voted_at) VALUES (?, ?)",
            (email, datetime.now().strftime("%d-%m-%Y %I:%M %p"))
        )

        conn.commit()
        conn.close()
        return redirect("/result")

    cur.execute("SELECT * FROM candidates")
    candidates = cur.fetchall()
    conn.close()

    return render_template("vote.html", candidates=candidates)


@app.route("/result")
def result():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT name, votes FROM candidates")
    results = cur.fetchall()
    conn.close()

    winner = max(results, key=lambda x: x[1]) if results else ("No candidates", 0)
    return render_template("result.html", results=results, winner=winner)

@app.route("/admin_login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        if username == ADMIN_USER and password == ADMIN_PASS:
            session["admin"] = True
            return redirect("/admin")
        return render_template(
                "message.html",
                title="🔐 Admin Login Failed",
                message="Invalid admin username or password.",
                back_url="/admin_login",
                )

    return render_template("admin_login.html")

@app.route("/admin")
def admin():
    if "admin" not in session:
        return redirect("/admin_login")

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # 📊 election results
    cur.execute("SELECT name, votes FROM candidates ORDER BY votes DESC")
    results = cur.fetchall()

    # 📥 pending candidate requests
    cur.execute("SELECT * FROM candidate_requests WHERE status='Pending'")
    requests = cur.fetchall()

    conn.close()

    return render_template(
        "admin.html",
        results=results,
        requests=requests
    )

@app.route("/audit_logs")
def audit_logs():
    if "admin" not in session:
        return redirect("/admin_login")

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("SELECT email, voted_at FROM vote_audit ORDER BY id DESC")
    logs = cur.fetchall()

    conn.close()

    return render_template("audit_logs.html", logs=logs)


@app.route("/add_candidate", methods=["POST"])
def add_candidate():
    if "admin" not in session:
        return redirect("/admin_login")

    name = request.form["name"]

    photo = request.files["photo"]
    filename = photo.filename
    photo.save(os.path.join("static/candidates_images", filename))

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO candidates (name, image, votes) VALUES (?, ?, 0)",
        (name, filename)
    )
    conn.commit()
    conn.close()

    return redirect("/admin")

@app.route("/delete_candidate/<int:id>")
def delete_candidate(id):
    if "admin" not in session:
        return redirect("/admin_login")

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("DELETE FROM candidates WHERE id=?", (id,))
    conn.commit()
    conn.close()

    return redirect("/admin")

#ADMIN ROUTES to either Approve / Reject
@app.route("/approve_candidate/<int:id>")
def approve_candidate(id):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("SELECT full_name, photo FROM candidate_requests WHERE id=?", (id,))
    req = cur.fetchone()

    cur.execute(
        "INSERT INTO candidates (name, image, votes) VALUES (?, ?, 0)",
        (req[0], req[1])
    )

    cur.execute("DELETE FROM candidate_requests WHERE id=?", (id,))
    conn.commit()
    conn.close()

    return redirect("/admin")


@app.route("/reject_candidate/<int:id>")
def reject_candidate(id):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("DELETE FROM candidate_requests WHERE id=?", (id,))
    conn.commit()
    conn.close()
    return redirect("/admin")


if __name__ == "__main__":
    app.run(debug=True)


