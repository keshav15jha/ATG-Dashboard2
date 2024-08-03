from flask import Flask, render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import os
import re

app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(24)
app.config['UPLOAD_FOLDER'] = 'static/uploads'

# Custom Jinja2 filter to truncate words
def truncate_words(s, num_words):
    words = re.split(r'\s+', s)
    if len(words) > num_words:
        return ' '.join(words[:num_words]) + '...'
    return s

# Register the custom filter
app.jinja_env.filters['truncate_words'] = truncate_words

# Helper function to connect to the database
def get_db_connection():
    conn = sqlite3.connect('users.db')
    conn.row_factory = sqlite3.Row
    return conn

# Database setup
def init_db():
    conn = get_db_connection()
    conn.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        first_name TEXT,
        last_name TEXT,
        profile_picture TEXT,
        username TEXT UNIQUE,
        email TEXT UNIQUE,
        password TEXT,
        address_line1 TEXT,
        city TEXT,
        state TEXT,
        pincode TEXT,
        user_type TEXT
    )''')

    conn.execute('''CREATE TABLE IF NOT EXISTS blogs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT,
        image TEXT,
        category TEXT,
        summary TEXT,
        content TEXT,
        is_draft INTEGER,
        author_id INTEGER,
        FOREIGN KEY (author_id) REFERENCES users (id)
    )''')

    conn.commit()
    conn.close()

# Call the database setup function
init_db()

# Routes and view functions
@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        username = request.form['username']
        email = request.form['email']
        password = generate_password_hash(request.form['password'])
        address_line1 = request.form['address_line1']
        city = request.form['city']
        state = request.form['state']
        pincode = request.form['pincode']
        user_type = request.form['user_type']
        profile_picture = request.files['profile_picture']

        if profile_picture:
            pic_filename = os.path.join(app.config['UPLOAD_FOLDER'], profile_picture.filename)
            profile_picture.save(pic_filename)
            pic_path = f'uploads/{profile_picture.filename}'
        else:
            pic_path = None

        try:
            conn = get_db_connection()
            conn.execute('''INSERT INTO users (first_name, last_name, profile_picture, username, email, password,
                            address_line1, city, state, pincode, user_type)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                            (first_name, last_name, pic_path, username, email, password,
                            address_line1, city, state, pincode, user_type))
            conn.commit()
            conn.close()
            flash('Registration successful! Please log in.', 'success')
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash('Username or email already exists. Please try again.', 'error')

    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
        conn.close()

        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['user_type'] = user['user_type']
            if user['user_type'] == 'Doctor':
                return redirect(url_for('doctor_dashboard'))
            elif user['user_type'] == 'Patient':
                return redirect(url_for('patient_dashboard'))
        else:
            flash('Invalid username or password. Please try again.', 'error')

    return render_template('login.html')

@app.route('/doctor_dashboard', methods=['GET', 'POST'])
def doctor_dashboard():
    if 'user_id' not in session or session['user_type'] != 'Doctor':
        return redirect(url_for('login'))

    user_id = session['user_id']
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()

    if request.method == 'POST':
        title = request.form['title']
        image = request.files['image']
        category = request.form['category']
        summary = request.form['summary']
        content = request.form['content']
        draft = 1 if 'draft' in request.form else 0
        author_id = user['id']

        if image:
            image_filename = os.path.join(app.config['UPLOAD_FOLDER'], image.filename)
            image.save(image_filename)
            image_path = f'uploads/{image.filename}'
        else:
            image_path = None

        add_blog_post(title, image_path, category, summary, content, draft, author_id)
        flash('Blog post created successfully!', 'success')
        return redirect(url_for('doctor_dashboard'))

    blogs = conn.execute('SELECT * FROM blogs WHERE author_id = ?', (user_id,)).fetchall()
    conn.close()

    # Categorize blogs for display
    categorized_blogs = {
        "Mental Health": [],
        "Heart Disease": [],
        "Covid-19": [],
        "Immunization": []
    }

    for blog in blogs:
        categorized_blogs[blog['category']].append(blog)

    return render_template('doctor_dashboard.html', user=user, categorized_blogs=categorized_blogs)

@app.route('/patient_dashboard')
def patient_dashboard():
    if 'user_id' not in session or session['user_type'] != 'Patient':
        return redirect(url_for('login'))

    user_id = session['user_id']
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
    blogs = conn.execute('SELECT * FROM blogs WHERE is_draft = 0').fetchall()
    conn.close()

    # Categorize blogs for display
    categorized_blogs = {
        "Mental Health": [],
        "Heart Disease": [],
        "Covid-19": [],
        "Immunization": []
    }

    for blog in blogs:
        categorized_blogs[blog['category']].append(blog)

    return render_template('patient_dashboard.html', user=user, categorized_blogs=categorized_blogs)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

def add_blog_post(title, image, category, summary, content, draft, author_id):
    conn = get_db_connection()
    conn.execute('''INSERT INTO blogs (title, image, category, summary, content, is_draft, author_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?)''',
                    (title, image, category, summary, content, draft, author_id))
    conn.commit()
    conn.close()

if __name__ == '__main__':
    app.run(debug=True)
