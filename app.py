
from flask import Flask, render_template, request, redirect, session, url_for
import sqlite3, os
from datetime import datetime, timedelta
from werkzeug.utils import secure_filename
from functools import wraps

app = Flask(__name__)
app.secret_key = 'kabir_galgotias_2027'
app.config['UPLOAD_FOLDER'] = 'static/uploads'
DB = 'campus_final.db'

def init_db():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, name TEXT, email TEXT UNIQUE, password TEXT, role TEXT DEFAULT 'student')''')
    c.execute('''CREATE TABLE IF NOT EXISTS books (id INTEGER PRIMARY KEY, title TEXT, author TEXT, isbn TEXT, quantity INTEGER, available INTEGER, added_by INTEGER, added_at TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS issued (id INTEGER PRIMARY KEY, book_id INTEGER, student_id INTEGER, student_name TEXT, issue_date TEXT, due_date TEXT, return_date TEXT, status TEXT DEFAULT 'issued', fine INTEGER DEFAULT 0)''')
    c.execute('''CREATE TABLE IF NOT EXISTS mentors (id INTEGER PRIMARY KEY, user_id INTEGER, name TEXT, branch TEXT, year TEXT, status TEXT, photo TEXT, skills TEXT, contact TEXT, rating INTEGER DEFAULT 5, created_at TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS mentees (id INTEGER PRIMARY KEY, user_id INTEGER, name TEXT, branch TEXT, year TEXT, interest TEXT, contact TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS notes (id INTEGER PRIMARY KEY, title TEXT, subject TEXT, semester TEXT, student_name TEXT, price INTEGER, description TEXT, contact TEXT, status TEXT DEFAULT 'available', created_at TEXT)''')
    conn.commit(); conn.close()

init_db()

def login_required(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if 'user_id' not in session:
            return redirect('/login')
        return f(*args, **kwargs)
    return wrap

@app.route('/register', methods=['GET','POST'])
def register():
    if request.method == 'POST':
        conn = sqlite3.connect(DB); c = conn.cursor()
        try:
            c.execute("INSERT INTO users (name, email, password) VALUES (?,?,?)", (request.form['name'], request.form['email'], request.form['password']))
            conn.commit(); conn.close()
            return redirect('/login')
        except:
            conn.close()
            return "Email already exists!"
    return render_template('register.html')

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        conn = sqlite3.connect(DB); conn.row_factory = sqlite3.Row
        user = conn.execute("SELECT * FROM users WHERE email=? AND password=?", (request.form['email'], request.form['password'])).fetchone()
        conn.close()
        if user:
            session['user_id'] = user['id']; session['user_name'] = user['name']
            return redirect('/')
        else:
            return "Invalid Login!"
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear(); return redirect('/login')

@app.route('/')
@login_required
def home():
    conn = sqlite3.connect(DB); conn.row_factory = sqlite3.Row
    books = conn.execute("SELECT COUNT(*) FROM books").fetchone()[0]
    issued_count = conn.execute("SELECT COUNT(*) FROM issued WHERE status='issued'").fetchone()[0]
    mentors = conn.execute("SELECT COUNT(*) FROM mentors").fetchone()[0]
    notes = conn.execute("SELECT COUNT(*) FROM notes WHERE status='available'").fetchone()[0]
    conn.close()
    return render_template('index.html', books=books, issued_count=issued_count, mentors=mentors, notes=notes)

# ===== LIBRARY MODULE =====
@app.route('/library')
@login_required
def library():
    conn = sqlite3.connect(DB); conn.row_factory = sqlite3.Row
    books = conn.execute("SELECT * FROM books ORDER BY id DESC").fetchall()
    issued = conn.execute("SELECT issued.*, books.title, books.author FROM issued JOIN books ON issued.book_id = books.id ORDER BY issued.id DESC").fetchall()
    # Fine calculation
    today = datetime.now().date()
    for row in issued:
        if row['status'] == 'issued':
            due = datetime.strptime(row['due_date'], "%Y-%m-%d").date()
            if today > due:
                days = (today - due).days
                fine = days * 100
                conn.execute("UPDATE issued SET fine=? WHERE id=?", (fine, row['id']))
    conn.commit()
    issued = conn.execute("SELECT issued.*, books.title, books.author FROM issued JOIN books ON issued.book_id = books.id ORDER BY issued.id DESC").fetchall()
    conn.close()
    return render_template('library.html', books=books, issued=issued)

@app.route('/library/add', methods=['GET','POST'])
@login_required
def add_book():
    if request.method == 'POST':
        conn = sqlite3.connect(DB)
        conn.execute("INSERT INTO books (title, author, isbn, quantity, available, added_by, added_at) VALUES (?,?,?,?,?,?,?)",
                     (request.form['title'], request.form['author'], request.form['isbn'], int(request.form['quantity']), int(request.form['quantity']), session['user_id'], datetime.now().strftime("%d %b %Y")))
        conn.commit(); conn.close()
        return redirect('/library')
    return render_template('add_book.html')

@app.route('/library/issue', methods=['POST'])
@login_required
def issue_book():
    conn = sqlite3.connect(DB)
    book_id = request.form['book_id']
    student_name = request.form['student_name']
    book = conn.execute("SELECT * FROM books WHERE id=?", (book_id,)).fetchone()
    if book and book[4] > 0:
        issue_date = datetime.now().date()
        due_date = issue_date + timedelta(days=7)
        conn.execute("INSERT INTO issued (book_id, student_id, student_name, issue_date, due_date, status) VALUES (?,?,?,?,?,?)",
                     (book_id, session['user_id'], student_name, str(issue_date), str(due_date), 'issued'))
        conn.execute("UPDATE books SET available = available - 1 WHERE id=?", (book_id,))
        conn.commit()
    conn.close()
    return redirect('/library')

@app.route('/library/return/<int:id>')
@login_required
def return_book(id):
    conn = sqlite3.connect(DB)
    conn.execute("UPDATE issued SET status='returned', return_date=? WHERE id=?", (str(datetime.now().date()), id))
    book_id = conn.execute("SELECT book_id FROM issued WHERE id=?", (id,)).fetchone()[0]
    conn.execute("UPDATE books SET available = available + 1 WHERE id=?", (book_id,))
    conn.commit(); conn.close()
    return redirect('/library')

# ===== MENTOR MODULE =====
@app.route('/mentors')
@login_required
def mentors():
    conn = sqlite3.connect(DB); conn.row_factory = sqlite3.Row
    seniors = conn.execute("SELECT * FROM mentors ORDER BY id DESC").fetchall()
    juniors = conn.execute("SELECT * FROM mentees ORDER BY id DESC").fetchall()
    conn.close()
    return render_template('mentors.html', seniors=seniors, juniors=juniors)

@app.route('/mentors/senior', methods=['GET','POST'])
@login_required
def senior_register():
    if request.method == 'POST':
        photo = request.files['photo']
        filename = ""
        if photo:
            filename = secure_filename(photo.filename)
            photo.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        conn = sqlite3.connect(DB)
        conn.execute("INSERT INTO mentors (user_id, name, branch, year, status, photo, skills, contact, created_at) VALUES (?,?,?,?,?,?,?,?,?)",
                     (session['user_id'], request.form['name'], request.form['branch'], request.form['year'], request.form['status'], filename, request.form['skills'], request.form['contact'], datetime.now().strftime("%d %b")))
        conn.commit(); conn.close()
        return redirect('/mentors')
    return render_template('mentor_senior.html')

@app.route('/mentors/junior', methods=['GET','POST'])
@login_required
def junior_register():
    if request.method == 'POST':
        conn = sqlite3.connect(DB)
        conn.execute("INSERT INTO mentees (user_id, name, branch, year, interest, contact) VALUES (?,?,?,?,?,?)",
                     (session['user_id'], request.form['name'], request.form['branch'], request.form['year'], request.form['interest'], request.form['contact']))
        conn.commit(); conn.close()
        return redirect('/mentors')
    return render_template('mentor_junior.html')

# ===== NOTES MODULE =====
@app.route('/notes')
@login_required
def notes():
    conn = sqlite3.connect(DB); conn.row_factory = sqlite3.Row
    items = conn.execute("SELECT * FROM notes WHERE status='available' ORDER BY id DESC").fetchall()
    conn.close()
    return render_template('notes.html', items=items)

@app.route('/notes/sell', methods=['GET','POST'])
@login_required
def sell_notes():
    if request.method == 'POST':
        conn = sqlite3.connect(DB)
        conn.execute("INSERT INTO notes (title, subject, semester, student_name, price, description, contact, created_at) VALUES (?,?,?,?,?,?,?,?)",
                     (request.form['title'], request.form['subject'], request.form['semester'], request.form['student_name'], request.form['price'], request.form['description'], request.form['contact'], datetime.now().strftime("%d %b")))
        conn.commit(); conn.close()
        return redirect('/notes')
    return render_template('sell_notes.html')

from werkzeug.security import generate_password_hash

@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        username = request.form.get('username')
        new_pass = request.form.get('new_password')
        user = User.query.filter((User.username==username) | (User.email==username)).first()
        if user:
            user.password = generate_password_hash(new_pass)
            db.session.commit()
            flash('Password reset ho gaya, ab login karo!')
            return redirect('/login')
        else:
            flash('Username / Email nahi mila')
    return render_template('forgot_password.html')
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
