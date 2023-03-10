import os

from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.security import check_password_hash, generate_password_hash

from re import sub
from decimal import Decimal

from helpers import apology, login_required, lookup, usd
from datetime import datetime

#export API_KEY=pk_f3126fff0f8a4e3cb5ccd702783458f2

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")

# Make sure API key is set
if not os.environ.get("API_KEY"):
    raise RuntimeError("API_KEY not set")

buggy = []


@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


@app.route("/")
@login_required
def index():
    """Show portfolio of stocks"""

    # Display all stocks owned, number of shares, currrent price, and total value of each holding
    id = session['user_id']
    buffer = db.execute("SELECT username FROM users WHERE id = ?", id)
    name = buffer[0]['username']

    cash_buff = db.execute("SELECT cash FROM users WHERE id = ?", id)
    cash = cash_buff[0]['cash']

    try:
        stock_list = db.execute("SELECT * FROM ?", name)
        sum_buff = db.execute("SELECT total FROM ?", name)
        sum = 0

        for buff in sum_buff:
            tot = buff['total']
            part = Decimal(sub(r'[^\d.]', '', tot))
            sum = float(part) + sum

        total = cash + sum

        return render_template("index.html", stock_list=stock_list, cash=usd(cash), total=usd(total))
    except:
        return render_template("index.html", cash=usd(cash), total=usd(cash))

@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""

    if request.method == "POST":

        # Create variables
        stock = request.form.get("symbol")
        amount = request.form.get("shares")
        symbol = lookup(request.form.get("symbol"))

        # Check if input is blank
        if not stock:
            return apology("Stock cannot be blank")
        if not amount:
            return apology("Amount cannot be blank")

        # Check if stock name is valid
        if not symbol:
            return apology("Cannot find stock")

        # Check if user has enough money to make purchase
        total_cost = int(amount) * symbol["price"]
        id = session['user_id']
        temp = db.execute("SELECT cash FROM users WHERE id = ?", id)
        user_cash = temp[0]['cash']

        if total_cost > user_cash:
            return apology("Invalid funds")

        # Subtract money owed
        new_bal = user_cash - total_cost
        db.execute("UPDATE users SET cash = ? WHERE id = ?", new_bal, id)

        # Create a table if one doesnt exist
        buffer = db.execute("SELECT username FROM users WHERE id = ?", id)
        name = buffer[0]['username']
        db.execute("CREATE TABLE IF NOT EXISTS ? (symbol varchar(255), name varchar(255), shares int, price money, total money)", name)
        upper = stock.upper()

        # Check if stock exist in table
        temp = db.execute("SELECT symbol FROM ? WHERE symbol = ?", name, upper)
        if temp == []:
            db.execute("INSERT INTO ? (symbol, name, shares, price, total) VALUES (?, ?, ?, ?, ?)", name,
                       symbol["symbol"], symbol["name"], int(amount), usd(symbol["price"]), usd(total_cost))

        # Add if stock already exist
        else:

            # Update shares
            buff = db.execute("SELECT shares FROM ? WHERE symbol = ?", name, upper)
            old_value = buff[0]['shares']
            new_total = old_value + int(amount)
            db.execute("UPDATE ? SET shares = ? WHERE symbol = ?", name, new_total, upper)

            # Update price
            papa = symbol["price"]
            db.execute("UPDATE ? SET price = ? WHERE symbol = ?", name, usd(papa), upper)

            # Update total
            new_cost = new_total * symbol["price"]
            db.execute("UPDATE ? SET total = ? WHERE symbol = ?", name, usd(new_cost), upper)

        # Add into history, make a diactionary to insert into the list history that includes SYMBOL, SHARES, PRICE, TRANSACTED

        boog = datetime.now()
        time = boog.strftime("%m/%d/%Y %H:%M:%S")
        buff = {
            "symbol": symbol["symbol"],
            "shares": amount,
            "price": usd(symbol["price"]),
            "time": time
        }

        buggy.append(buff)

        # Return INDEX
        return redirect("/")

    else:
        return render_template("buy.html")

