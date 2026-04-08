from flask import Flask, render_template, request, redirect, url_for
import sqlite3
import os

app = Flask(__name__)

# =========================
# DATABASE PATH
# =========================
DB_FOLDER = "database"
DB_NAME = os.path.join(DB_FOLDER, "expenses.db")


# =========================
# CREATE DATABASE
# =========================
def init_db():
    os.makedirs(DB_FOLDER, exist_ok=True)

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

    cur.execute("""
        CREATE TABLE IF NOT EXISTS budget (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            amount REAL NOT NULL
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


@app.route('/summary')
def summary():
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()

    selected_month = request.args.get("month")
    selected_year = request.args.get("year")
    selected_category = request.args.get("category")

    query = "SELECT name, amount, category, date FROM expenses WHERE 1=1"
    params = []

    if selected_month:
        query += " AND strftime('%m', date)=?"
        params.append(selected_month.zfill(2))

    if selected_year:
        query += " AND strftime('%Y', date)=?"
        params.append(selected_year)

    if selected_category:
        query += " AND category=?"
        params.append(selected_category)

    cur.execute(query, params)
    expenses = cur.fetchall()

    total = sum(row[1] for row in expenses)

    # Pie chart data
    category_totals = {}
    for row in expenses:
        cat = row[2]
        category_totals[cat] = category_totals.get(cat, 0) + row[1]

    labels = list(category_totals.keys())
    values = list(category_totals.values())

    # Monthly comparison bar chart
    cur.execute("""
        SELECT strftime('%m', date) as month, SUM(amount)
        FROM expenses
        GROUP BY month
        ORDER BY month
    """)
    monthly_rows = cur.fetchall()

    bar_labels = [f"Month {m}" for m, _ in monthly_rows]
    bar_values = [v for _, v in monthly_rows]

    # Calendar-style daily totals (THIS FIXES YOUR ERROR)
    cur.execute("""
        SELECT strftime('%d/%m/%Y', date), SUM(amount)
        FROM expenses
        GROUP BY date
        ORDER BY date DESC
        LIMIT 10
    """)
    calendar_rows = cur.fetchall()

    calendar_data = [
        {"date": row[0], "amount": row[1]}
        for row in calendar_rows
    ]

    # ===== BUDGET STATUS =====
    budget_amount = 0
    budget_status = "No Budget Set"
    budget_color = "gray"

    cur.execute(
    "SELECT amount FROM budget WHERE month=? AND year=? ORDER BY id DESC LIMIT 1",
    (selected_month, selected_year)
    )
    budget_row = cur.fetchone()

    if budget_row:
     budget_amount = float(budget_row[0])

    if total > budget_amount:
        budget_status = "Budget Exceeded"
        budget_color = "red"
    elif total >= budget_amount / 2:
        budget_status = "Budget More Than Half Used"
        budget_color = "orange"
    else:
        budget_status = "Budget Under Control"
        budget_color = "green"

# CLOSE ONLY HERE
    conn.close()

    return render_template(
    "summary.html",
    total=total,
    labels=labels,
    values=values,
    bar_labels=bar_labels,
    bar_values=bar_values,
    calendar_data=calendar_data,
    selected_month=selected_month,
    selected_year=selected_year,
    selected_category=selected_category,
    budget_amount=budget_amount,
    budget_status=budget_status,
    budget_color=budget_color
)
    
@app.route("/budget", methods=["GET", "POST"])
def budget():
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()

    # recreate clean budget table
    cur.execute("DROP TABLE IF EXISTS budget")
    cur.execute("""
        CREATE TABLE budget (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            month TEXT,
            year TEXT,
            amount REAL
        )
    """)

    if request.method == "POST":
        month = request.form.get("month")
        year = request.form.get("year")
        amount = request.form.get("amount")

        cur.execute(
            "INSERT INTO budget (month, year, amount) VALUES (?, ?, ?)",
            (month, year, amount)
        )
        conn.commit()

    cur.execute("SELECT * FROM budget ORDER BY id DESC")
    budgets = cur.fetchall()

    conn.close()

    return render_template("budget.html", budgets=budgets)

# =========================
# RUN APP
# =========================
if __name__ == "__main__":
    init_db()
    app.run(debug=True)