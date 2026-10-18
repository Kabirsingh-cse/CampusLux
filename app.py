from flask import Flask, render_template, request, redirect, session, url_for, flash
import sqlite3, os
from datetime import datetime, timedelta
from werkzeug.utils import secure_filename
from functools import wraps

app = Flask(__name__)
app.secret_key = 'kabir_galgotias_2027'
app.config['UPLOAD_FOLDER'] = 'static/uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
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
    conn.commit()
    conn.close()

init_db()

def login_required(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if 'user_id' not in session:
            return redirect('/login')
        return f(*args, **kwargs)
    return wrap

# ===== AUTH =====
@app.route('/register', methods=['GET','POST'])
def register():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')
        conn = sqlite3.connect(DB)
        c = conn.cursor()
        try:
            c.execute("INSERT INTO users (name, email, password) VALUES (?,?,?)", (name, email, password))
            conn.commit()
            conn.close()
            flash("Register ho gaya! Ab login karo", "success")
            return redirect('/login')
        except sqlite3.IntegrityError:
            conn.close()
            flash("Ye Email pehle se exist karta hai!", "danger")
            return render_template('register.html')
    return render_template('register.html')

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        email_input = request.form.get('email') or request.form.get('username')
        password = request.form.get('password')

        if not email_input or not password:
            flash("Email aur Password dono bharo", "danger")
            return render_template('login.html')

        conn = sqlite3.connect(DB)
        conn.row_factory = sqlite3.Row
        user = conn.execute("SELECT * FROM users WHERE (email=? OR name=?) AND password=?", (email_input, email_input, password)).fetchone()
        conn.close()
        
        if user:
            session['user_id'] = user['id']
            session['user_name'] = user['name']
            return redirect('/')
        else:
            flash("Invalid Login! Email/Username ya Password galat hai", "danger")
            return render_template('login.html')
            
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')

# ===== FORGOT PASSWORD - FINAL FIX =====
@app.route('/forgot_password', methods=['GET', 'POST'])
@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email_input = request.form.get('username') or request.form.get('email')
        new_pass = request.form.get('new_password') or request.form.get('new_pass') or request.form.get('password')

        if not email_input or not new_pass:
            flash("Saare fields bharo", "danger")
            return render_template('forgot_password.html')

        conn = sqlite3.connect(DB)
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE email=? OR name=?", (email_input, email_input))
        user = c.fetchone()
        
        if user:
            c.execute("UPDATE users SET password=? WHERE email=? OR name=?", (new_pass, email_input, email_input))
            conn.commit()
            conn.close()
            flash('Password reset ho gaya! Ab naye password se login karo.', 'success')
            return redirect('/login')
        else:
            conn.close()
            flash('Ye Email / Username hamare database me nahi mila', 'danger')
            
    return render_template('forgot_password.html')

@app.route('/')
@login_required
def home():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    books = conn.execute("SELECT COUNT(*) as c FROM books").fetchone()['c']
    issued_count = conn.execute("SELECT COUNT(*) as c FROM issued WHERE status='issued'").fetchone()['c']
    mentors = conn.execute("SELECT COUNT(*) as c FROM mentors").fetchone()['c']
    notes = conn.execute("SELECT COUNT(*) as c FROM notes WHERE status='available'").fetchone()['c']
    conn.close()
    return render_template('index.html', books=books, issued_count=issued_count, mentors=mentors, notes=notes)

# ===== LIBRARY MODULE =====
@app.route('/library')
@login_required
def library():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    books = conn.execute("SELECT * FROM books ORDER BY id DESC").fetchall()
    issued = conn.execute("SELECT issued.*, books.title, books.author FROM issued JOIN books ON issued.book_id = books.id ORDER BY issued.id DESC").fetchall()
    today = datetime.now().date()
    for row in issued:
        if row['status'] == 'issued':
            try:
                due = datetime.strptime(row['due_date'], "%Y-%m-%d").date()
                if today > due:
                    days = (today - due).days
                    fine = days * 100
                    conn.execute("UPDATE issued SET fine=? WHERE id=?", (fine, row['id']))
            except:
                pass
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
        conn.commit()
        conn.close()
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
    book_id_row = conn.execute("SELECT book_id FROM issued WHERE id=?", (id,)).fetchone()
    if book_id_row:
        conn.execute("UPDATE books SET available = available + 1 WHERE id=?", (book_id_row[0],))
    conn.commit()
    conn.close()
    return redirect('/library')

# ===== MENTOR MODULE =====
@app.route('/mentors')
@login_required
def mentors():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    seniors = conn.execute("SELECT * FROM mentors ORDER BY id DESC").fetchall()
    juniors = conn.execute("SELECT * FROM mentees ORDER BY id DESC").fetchall()
    conn.close()
    return render_template('mentors.html', seniors=seniors, juniors=juniors)

@app.route('/mentors/senior', methods=['GET','POST'])
@login_required
def senior_register():
    if request.method == 'POST':
        photo = request.files.get('photo')
        filename = ""
        if photo and photo.filename:
            filename = secure_filename(photo.filename)
            photo.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        conn = sqlite3.connect(DB)
        conn.execute("INSERT INTO mentors (user_id, name, branch, year, status, photo, skills, contact, created_at) VALUES (?,?,?,?,?,?,?,?,?)",
                     (session['user_id'], request.form['name'], request.form['branch'], request.form['year'], request.form['status'], filename, request.form['skills'], request.form['contact'], datetime.now().strftime("%d %b")))
        conn.commit()
        conn.close()
        return redirect('/mentors')
    return render_template('mentor_senior.html')

@app.route('/mentors/junior', methods=['GET','POST'])
@login_required
def junior_register():
    if request.method == 'POST':
        conn = sqlite3.connect(DB)
        conn.execute("INSERT INTO mentees (user_id, name, branch, year, interest, contact) VALUES (?,?,?,?,?,?)",
                     (session['user_id'], request.form['name'], request.form['branch'], request.form['year'], request.form['interest'], request.form['contact']))
        conn.commit()
        conn.close()
        return redirect('/mentors')
    return render_template('mentor_junior.html')

# ===== NOTES MODULE =====
@app.route('/notes')
@login_required
def notes():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
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
        conn.commit()
        conn.close()
        return redirect('/notes')
    return render_template('sell_notes.html')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)