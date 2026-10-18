from flask import Flask, render_template, request, redirect, session, flash, url_for
import sqlite3, os
from datetime import date, timedelta, datetime
from werkzeug.utils import secure_filename
from functools import wraps

app = Flask(__name__)
app.secret_key = 'kabir_luxury_final'
app.config['UPLOAD_FOLDER'] = 'static/uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
DB = 'campus_final.db'

def init_db():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, name TEXT, email TEXT UNIQUE, password TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS books (id INTEGER PRIMARY KEY, title TEXT, author TEXT, isbn TEXT, quantity INTEGER, available INTEGER, added_by INTEGER, added_at TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS issued (id INTEGER PRIMARY KEY, book_id INTEGER, student_id INTEGER, student_name TEXT, issue_date TEXT, due_date TEXT, return_date TEXT, status TEXT DEFAULT 'issued', fine INTEGER DEFAULT 0)")
    c.execute("CREATE TABLE IF NOT EXISTS mentors (id INTEGER PRIMARY KEY, user_id INTEGER, name TEXT, branch TEXT, year TEXT, status TEXT, photo TEXT, skills TEXT, contact TEXT, created_at TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS mentees (id INTEGER PRIMARY KEY, user_id INTEGER, name TEXT, branch TEXT, year TEXT, interest TEXT, contact TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS notes (id INTEGER PRIMARY KEY, title TEXT, subject TEXT, semester TEXT, student_name TEXT, price INTEGER, description TEXT, contact TEXT, status TEXT DEFAULT 'available', created_at TEXT)")
    conn.commit(); conn.close()
init_db()

# --- YAHI TERI REQUIREMENT KA MAIN FIX HAI ---
def login_required(f):
    @wraps(f)
    def wrap(*a, **kw):
        if 'user_id' not in session: 
            return redirect('/login')
        return f(*a, **kw)
    return wrap

# Agar login hai to login/register pe wapas home bhej do
@app.route('/register', methods=['GET','POST'])
def register():
    if 'user_id' in session:
        return redirect('/')
    if request.method=='POST':
        try:
            conn=sqlite3.connect(DB)
            conn.execute("INSERT INTO users (name,email,password) VALUES (?,?,?)",(request.form['name'],request.form['email'],request.form['password']))
            conn.commit(); conn.close()
            flash("Account created! Login now","success")
            return redirect('/login')
        except:
            flash("Email already exists","danger")
    return render_template('register.html')

@app.route('/login', methods=['GET','POST'])
def login():
    if 'user_id' in session:
        return redirect('/') # login hai to direct home
    if request.method=='POST':
        e=request.form.get('email'); p=request.form.get('password')
        conn=sqlite3.connect(DB); conn.row_factory=sqlite3.Row
        u=conn.execute("SELECT * FROM users WHERE (email=? OR name=?) AND password=?",(e,e,p)).fetchone()
        conn.close()
        if u:
            session['user_id']=u['id']
            session['user_name']=u['name']
            return redirect('/') # login ke baad hi home khulega
        flash("Invalid Email or Password","danger")
    return render_template('login.html')

@app.route('/logout')
def logout(): 
    session.clear()
    return redirect('/login')

@app.route('/forgot_password', methods=['GET','POST'])
def forgot_password():
    if 'user_id' in session:
        return redirect('/')
    if request.method=='POST':
        email=request.form.get('username'); newp=request.form.get('new_password')
        conn=sqlite3.connect(DB); cur=conn.cursor()
        cur.execute("SELECT * FROM users WHERE email=? OR name=?",(email,email)); user=cur.fetchone()
        if user and newp:
            cur.execute("UPDATE users SET password=? WHERE email=? OR name=?",(newp,email,email))
            conn.commit(); conn.close()
            flash("Password updated","success")
            return redirect('/login')
        conn.close()
        flash('User not found','danger')
    return render_template('forgot_password.html')

# --- YE PAGE AB SIRF LOGIN KE BAAD KHULEGA ---
@app.route('/')
@login_required
def home():
    conn=sqlite3.connect(DB); conn.row_factory=sqlite3.Row
    books=conn.execute("SELECT COUNT(*) as c FROM books").fetchone()['c']
    ic=conn.execute("SELECT COUNT(*) as c FROM issued WHERE status='issued'").fetchone()['c']
    mentors=conn.execute("SELECT COUNT(*) as c FROM mentors").fetchone()['c']
    notes=conn.execute("SELECT COUNT(*) as c FROM notes").fetchone()['c']
    conn.close()
    return render_template('index.html', books=books, issued_count=ic, mentors=mentors, notes=notes)

# Baaki sab bhi protected
@app.route('/library')
@login_required
def library():
    conn=sqlite3.connect(DB); conn.row_factory=sqlite3.Row
    books=conn.execute("SELECT * FROM books ORDER BY id DESC").fetchall()
    issued=conn.execute("SELECT issued.id, issued.student_name, issued.issue_date, issued.due_date, issued.status, issued.fine, books.title FROM issued JOIN books ON issued.book_id=books.id ORDER BY issued.id DESC").fetchall()
    conn.close()
    return render_template('library.html', books=books, issued=issued)

@app.route('/library/add', methods=['GET','POST'])
@app.route('/add_book', methods=['GET','POST'])
@login_required
def add_book():
    if request.method=='POST':
        conn=sqlite3.connect(DB)
        conn.execute("INSERT INTO books (title,author,isbn,quantity,available,added_by,added_at) VALUES (?,?,?,?,?,?,?)",(request.form['title'],request.form['author'],request.form['isbn'],int(request.form['quantity']),int(request.form['quantity']),session['user_id'],datetime.now().strftime("%d %b")))
        conn.commit(); conn.close()
        return redirect('/library')
    return render_template('add_book.html')

@app.route('/library/issue', methods=['POST'])
@login_required
def issue_book():
    conn=sqlite3.connect(DB); conn.row_factory=sqlite3.Row
    bid=request.form['book_id']; sname=request.form['student_name']
    b=conn.execute("SELECT * FROM books WHERE id=?",(bid,)).fetchone()
    if b and b['available']>0:
        idate=date.today(); ddate=idate+timedelta(days=7)
        conn.execute("INSERT INTO issued (book_id,student_id,student_name,issue_date,due_date,status) VALUES (?,?,?,?,?,?)",(bid,session['user_id'],sname,str(idate),str(ddate),'issued'))
        conn.execute("UPDATE books SET available=available-1 WHERE id=?",(bid,))
        conn.commit()
    conn.close()
    return redirect('/library')

@app.route('/library/return/<int:id>')
@login_required
def return_book(id):
    conn=sqlite3.connect(DB)
    row=conn.execute("SELECT book_id FROM issued WHERE id=?",(id,)).fetchone()
    conn.execute("UPDATE issued SET status='returned', return_date=? WHERE id=?",(str(date.today()),id))
    if row: conn.execute("UPDATE books SET available=available+1 WHERE id=?",(row[0],))
    conn.commit(); conn.close()
    return redirect('/library')

@app.route('/mentors')
@login_required
def mentors_page():
    conn=sqlite3.connect(DB); conn.row_factory=sqlite3.Row
    seniors=conn.execute("SELECT * FROM mentors ORDER BY id DESC").fetchall()
    juniors=conn.execute("SELECT * FROM mentees ORDER BY id DESC").fetchall()
    conn.close()
    return render_template('mentors.html', seniors=seniors, juniors=juniors)

@app.route('/mentors/senior', methods=['GET','POST'])
@app.route('/mentor_senior', methods=['GET','POST'])
@login_required
def senior_register():
    if request.method=='POST':
        f=request.files.get('photo'); filename=""
        if f and f.filename:
            import time; filename=f"{int(time.time())}_{secure_filename(f.filename)}"; f.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        conn=sqlite3.connect(DB)
        conn.execute("INSERT INTO mentors (user_id,name,branch,year,status,photo,skills,contact,created_at) VALUES (?,?,?,?,?,?,?,?,?)",(session['user_id'],request.form['name'],request.form['branch'],request.form['year'],request.form['status'],filename,request.form['skills'],request.form['contact'],datetime.now().strftime("%d %b")))
        conn.commit(); conn.close()
        return redirect('/mentors')
    return render_template('mentor_senior.html')

@app.route('/mentors/junior', methods=['GET','POST'])
@app.route('/mentor_junior', methods=['GET','POST'])
@login_required
def junior_register():
    if request.method=='POST':
        conn=sqlite3.connect(DB)
        conn.execute("INSERT INTO mentees (user_id,name,branch,year,interest,contact) VALUES (?,?,?,?,?,?)",(session['user_id'],request.form['name'],request.form['branch'],request.form['year'],request.form['interest'],request.form['contact']))
        conn.commit(); conn.close()
        return redirect('/mentors')
    return render_template('mentor_junior.html')

@app.route('/notes')
@login_required
def notes_page():
    conn=sqlite3.connect(DB); conn.row_factory=sqlite3.Row
    items=conn.execute("SELECT * FROM notes ORDER BY id DESC").fetchall()
    conn.close()
    return render_template('notes.html', items=items)
@app.route('/sell_notes', methods=['GET','POST'])
@login_required
def sell_notes():
    if request.method=='POST':
        conn=sqlite3.connect(DB)
        conn.execute("INSERT INTO notes (title,subject,semester,student_name,price,description,contact,created_at) VALUES (?,?,?,?,?,?,?,?)",(request.form['title'],request.form['subject'],request.form['semester'],request.form['student_name'],request.form['price'],request.form['description'],request.form['contact'],datetime.now().strftime("%d %b")))
        conn.commit(); conn.close()
        return redirect('/notes')
    return render_template('sell_notes.html')

if __name__=='__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)