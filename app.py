import sqlite3
import joblib
from flask import Flask, request, render_template_string, redirect, url_for

app = Flask(__name__)

# Load Trained AI Model
model = joblib.load("model.pkl")

# Database Initialization
def init_db():
    conn = sqlite3.connect("expenses.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS accounts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            account_name TEXT NOT NULL,
            balance REAL NOT NULL
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            amount REAL NOT NULL,
            description TEXT NOT NULL,
            category TEXT NOT NULL,
            account_id INTEGER,
            FOREIGN KEY (account_id) REFERENCES accounts (id)
        )
    """)
    
    cursor.execute("SELECT COUNT(*) FROM accounts")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO accounts (account_name, balance) VALUES ('Main Bank (SBI/HDFC)', 25000.0)")
    
    conn.commit()
    conn.close()

init_db()

# Helper Functions
def get_total_expense():
    conn = sqlite3.connect("expenses.db")
    cursor = conn.cursor()
    cursor.execute("SELECT SUM(amount) FROM expenses")
    result = cursor.fetchone()[0]
    conn.close()
    return result if result else 0.0

def get_expense_history():
    conn = sqlite3.connect("expenses.db")
    cursor = conn.cursor()
    cursor.execute("""
        SELECT e.amount, e.description, e.category, a.account_name 
        FROM expenses e 
        LEFT JOIN accounts a ON e.account_id = a.id 
        ORDER BY e.id DESC
    """)
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        return "<p style='color: #777;'>अजून कोणताही खर्च सेव्ह केलेला नाही.</p>"

    table_html = """
    <table>
        <tr>
            <th>Amount</th>
            <th>Description</th>
            <th>Category</th>
            <th>Paid Via Account</th>
        </tr>
    """
    for row in rows:
        acc = row[3] if row[3] else "General"
        table_html += f"<tr><td>₹{row[0]}</td><td>{row[1]}</td><td>{row[2]}</td><td>{acc}</td></tr>"
    
    table_html += "</table>"
    return table_html

def get_chart_data():
    conn = sqlite3.connect("expenses.db")
    cursor = conn.cursor()
    cursor.execute("SELECT category, SUM(amount) FROM expenses GROUP BY category")
    data = cursor.fetchall()
    conn.close()
    labels = [row[0] for row in data]
    values = [row[1] for row in data]
    return labels, values

def get_accounts_info():
    conn = sqlite3.connect("expenses.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id, account_name, balance FROM accounts")
    accounts = cursor.fetchall()
    conn.close()

    cards_html = ""
    options_html = ""
    for acc in accounts:
        cards_html += f"""
        <div class="card" style="border-left: 5px solid #28a745; min-width: 180px;">
            <span style="color: #666; font-size: 13px;">🏦 {acc[1]}</span>
            <h3 style="margin: 5px 0 0 0; color: #28a745;">₹{acc[2]}</h3>
        </div>
        """
        options_html += f'<option value="{acc[0]}">{acc[1]} (Balance: ₹{acc[2]})</option>'
    
    return cards_html, options_html

# HTML UI Template
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Smart Expense AI Assistant</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/animate.css/4.1.1/animate.min.css"/>
    <style>
        #splash-screen {
            position: fixed;
            top: 0; left: 0; width: 100%; height: 100%;
            background: linear-gradient(135deg, #007bff, #6c5ce7);
            display: flex; flex-direction: column; justify-content: center; align-items: center;
            z-index: 9999; color: white;
            transition: opacity 0.8s ease, visibility 0.8s ease;
        }
        .ai-icon-loader {
            width: 80px; height: 80px; background: white; border-radius: 50%;
            display: flex; justify-content: center; align-items: center;
            font-size: 36px; box-shadow: 0 0 20px rgba(255,255,255,0.5);
            animation: pulse 1.5s infinite ease-in-out;
        }
        @keyframes pulse {
            0% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(255, 255, 255, 0.7); }
            70% { transform: scale(1.05); box-shadow: 0 0 0 20px rgba(255, 255, 255, 0); }
            100% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(255, 255, 255, 0); }
        }
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 40px; background-color: #f4f7f6; color: #333; }
        .card { background: white; padding: 20px 25px; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.05); transition: transform 0.3s ease; }
        .card:hover { transform: translateY(-5px); }
        .btn-submit { padding: 12px 20px; background: #007bff; color: white; border: none; cursor: pointer; border-radius: 6px; width: 100%; font-weight: bold; }
        .btn-clear { padding: 8px 15px; background: #dc3545; color: white; border: none; cursor: pointer; border-radius: 6px; font-size: 13px; }
        table { border-collapse: collapse; background: white; width: 100%; border-radius: 8px; overflow: hidden; }
        th { background: #007bff; color: white; padding: 12px; text-align: left; }
        td { padding: 10px 12px; border-bottom: 1px solid #eee; }
        .input-box { padding: 10px; margin: 8px 0; width: 93%; border: 1px solid #ccc; border-radius: 4px; }
    </style>
</head>
<body>
    <div id="splash-screen">
        <div class="ai-icon-loader">🤖</div>
        <h1 class="animate__animated animate__zoomIn" style="margin-top: 20px;">Smart Expense AI</h1>
        <p class="animate__animated animate__fadeInUp">Loading your personal dashboard...</p>
    </div>

    <h1>Smart Expense & Finance AI Assistant</h1>

    <h3>Savings & Bank Accounts</h3>
    <div style="display: flex; gap: 20px; margin-bottom: 25px;">
        {{ account_cards | safe }}
    </div>

    <div style="display: flex; gap: 20px; margin-bottom: 25px;">
        <div class="card" style="border-left: 5px solid #007bff; min-width: 200px;">
            <span style="color: #666; font-size: 14px;">Total Spent (एकूण खर्च)</span>
            <h2 style="margin: 5px 0 0 0;">₹{{ total_expense }}</h2>
        </div>
        <div class="card" style="border-left: 5px solid #28a745; min-width: 200px;">
            <span style="color: #666; font-size: 14px;">Monthly Budget Limit</span>
            <h2 style="margin: 5px 0 0 0;">₹5,000.0</h2>
        </div>
    </div>

    <div style="display: flex; gap: 40px; align-items: flex-start;">
        <div class="card" style="width: 380px;">
            <h3>Add New Expense</h3>
            <form action="/predict" method="POST">
                <label><b>Amount:</b></label><br>
                <input type="number" step="any" name="amount" class="input-box" required><br><br>
                <label><b>Description:</b></label><br>
                <input type="text" name="description" placeholder="उदा. Pizza, Petrol..." class="input-box" required><br><br>
                <label><b>Select Account:</b></label><br>
                <select name="account_id" class="input-box" style="width: 98%;" required>
                    {{ account_options | safe }}
                </select><br><br>
                <button type="submit" class="btn-submit">Predict & Save Expense</button>
            </form>
        </div>

        <div class="card" style="width: 300px;">
            <h3>Add Bank Account</h3>
            <form action="/add_account" method="POST">
                <label><b>Account Name:</b></label><br>
                <input type="text" name="account_name" placeholder="उदा. ICICI Bank" class="input-box" required><br><br>
                <label><b>Initial Balance:</b></label><br>
                <input type="number" step="any" name="balance" placeholder="10000" class="input-box" required><br><br>
                <button type="submit" class="btn-submit" style="background: #28a745;">Add Account</button>
            </form>
        </div>

        <div class="card" style="width: 350px;">
            <h3>Expense Breakdown</h3>
            <canvas id="expenseChart" width="300" height="300"></canvas>
        </div>
    </div>

    {{ result_section | safe }}

    <div style="margin-top: 40px; display: flex; align-items: center; justify-content: space-between; width: 1100px;">
        <h2>All Saved Expenses</h2>
        <form action="/clear" method="POST" onsubmit="return confirm('सर्व खर्च डिलीट करायचे आहेत का?');">
            <button type="submit" class="btn-clear">Clear All Data</button>
        </form>
    </div>

    <div style="width: 1100px;">
        {{ history_section | safe }}
    </div>

    <script>
        window.addEventListener('load', () => {
            setTimeout(() => {
                const splash = document.getElementById('splash-screen');
                splash.style.opacity = '0';
                splash.style.visibility = 'hidden';
            }, 1200);
        });

        const categories = {{ chart_labels | safe }};
        const categoryData = {{ chart_data | safe }};

        if (categories.length > 0) {
            const ctx = document.getElementById('expenseChart').getContext('2d');
            new Chart(ctx, {
                type: 'pie',
                data: {
                    labels: categories,
                    datasets: [{
                        data: categoryData,
                        backgroundColor: ['#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0', '#9966FF', '#FF9F40']
                    }]
                },
                options: { responsive: true, plugins: { legend: { position: 'bottom' } } }
            });
        }
    </script>
</body>
</html>
"""

