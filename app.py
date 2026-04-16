from flask import Flask, render_template, request, redirect, url_for
import sqlite3
from datetime import datetime
import os

app = Flask(__name__)
app.config['SECRECT KEY']=os.environ.get('SECRET_KEY')
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_NAME = os.path.join(BASE_DIR, "expenses.db")


# =========================
# CREATE DATABASE
# =========================
def init_db():
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            amount REAL NOT NULL,
            category TEXT NOT NULL,
            date TEXT NOT NULL
        )
    """)

    conn.commit()
    conn.close()


# =========================
# DB HELPERS
# =========================
def get_db():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


# =========================
# HOME
# =========================
@app.route("/")
def home():
    return render_template("home.html")


# =========================
# ADD EXPENSE
# =========================
@app.route("/add", methods=["GET", "POST"])
def add_expense():
    if request.method == "POST":
        name = request.form["name"]
        amount = request.form["amount"]
        category = request.form["category"]
        date = request.form["date"]

        conn = get_db()
        conn.execute(
            "INSERT INTO expenses (name, amount, category, date) VALUES (?, ?, ?, ?)",
            (name, amount, category, date)
        )
        conn.commit()
        conn.close()

        return redirect(url_for("summary"))

    return render_template("add_expense.html")


@app.route("/budget", methods=["GET", "POST"])
def budget():
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()

    # create budget table safely
    cur.execute("""
        CREATE TABLE IF NOT EXISTS budget (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            month INTEGER NOT NULL,
            year INTEGER NOT NULL,
            amount REAL NOT NULL,
            UNIQUE(month, year)
        )
    """)

    selected_month = int(request.values.get("month", datetime.now().month))
    selected_year = int(request.values.get("year", datetime.now().year))

    if request.method == "POST":
        amount = float(request.form.get("budget_amount", 0))

        cur.execute("""
            INSERT INTO budget (month, year, amount)
            VALUES (?, ?, ?)
            ON CONFLICT(month, year)
            DO UPDATE SET amount=excluded.amount
        """, (selected_month, selected_year, amount))

        conn.commit()
        conn.close()
        return redirect(url_for("budget", month=selected_month, year=selected_year))

    cur.execute(
        "SELECT amount FROM budget WHERE month=? AND year=?",
        (selected_month, selected_year),
    )
    row = cur.fetchone()
    saved_budget = row[0] if row else 0

    conn.close()

    return render_template(
        "budget.html",
        saved_budget=saved_budget,
        selected_month=selected_month,
        selected_year=selected_year,
    )


@app.route("/summary")
def summary():
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()

    selected_month = int(request.args.get("month", datetime.now().month))
    selected_year = int(request.args.get("year", datetime.now().year))
    selected_category = request.args.get("category", "All")

    # ensure budget table exists
    cur.execute("""
        CREATE TABLE IF NOT EXISTS budget (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            month INTEGER NOT NULL,
            year INTEGER NOT NULL,
            amount REAL NOT NULL,
            UNIQUE(month, year)
        )
    """)

    query = "SELECT category, SUM(amount) FROM expenses WHERE strftime('%m', date)=? AND strftime('%Y', date)=?"
    params = [f"{selected_month:02d}", str(selected_year)]

    if selected_category != "All":
        query += " AND category=?"
        params.append(selected_category)

    query += " GROUP BY category"

    cur.execute(query, params)
    rows = cur.fetchall()

    labels = [r[0] for r in rows] if rows else []
    values = [r[1] for r in rows] if rows else []
    total_spent = sum(values) if values else 0

    # monthly bar chart data
    cur.execute("""
        SELECT strftime('%d', date) as day, SUM(amount)
        FROM expenses
        WHERE strftime('%m', date)=? AND strftime('%Y', date)=?
        GROUP BY day
        ORDER BY day
    """, (f"{selected_month:02d}", str(selected_year)))

    bar_rows = cur.fetchall()
    bar_labels = [r[0] for r in bar_rows]
    bar_values = [r[1] for r in bar_rows]

    # get linked budget
    cur.execute(
        "SELECT amount FROM budget WHERE month=? AND year=?",
        (selected_month, selected_year),
    )
    row = cur.fetchone()
    budget_amount = row[0] if row else 0

    # status logic
    if budget_amount == 0:
        budget_status = "No budget set"
        budget_color = "gray"
    elif total_spent > budget_amount:
        budget_status = "Budget Exceeded"
        budget_color = "red"
    elif total_spent >= budget_amount * 0.5:
        budget_status = "Budget More Than Half"
        budget_color = "orange"
    else:
        budget_status = "Budget Under Control"
        budget_color = "green"

    conn.close()

    return render_template(
        "summary.html",
        labels=labels,
        values=values,
        total_spent=total_spent,
        budget_amount=budget_amount,
        budget_status=budget_status,
        budget_color=budget_color,
        bar_labels=bar_labels,
        bar_values=bar_values,
        selected_month=selected_month,
        selected_year=selected_year,
        selected_category=selected_category,
    )

 

# =========================
# RUN APP
# =========================
if __name__ == "__main__":
    init_db()
    app.run(debug=True)