@app.route("/history")
@login_required
def history():
    """Show history of transactions"""

    return render_template("history.html", buggy=buggy)


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """Get stock quote."""

    if request.method == "POST":

        # Check if field is blank
        if not request.form.get("symbol"):
            return apology("Invalid input")

        # Check if stock is in database
        symbol = lookup(request.form.get("symbol"))
        if symbol == None:
            return apology("Could not find stock")
        else:
            name = symbol["name"]
            price = usd(symbol["price"])
            symbols = symbol["symbol"]
            return render_template("quoted.html", name=name, price=price, symbols=symbols)
    else:
        return render_template("quote.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""

    if request.method == "POST":

        # Check if any field is left blank
        if not request.form.get("username") or not request.form.get("password") or not request.form.get("confirmation"):
            return apology("Each field is required")

        # Check if passwords match
        if request.form.get("password") != request.form.get("confirmation"):
            return apology("Passwords do not match")

        # Check if username is taken

        usernames = db.execute("SELECT username FROM users")
        if request.form.get("username") in usernames:
            return apology("Username already taken")

        username = request.form.get("username")
        password = generate_password_hash(request.form.get("password"))
        db.execute("INSERT INTO users (username, hash) VALUES (?, ?)", username, password)

        # Log user in
        buffer = db.execute("SELECT id FROM users WHERE username = (?)", username)
        session["user_id"] = buffer[0]['id']
        return redirect("/")

    else:
        return render_template("register.html")

@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""

    if request.method == "POST":
        if not request.form.get("symbol"):
            return apology("No stock selected")

        id = session["user_id"]
        name = db.execute("SELECT username FROM users WHERE id = ?", id)[0]["username"]
        symbol = request.form.get("symbol")
        shares = request.form.get("shares")

        # Check if amount of shares is invalid (more then possible)
        shares_actual = db.execute("SELECT shares FROM ? WHERE symbol = ?", name, symbol)[0]["shares"]
        if int(shares) > shares_actual:
            return apology("Invalid amount")

        # If valid then adjust
        elif int(shares) < shares_actual:
            shares_new = shares_actual - int(shares)
            price = lookup(symbol)["price"]
            total = round((shares_new * float(price)), 2)
            old_cash = round((db.execute("SELECT cash FROM users WHERE username = ?", name)[0]["cash"]), 2)

            db.execute("UPDATE ? SET shares = ? WHERE symbol = ?", name, shares_new, symbol)
            db.execute("UPDATE ? SET price = ? WHERE symbol = ?", name, usd(price), symbol)
            db.execute("UPDATE ? SET total = ? WHERE symbol = ?", name, usd(total), symbol)

            vec = round((int(shares) * price), 2)
            new_cash = round((vec + old_cash), 2)

            db.execute("UPDATE users SET cash = ? WHERE username = ?", new_cash, name)

            # Add into history list
            boog = datetime.now()
            time = boog.strftime("%m/%d/%Y %H:%M:%S")
            tag = ("-"+shares)
            buff = {
                "symbol": symbol,
                "shares": tag,
                "price": usd(price),
                "time": time
            }
            buggy.append(buff)

            # return render_template("check.html", a = symbol, b = tag, c = buff)
            return redirect("/")

        # Remove from table if shares is equal to sell amount
        else:
            price = lookup(symbol)["price"]
            old_cash = round((db.execute("SELECT cash FROM users WHERE username = ?", name)[0]["cash"]), 2)
            total = round((int(shares) * price), 2)
            final = round((total + old_cash), 2)
            db.execute("UPDATE users SET cash = ? WHERE username = ?", final, name)
            db.execute("DELETE FROM ? WHERE symbol = ?", name, symbol)

            # Add into history list
            boog = datetime.now()
            time = boog.strftime("%m/%d/%Y %H:%M:%S")
            tag = ("-"+shares)

            buff = {
                "symbol": symbol,
                "shares": tag,
                "price": usd(price),
                "time": time
            }
            buggy.append(buff)

            return redirect("/")

    else:

        # If meathod is get make sure to send through a list of stocks for the list
        id = session["user_id"]
        name = db.execute("SELECT username FROM users WHERE id = ?", id)[0]["username"]
        try:
            buffer = db.execute("SELECT symbol FROM ?", name)
            arr = []

            for buff in buffer:
                arr.append(buff["symbol"])

            # return render_template("check.html", a = buffer, b = arr)
            return render_template("sell.html", arr=arr)

        except:
            return render_template("sell.html", arr=[])
    # return apology("TODO")

