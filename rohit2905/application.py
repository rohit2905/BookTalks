import os
import sys

from helpers import login_required, get_review_counts

import json
from werkzeug.security import check_password_hash, generate_password_hash
from flask import Flask, session, render_template, request, redirect
from flask_session import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from flask.helpers import flash

app = Flask(__name__)

# Check for environment variable
if not os.getenv("DATABASE_URL"):
    raise RuntimeError("DATABASE_URL is not set")

# Configure app's secret key for cookie signing
app.secret_key = os.urandom(24)

# Configure session to use filesystem
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Set up database
engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))


@app.route("/", methods=["GET", "POST"])
def index():
    # POST-request to this route means the user tries to log in
    if request.method == "POST":

        # Check if all required fields were filled in
        if not request.form.get("username"):
            return render_template("error.html", error="Username field not filled in")

        if not request.form.get("password"):
            return render_template("eoor.html", error="Must fill in password")

        # Get data from form
        username = request.form.get("username")
        password = request.form.get("password")

        # Query database for user
        rows = db.execute("SELECT * FROM users WHERE username = :username",
                            {"username": username})
        
        result = rows.fetchone()
        # If we get no data back here, the user is not in our database=
        if not result:
            return render_template("error.html", error="Username not found")

        # Get passwordhash from userrow
       

        # check password
        if not check_password_hash(result[2], password):
            return render_template("error.html", error="Password incorrect")

        # check the user and the password is correct
        else:
            session["user"] = username
            return redirect("/loginhome")

    #to welcome page
    else:
        if session.get("user") is None:
            return render_template("welcome.html")

        else:
            return redirect("/loginhome")


#register user.
@app.route("/register", methods=["GET", "POST"])
def register():
    """Let users register"""

    if request.method == "POST":

        #Check if all fields were filled
        if not request.form.get("username"):
            return render_template("error.html", error="Username field not filled in")

        elif not request.form.get("password"):
            return render_template("error.html", error="Password field not filled in")

        elif not request.form.get("passwordConfirm"):
            return render_template("error.html", error="Password confirmation field not filled in")

        #Get all fields from the form
        username = request.form.get("username")
        password = request.form.get("password")
        passwordConfirm = request.form.get("passwordConfirm")

        # DEBUG:
        #print(username, file=sys.stderr)
        #print(password, file=sys.stderr)
        #print(passwordConfirm, file=sys.stderr)

        #Check form for correctness
        if not password == passwordConfirm:
            return render_template("error.html", error="Passwords did not match")

        # Check username
        userrow = db.execute("SELECT * FROM users WHERE username = :username", {"username": username})
        user_exists = userrow.first()
        if not user_exists:
            #  store the username and hashed password in the database
            hashedPassword = generate_password_hash(request.form.get("password"), method='pbkdf2:sha256', salt_length=8)
            db.execute("INSERT INTO users (username, hash) VALUES (:username, :hashedPassword)",
                {"username": username, "hashedPassword": hashedPassword})
            db.commit()
            return render_template("registercomplete.html")

        # If a row with that username was found
        else:
            return render_template("error.html", error="That username is taken.")

  
    else:
        return render_template("register.html")

@app.route("/search", methods=["POST"])
def search():
    #get search query from request
    q = request.form.get("search")
    q=q.title()
    q = "%" + q + "%"
    print(q)

    # Search database for any entry containing this set of characters
    result = db.execute("SELECT isbn, title, author, year, id FROM books WHERE isbn LIKE :q OR title LIKE :q OR author LIKE :q OR year LIKE :q",
                {"q": q})

    # The data will be given to the template in a list
    result_list = []

    # In this loop, result and the rows therein are converted to lists; result_list containing row_lists
    for row in result:
        row_list = []
        for i in range(5):
            row_list.append(row[i])

        result_list.append(row_list)

    #close connection
    result.close()

    #sending result_list to search.html
    return render_template("search.html", result_list=result_list)

