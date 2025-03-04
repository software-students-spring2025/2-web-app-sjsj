import json
from flask import Flask, render_template, request, redirect, url_for, flash, session
import certifi
from pymongo import MongoClient
from bson.objectid import ObjectId
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY')

MONGO_URI = os.getenv('MONGO_URI')
client = MongoClient(
    "mongodb+srv://sms10010:Wittmer2@swe-project2.zdloe.mongodb.net/?retryWrites=true&w=majority&appName=SWE-project2", tlsCAFile=certifi.where())
db = client["movie_tracker"]
movies_collection = db["movies"]
users_collection = db["users"]

@app.before_request
def clear_stale_flash_messages():
    session.pop('_flashes', None)

@app.route('/')
def index():
    return redirect(url_for('login'))


@app.route('/home')
def home():
    if 'username' not in session:
        return redirect(url_for('login'))
    username = session['username']
    user = movies_collection.find_one({"username": username})
    movies = user.get("movies", []) if user else []

    return render_template('home.html', movies=movies)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = users_collection.find_one({"username": username})

        if user and user['password'] == password:
            session['username'] = username
            return redirect(url_for('home'))
        else:
            return redirect(url_for('login'))
    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        if users_collection.find_one({"username": username}):
            flash("Username already exists. Please choose a different one.")
        else:
            users_collection.insert_one({
                "username": username,
                "password": password,
            })

            movies_collection.insert_one({
                "username": username,
                "movies": []
            })

            return redirect(url_for('login'))
    return render_template('register.html')


@app.route("/add", methods=["GET", "POST"])
def add():
    username = session['username']

    if request.method == "POST":
        title = request.form.get("title")
        genre = request.form.get("genre")
        release_year = request.form.get("release_year")

        if title and genre and release_year:
            new_movie = {
                "title": title,
                "genre": genre,
                "release_year": release_year
            }
            movies_collection.update_one(
                {"username": username},
                {"$push": {"movies": new_movie}}
            )
        return redirect(url_for('home'))

    return render_template("add.html")


@app.route('/movie_details/<username>/<title>', methods=['GET'])
def movie_details(username, title):
    if 'username' not in session:
        return redirect(url_for('login'))

    user_movies = movies_collection.find_one({"username": username})

    if user_movies and 'movies' in user_movies:
        movie = next(
            (m for m in user_movies['movies'] if m['title'] == title), None)

        if movie:
            return render_template('details.html', movie=movie)
        else:
            flash("Movie not found!")
            return redirect(url_for('home'))
    else:
        flash("No movies found for this user!")
        return redirect(url_for('home'))


@app.route('/edit_movie/<username>/<title>', methods=['GET', 'POST'])
def edit_movie(username, title):
    if 'username' not in session:
        flash("Please log in first.")
        return redirect(url_for('login'))

    user_movies = movies_collection.find_one({"username": username})

    if user_movies:
        movie = next(
            (m for m in user_movies['movies'] if m['title'] == title), None)

        if not movie:
            flash("Movie not found!")
            return redirect(url_for('home'))

        if request.method == 'POST':
            new_title = request.form.get("title")
            genre = request.form.get("genre")
            release_year = request.form.get("release_year")

            movies_collection.update_one(
                {"username": username, "movies.title": title},
                {"$set": {
                    "movies.$.title": new_title,
                    "movies.$.genre": genre,
                    "movies.$.release_year": release_year
                }}
            )

            flash("Movie updated successfully!")
            return redirect(url_for('home'))

        return render_template('edit.html', movie=movie)
    else:
        flash("No movies found for this user!")
        return redirect(url_for('home'))


@app.route('/delete_movie/<username>/<title>', methods=['POST'])
def delete_movie(username, title):
    if 'username' not in session:
        flash("Please log in first.")
        return redirect(url_for('login'))

    result = movies_collection.update_one(
        {"username": username},
        {"$pull": {"movies": {"title": title}}}
    )

    if result.modified_count > 0:
        flash("Movie deleted successfully!")
    else:
        flash("Movie not found!")

    return redirect(url_for('home'))


@app.route('/search', methods=['GET', 'POST'])
def search():
    if 'username' not in session:
        flash("Please log in first.")
        return redirect(url_for('login'))

    matching_movies = []

    if request.method == 'POST':
        username = session['username']
        search_query = request.form.get('query')
        user_movies = movies_collection.find_one({"username": username})

        if user_movies:
            movies = user_movies.get("movies", [])
            for movie in movies:
                movie_dict = None
                if isinstance(movie, str):
                    try:
                        movie_dict = json.loads(movie)
                    except json.JSONDecodeError:
                        print(f"Error decoding movie: {movie}")
                elif isinstance(movie, dict):
                    movie_dict = movie

                if movie_dict and search_query.lower() in movie_dict.get("title", "").lower():
                    matching_movies.append(movie_dict)

    return render_template('search.html', matching_movies=matching_movies)


if __name__ == '__main__':
    app.run(debug=True)
