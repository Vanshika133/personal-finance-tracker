from flask import Flask, render_template, request, redirect, url_for, session, g
import sqlite3 # To connect and query the SQLite database.
import os #For path handling, especially when packaging the app.
import os, sys

base_dir = getattr(sys, '_MEIPASS', os.path.abspath(os.getcwd()))
app = Flask(__name__,
    template_folder=os.path.join(base_dir, 'templates')
)

app.secret_key = 'your_secret_key'  # Change this in real app
DATABASE = 'finance.db'

# ---------------- DATABASE SETUP ---------------- #

def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
    return g.db

@app.teardown_appcontext
def close_db(error):
    db = g.pop('db', None)
    if db is not None:
        db.close()

def init_db():
    # Initialize the database within the Flask app context
    with app.app_context():
        db = get_db()
        
        # Create users table if it doesn't exist
        db.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL
            );
        ''')

        # Create budgets table with a foreign key to users table
        db.execute('''
            CREATE TABLE IF NOT EXISTS budgets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                amount REAL,
                FOREIGN KEY(user_id) REFERENCES users(id)
            );
        ''')

        # Create expenses table with a foreign key to users table
        db.execute('''
            CREATE TABLE IF NOT EXISTS expenses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                amount REAL,
                date TEXT,
                description TEXT,
                FOREIGN KEY(user_id) REFERENCES users(id)
            );
        ''')

        # Save changes to the database
        db.commit()

# ------------------- ROUTES --------------------- #
@app.route("/")
def home():
    # Render the home page template
    return render_template("home.html")

#--------------------LOGIN-----------------#

@app.route("/login", methods=["GET", "POST"])
def login():
    # If form is submitted
    if request.method == "POST":
        # Get username and password from form
        username = request.form["username"]
        password = request.form["password"]

        # Get database connection
        db = get_db()

        # Check if user exists in database
        user = db.execute("SELECT * FROM users WHERE username=? AND password=?", (username, password)).fetchone()
        
        # If valid user found
        if user:
            # Store user id in session
            session["user_id"] = user["id"]
            return redirect(url_for("dashboard"))
        else:
            # Show error if login failed
            return render_template("login.html", error="Invalid credentials")
    
    # If page is visited (GET)
    return render_template("login.html")

#--------------------REGISTER -----------------#

@app.route("/register", methods=["GET", "POST"])
def register():
    # If form is submitted
    if request.method == "POST":
        # Get form data
        username = request.form['username']
        password = request.form['password']

        db = get_db()

        try:
            # Try to insert new user into database
            db.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, password))
            db.commit()
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            # If username already exists
            return render_template("register.html", error="Username already exists")
    
    # If page is visited (GET)
    return render_template("register.html")

#--------------------DASHBOARD -----------------#

@app.route("/dashboard")
def dashboard():
    # Redirect to login if not logged in
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    # Render the dashboard page (index.html)
    return render_template('index.html')

# ----------------- MENU ------------------- #

@app.route("/menu")
def menu():
    # Render the menu page
    return render_template("menu.html")


#--------------------LOGOUT -----------------#

@app.route("/logout")
def logout():
    # Clear session and redirect to login
    session.clear()
    return redirect(url_for('login'))

# ----------------- BUDGET API ------------------- #

@app.route("/budgets", methods=["GET", "POST"])
def budgets():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    db = get_db()

    if request.method == "POST":
        # Get budget amount from form
        amount = float(request.form['amount'])

        # Check if budget already exists
        existing = db.execute("SELECT * FROM budgets WHERE user_id=?", (session['user_id'],)).fetchone()
        
        if existing:
            # Update budget by adding amount
            new_amount = existing['amount'] + amount
            db.execute("UPDATE budgets SET amount=? WHERE user_id=?", (new_amount, session['user_id']))
        else:
            # Insert new budget entry
            db.execute("INSERT INTO budgets (user_id, amount) VALUES (?, ?)", (session['user_id'], amount))

        db.commit()
        return redirect(url_for('budgets'))

    # Fetch and display current budget
    budget_data = db.execute("SELECT amount FROM budgets WHERE user_id=?", (session['user_id'],)).fetchone()
    return render_template("budgets.html", budget=budget_data['amount'] if budget_data else 0)



# ----------------- EXPENSE API ------------------- #

@app.route("/expenses", methods=["GET", "POST"])
def expenses():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    db = get_db()

    if request.method == "POST":
        # Get data from form
        amount = float(request.form['amount'])
        date = request.form['date']
        desc = request.form['description']

        # Insert expense into database
        db.execute("INSERT INTO expenses (user_id, amount, date, description) VALUES (?, ?, ?, ?)",
                   (session['user_id'], amount, date, desc))
        db.commit()

        # Refresh the expenses page
        return redirect(url_for('expenses'))

    return render_template("expenses.html")


# ----------------- TRANSACTION API ------------------- #

@app.route("/Transactions")
def Transactions():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    db = get_db()

    # Get all transactions (expenses) for this user
    rows = db.execute("SELECT amount, date, description FROM expenses WHERE user_id=?", (session['user_id'],)).fetchall()
    return render_template("Transaction.html", transactions=rows)


# ----------------- OVERVIEW API ------------------- #


@app.route("/overview")
def overview():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    db = get_db()

    # Get total budget
    budget_row = db.execute("SELECT amount FROM budgets WHERE user_id=?", (session['user_id'],)).fetchone()
    total_budget = budget_row['amount'] if budget_row else 0

    # Get total expenses
    expenses = db.execute("SELECT amount FROM expenses WHERE user_id=?", (session['user_id'],)).fetchall()
    total_expenses = sum([e['amount'] for e in expenses])

    # Calculate remaining balance
    balance = total_budget - total_expenses

    # Get list of transactions
    transactions = db.execute("SELECT amount, date, description FROM expenses WHERE user_id=?", (session['user_id'],)).fetchall()
    
    return render_template("overview.html", budget=total_budget, expenses=total_expenses, balance=balance, transactions=transactions)


# ----------------- CHART API ------------------- #


@app.route("/chart")
def chart():
    #Step 1: Check if the user is logged in
    if 'user_id' not in session:
        return redirect(url_for('login'))  # If not, redirect to login page

    #Step 2: Get a connection to the database
    db = get_db()

    #Step 3: Fetch the total budget for the current user
    budget_row = db.execute(
        "SELECT amount FROM budgets WHERE user_id=?",
        (session['user_id'],)
    ).fetchone()
    
    # If budget exists, use it; otherwise, default to 0
    total_budget = budget_row['amount'] if budget_row else 0

    #Step 4: Fetch all expenses for the current user
    expenses = db.execute(
        "SELECT amount FROM expenses WHERE user_id=?",
        (session['user_id'],)
    ).fetchall()
    
    #Step 5: Calculate total expenses by summing each amount
    total_expenses = sum([e['amount'] for e in expenses])

    #Step 6: Calculate the remaining balance
    balance = total_budget - total_expenses

    #Step 7: Pass data to chart.html to render the chart
    return render_template("chart.html", expenses=total_expenses, balance=balance )


# ----------------- RESET API ------------------- #

@app.route("/reset", methods=["POST"])
def reset():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    db = get_db()

    # Delete user-specific budget and expenses data
    db.execute("DELETE FROM budgets WHERE user_id=?", (session['user_id'],))
    db.execute("DELETE FROM expenses WHERE user_id=?", (session['user_id'],))
    db.commit()

    return redirect(url_for('overview'))


# -------------------- MAIN ----------------------- #
 
if __name__ == "__main__":
    import webbrowser
    import threading

    # Function to open browser automatically
    def open_browser():
        webbrowser.open("http://127.0.0.1:5000/")
    
    # Start a timer to open browser after 1.25 seconds
    threading.Timer(1.25, open_browser).start()

    # Initialize the database and run the Flask app
    init_db()
    app.run(debug=False)



