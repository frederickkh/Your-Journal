import os

from cs50 import SQL
from flask import Flask, flash, jsonify, redirect, render_template, request, session, url_for
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash
import json
import re
import html

from helpers import apology, login_required

from datetime import date, datetime
import time

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Ensure responses aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

# cache-control: must-revalidate

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = True
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///journal.db")

@app.route("/")
def land():

    session.clear()

    return render_template("landing.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            flash("Please input username", "error")
            return render_template("login.html")

        # Ensure password was submitted
        elif not request.form.get("password"):
            flash("Please input password", "error")
            return render_template("login.html")

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = :username",
                          username=request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            flash("Invalid username and/or password", "error")
            return render_template("login.html")

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/home")

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


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""

    session.clear()

    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            flash("Please input username", "error")
            return render_template("register.html")

        # Ensure password was submitted
        elif not request.form.get("password"):
            flash("Please input password", "error")
            return render_template("register.html")

        # Ensure username and password aren't the same
        elif request.form.get("username") == request.form.get("password"):
            flash("Username and password can't be identical", "error")
            return render_template("register.html")

        # Check password validity
        elif not validpassword(request.form.get("password")):
            flash("Password requirements: minimum length 8, at least 1 from each [a-z], [A-Z], and [0-9]", "error")
            return render_template("register.html")

        # Ensure confirmed password was submitted
        elif not request.form.get("confirmation"):
            flash("Please confirm password", "error")
            return render_template("register.html")

        # Ensure password is same with confirmed
        elif request.form.get("password") != request.form.get("confirmation"):
            flash("Password don't match", "error")
            return render_template("register.html")

        rows = db.execute("SELECT username FROM users")

        # Check for same username existed
        for row in rows:
            if request.form.get("username") == row["username"]:
                flash("Username taken", "error")
                return render_template("register.html")

        hashed = generate_password_hash(request.form.get("password"), method='pbkdf2:sha256', salt_length=8)

        # Insert data to database
        db.execute("INSERT INTO users (username, hash) VALUES (:username, :hashed);",
                    username=request.form.get("username"), hashed=hashed)


        ##########   Auto login   ##########

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = :username",
                          username=request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            flash("Invalid username and/or password", "error")
            return render_template("register.html")

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/home")

    else:
        return render_template("register.html")

@app.route("/home", methods=["GET", "POST"])
def index():
    if request.method == "POST":

        # Edit link
        if request.form.get("edit"):
            # Get journal title to edit
            title = request.form.get("edit")

            return redirect(url_for('edit', title = title))

        # View link
        elif request.form.get("view"):
            title = request.form.get("view")
            journal = db.execute("SELECT title, content FROM journals WHERE id = :id AND title = :title", id = session["user_id"], title = title)
            return redirect("/view")

        # Pin button
        elif request.form.get("pin"):
            title = request.form.get("pin")
            pinned = db.execute("SELECT pinned FROM journals WHERE id = :id AND title = :title", id = session["user_id"], title = title)

            # If pinned, set unpinned
            if pinned[0]["pinned"] == 'TRUE':
                db.execute("UPDATE journals SET pinned = 'FALSE' WHERE id = :id AND title = :title", id = session["user_id"], title = title)

            # If unpinned, set pinned
            else:
                db.execute("UPDATE journals SET pinned = 'TRUE' WHERE id = :id AND title = :title", id = session["user_id"], title = title)

            return redirect("/home")

    else:
        journals = db.execute("SELECT title, date_modified FROM journals WHERE id = :id ORDER BY pinned DESC, date_modified DESC", id = session["user_id"])

        user = db.execute("SELECT username FROM users WHERE id = :id", id = session["user_id"])[0]["username"]

        return render_template("index.html", journals = journals, user = user)


@app.route("/history")
@login_required
def history():
    """Show history of actions"""
    journals = db.execute("SELECT * FROM history WHERE id = :id ORDER BY date DESC", id = session["user_id"])

    # Indicate user
    user = db.execute("SELECT username FROM users WHERE id = :id", id = session["user_id"])[0]["username"]

    return render_template("history.html", journals = journals, user = user)


@app.route("/new", methods=["GET", "POST"])
@login_required
def new():
    if request.method == "POST":
        if not request.form.get("title"):
            flash("Provide journal title.")
            return redirect("/new")

        title = request.form.get("title")
        content = request.form.get("content")

        titles = db.execute("SELECT title FROM journals WHERE id = :id", id = session["user_id"])

        # Add number suffix to journal title if the same title existed
        counter = 1
        for exist in titles:
            if exist["title"] == title:
                title = title + "(" + str(counter) + ")"
            counter += 1

        db.execute("INSERT INTO journals (id, title, content, date_created, date_modified, pinned) VALUES (:id, :title, :content, CURRENT_DATE, CURRENT_TIMESTAMP, 'FALSE')",
                    id = session["user_id"], title = title, content = content)

        db.execute("INSERT INTO history VALUES (:id, :title, 'Created', CURRENT_TIMESTAMP)", id = session["user_id"], title = title)

        return redirect("/home")
    else:
        today = date.today()
        user = db.execute("SELECT username FROM users WHERE id = :id", id = session["user_id"])[0]["username"]
        return render_template("new.html", today=today, user=user)


@app.route("/edit/<title>", methods=["GET", "POST"])
@login_required
def edit(title):

    if request.method == "POST":
        title = title
        if not request.form.get("title"):
            flash("Provide journal title")
            return redirect("/edit")

        title_after = request.form.get("title")

        if request.form.get("save"):

            content = request.form.get("content")

            db.execute("UPDATE journals SET title = :title_after, content = :content, date_modified = CURRENT_TIMESTAMP WHERE id=:id AND title = :title_before",
                        title_after = title_after, content = content, id = session["user_id"], title_before = title)

            db.execute("INSERT INTO history VALUES (:id, :title, 'Edited', CURRENT_TIMESTAMP)", id = session["user_id"], title = title)

        elif request.form.get("delete"):
            db.execute("DELETE FROM journals WHERE title = :title AND id = :id", title = title, id = session["user_id"])
            db.execute("INSERT INTO history VALUES (:id, :title, 'Deleted', CURRENT_TIMESTAMP)", id = session["user_id"], title = title)


        return redirect("/home")

    else:
        title = title
        journal = db.execute("SELECT title, content, date_created FROM journals WHERE id = :id AND title = :title", id = session["user_id"], title = title)
        content = journal[0]["content"]
        date = journal[0]["date_created"]

        user = db.execute("SELECT username FROM users WHERE id = :id", id = session["user_id"])[0]["username"]

        return render_template("edit.html", title=title, content=content, date=date, user=user)


@app.route("/view/<title>")
@login_required
def view(title):
    title = title
    journal = db.execute("SELECT title, content, date_created FROM journals WHERE id = :id AND title = :title", id = session["user_id"], title = title)
    content = html.unescape(journal[0]["content"])
    date = journal[0]["date_created"]

    user = db.execute("SELECT username FROM users WHERE id = :id", id = session["user_id"])[0]["username"]

    return render_template("view.html", title=title, content=content, date=date, user=user)


@app.route("/user", methods=["GET", "POST"])
def user():
    """ User tab (Username, Change Username/Password) """
    if request.method == "POST":
        if request.form.get("change_username") == "True":
            # Ensure new username was submitted
            if not request.form.get("new_username"):
                flash("Input new username")
                return redirect("/user")

            username = request.form.get("new_username")

            # Insert data to database
            db.execute("UPDATE users SET username = :username WHERE id = :id",
                        username = username, id = session["user_id"])

        elif request.form.get("change_password") == "True":
            # Ensure old password was submitted
            if not request.form.get("old_password"):
                flash("Provide old password")
                return redirect("/user")

            old_password = db.execute("SELECT hash FROM users WHERE id = :id", id = session["user_id"])[0]["hash"]

            # Ensure old password matches database
            if not check_password_hash(old_password, request.form.get("old_password")):
                flash("Old password invalid")
                return redirect("/user")

            # Ensure new password was submitted
            if not request.form.get("new_password"):
                flash("Provide new password")
                return redirect("/user")

            # Check password validity
            elif not validpassword(request.form.get("new_password")):
                flash("Password requirements: minimum length 8, at least 1 from each [a-z], [A-Z], and [0-9]", "error")
                return render_template("register.html")

            # Ensure confirmed password was submitted
            if not request.form.get("confirmation"):
                flash("Confirm new password")
                return redirect("/user")

            # Ensure old and new password aren't same
            elif request.form.get("old_password") == request.form.get("new_password"):
                flash("Old and new password can't be identical")
                return redirect("/user")

            elif request.form.get("new_password") != request.form.get("confirmation"):
                flash("Passwords don't match")
                return redirect("/user")


            hashed = generate_password_hash(request.form.get("new_password"), method='pbkdf2:sha256', salt_length=8)

            # Insert data to database
            db.execute("UPDATE users SET hash = :hashed WHERE id = :id",
                        hashed = hashed, id = session["user_id"])

        return redirect("/login")

    else:
        # Indicate user
        user = db.execute("SELECT username FROM users WHERE id = :id", id = session["user_id"])[0]["username"]

        return render_template("user.html", user = user)

def validpassword(p):
    valid = False
    p = str(p)
    while not valid:
        if len(p) < 8:
            break
        elif not re.search("[a-z]",p):
            break
        elif not re.search("[0-9]",p):
            break
        elif not re.search("[A-Z]",p):
            break
        else:
            valid = True
            break

    return valid

def errorhandler(e):
    """Handle error"""
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    return apology(e.name, e.code)


# Listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)