@app.route("/book/<id>", methods=["GET", "POST"])
def book(id):
    """The GET-method for this page will take the id of a book, search for that id in our database and return a page with
    info on the book. Part of that info is an average score on Goodreads. This data is retrieved
    using a query to the Goodreads API."""
    # for submitting user review
    if request.method == "POST":
        # Search for reviews on this book by this author
        result = db.execute("SELECT * FROM reviews WHERE author = :user AND book_id = :id",
        {"user": session["user"], "id": id })
        print("RESULT: ")
        print(result)
        userreview = result.first()

        # If there are no reviews on this book by this user
        if not userreview:
            # Get all data from submitted form
            rating = request.form.get("rating")
            review_text = request.form.get("review_text")

            # add review to database
            db.execute("INSERT INTO reviews (book_id, author, rating, review) VALUES (:book_id, :author, :rating, :review_text)",
            {"book_id": id,  "author": session["user"], "rating": rating, "review_text": review_text})
            db.commit()

            # Make URL to redirect user back to updated book-page
            this_book_url = "/book/" + id

            # redirect user to updated book page
            return redirect(this_book_url)

        else:
            #error page
            return render_template('NoReview.html')
            

    # GET-route for displaying book data
    else:
        # Get data about book from database
        result = db.execute("SELECT isbn, title, author, year FROM books WHERE id = :id",
        {"id": id})

        # Store isbn, title, author, year (in that order) in book_data
        for row in result:
            book_data = dict(row)

        # add book id to book_data
        book_data['id'] = id

        # Query Goodreads for info on the book
        review_counts_result = get_review_counts(book_data['isbn'])

        # Store results from query in book_data
        book_data['average_rating'] = review_counts_result['average_rating']
        book_data['number_ratings'] = review_counts_result['number_ratings']
        

        # Get all reviews on this book from reviews table
        result = db.execute("SELECT author, rating, review FROM reviews WHERE book_id = :id",
                            {"id": id})

        # Store all rows in a list of dicts
        review_rows = []

        for row in result:
            review_rows.append(dict(row))

        return render_template("book.html", book_data=book_data, review_rows=review_rows)

@app.route("/api/<isbn>")
def api(isbn):

    # Get info on book title, author and year  from database
    result = db.execute("SELECT title, author, year FROM books WHERE isbn = :isbn",
    {"isbn": isbn})

    # Store result of SELECT-query in a dict
    book_data = dict(result.first())
    book_data['isbn'] = isbn

    # Query Goodreads API for data on book ratings
    review_counts_result = get_review_counts(isbn)

    # Store data from Goodreads in book_data
    book_data['average_score'] = review_counts_result['average_rating']
    book_data['review_count'] = review_counts_result['number_ratings']

    print(book_data)

    # Convert book_data dict into JSON string
    book_json = json.dumps(book_data, )

    return book_json

@app.route("/loginhome")
@login_required
def loginhome():
    """This is the first page you get to after logging in."""
    return render_template("loginhome.html")

@app.route("/logout")
@login_required
def logout():
    """Removes the user from the session, logging them out"""
    session.pop("user", None)
    return render_template("welcome.html")

@app.route("/myReview")
@login_required
def myReview():
    #select information for a specified user
    review_set=db.execute("SELECT book_id,review,rating from reviews where author=:username",{"username":session["user"]})
    #print(review_set)
    my_review_rows = []
    book_names=[]
    bookid=[]
    #appending information in form of dict
    for row in review_set:
        my_review_rows.append(dict(row))
        bookid.append(dict(row)['book_id'])
    #print(bookid)
    #FOR DEBUGGING
    #print(my_review_rows)
    #STORING BOOK NAME
    book_names_set=[]

    #extracting book names from the set
    for i in range(len(bookid)):
        book_names_set=db.execute("SELECT title from books where id=:id",{"id":bookid[i]})
        for j in book_names_set:
            book_names.append(dict(j)['title'])
    #print(book_names)

    #adding movie names to my_review_rows
    i=0
    for book in book_names:
        my_review_rows[i]['title']= book
        i+=1
    #print(my_review_rows)

    #passing my_review_rows to myReview.html
    return render_template("myReview.html",rset=my_review_rows)