# Routes
@app.route("/")
def home():
    total = get_total_expense()
    history = get_expense_history()
    labels, data = get_chart_data()
    acc_cards, acc_options = get_accounts_info()
    return render_template_string(
        HTML_TEMPLATE,
        total_expense=total,
        result_section="",
        history_section=history,
        chart_labels=labels,
        chart_data=data,
        account_cards=acc_cards,
        account_options=acc_options
    )

@app.route("/predict", methods=["POST"])
def predict():
    description = request.form["description"]
    amount = float(request.form["amount"])
    account_id = int(request.form.get("account_id", 1))

    category = model.predict([description])[0]

    conn = sqlite3.connect("expenses.db")
    cursor = conn.cursor()
    cursor.execute("INSERT INTO expenses (amount, description, category, account_id) VALUES (?, ?, ?, ?)", 
                   (amount, description, category, account_id))
    cursor.execute("UPDATE accounts SET balance = balance - ? WHERE id = ?", (amount, account_id))
    conn.commit()
    conn.close()

    total = get_total_expense()
    budget_alert = ""
    if total > 5000:
        budget_alert = "<p style='color: red; font-weight: bold;'>⚠️ Warning: You have exceeded your monthly budget limit of ₹5,000!</p>"

    result_html = f"""
    <div class="card animate__animated animate__bounceIn" style="background: #eef9ff; margin-top: 20px; border-left: 5px solid #007bff; width: 380px;">
        <h3>Prediction & Saved!</h3>
        <p><b>Amount:</b> ₹{amount}</p>
        <p><b>Description:</b> {description}</p>
        <p><b>AI Category:</b> <span style="color: green; font-weight: bold;">{category}</span></p>
        {budget_alert}
    </div>
    """

    history = get_expense_history()
    labels, data = get_chart_data()
    acc_cards, acc_options = get_accounts_info()
    return render_template_string(
        HTML_TEMPLATE,
        total_expense=total, 
        result_section=result_html, 
        history_section=history,
        chart_labels=labels,
        chart_data=data,
        account_cards=acc_cards,
        account_options=acc_options
    )

@app.route("/add_account", methods=["POST"])
def add_account():
    name = request.form["account_name"]
    balance = float(request.form["balance"])

    conn = sqlite3.connect("expenses.db")
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO accounts (account_name, balance) VALUES (?, ?)", (name, balance))
        conn.commit()
    except sqlite3.IntegrityError:
        
        pass
    finally:
        conn.close()

    return redirect(url_for("home"))

@app.route("/clear", methods=["POST"])
def clear():
    conn = sqlite3.connect("expenses.db")
    cursor = conn.cursor()
    cursor.execute("DELETE FROM expenses")
    conn.commit()
    conn.close()
    return redirect(url_for("home"))

if __name__ == "__main__":
    app.run(debug=True)