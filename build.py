import pathlib

root = pathlib.Path(".")  # Yahi folder jisme build.py hai

# folders
(root / "static" / "uploads").mkdir(parents=True, exist_ok=True)
(root / "templates").mkdir(parents=True, exist_ok=True)

# --- ALL FILES ---
files = {
"app.py": '''
from flask import Flask, render_template, request, redirect, session, flash
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

def login_required(f):
    @wraps(f)
    def wrap(*a, **kw):
        if 'user_id' not in session: return redirect('/login')
        return f(*a, **kw)
    return wrap

@app.route('/register', methods=['GET','POST'])
def register():
    if request.method=='POST':
        try:
            conn=sqlite3.connect(DB); conn.execute("INSERT INTO users (name,email,password) VALUES (?,?,?)",(request.form['name'],request.form['email'],request.form['password'])); conn.commit(); conn.close(); return redirect('/login')
        except: flash("Email exists","danger")
    return render_template('register.html')

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method=='POST':
        e=request.form.get('email'); p=request.form.get('password')
        conn=sqlite3.connect(DB); conn.row_factory=sqlite3.Row
        u=conn.execute("SELECT * FROM users WHERE (email=? OR name=?) AND password=?",(e,e,p)).fetchone(); conn.close()
        if u: session['user_id']=u['id']; session['user_name']=u['name']; return redirect('/')
        flash("Invalid","danger")
    return render_template('login.html')

@app.route('/logout')
def logout(): session.clear(); return redirect('/login')

@app.route('/forgot_password', methods=['GET','POST'])
def forgot_password():
    if request.method=='POST':
        email=request.form.get('username'); newp=request.form.get('new_password')
        conn=sqlite3.connect(DB); cur=conn.cursor()
        cur.execute("SELECT * FROM users WHERE email=? OR name=?",(email,email)); user=cur.fetchone()
        if user and newp: cur.execute("UPDATE users SET password=? WHERE email=? OR name=?",(newp,email,email)); conn.commit(); conn.close(); return redirect('/login')
        conn.close(); flash('User not found','danger')
    return render_template('forgot_password.html')

@app.route('/')
@login_required
def home():
    conn=sqlite3.connect(DB); conn.row_factory=sqlite3.Row
    books=conn.execute("SELECT COUNT(*) as c FROM books").fetchone()['c']; ic=conn.execute("SELECT COUNT(*) as c FROM issued WHERE status='issued'").fetchone()['c']; mentors=conn.execute("SELECT COUNT(*) as c FROM mentors").fetchone()['c']; notes=conn.execute("SELECT COUNT(*) as c FROM notes").fetchone()['c']; conn.close()
    return render_template('index.html', books=books, issued_count=ic, mentors=mentors, notes=notes)

@app.route('/library')
@login_required
def library():
    conn=sqlite3.connect(DB); conn.row_factory=sqlite3.Row; books=conn.execute("SELECT * FROM books ORDER BY id DESC").fetchall(); issued=conn.execute("SELECT issued.id, issued.student_name, issued.issue_date, issued.due_date, issued.status, issued.fine, books.title FROM issued JOIN books ON issued.book_id=books.id ORDER BY issued.id DESC").fetchall(); conn.close(); return render_template('library.html', books=books, issued=issued)

@app.route('/library/add', methods=['GET','POST'])
@app.route('/add_book', methods=['GET','POST'])
@login_required
def add_book():
    if request.method=='POST':
        conn=sqlite3.connect(DB); conn.execute("INSERT INTO books (title,author,isbn,quantity,available,added_by,added_at) VALUES (?,?,?,?,?,?,?)",(request.form['title'],request.form['author'],request.form['isbn'],int(request.form['quantity']),int(request.form['quantity']),session['user_id'],datetime.now().strftime("%d %b"))); conn.commit(); conn.close(); return redirect('/library')
    return render_template('add_book.html')

@app.route('/library/issue', methods=['POST'])
@login_required
def issue_book():
    conn=sqlite3.connect(DB); conn.row_factory=sqlite3.Row; bid=request.form['book_id']; sname=request.form['student_name']; b=conn.execute("SELECT * FROM books WHERE id=?",(bid,)).fetchone()
    if b and b['available']>0:
        idate=date.today(); ddate=idate+timedelta(days=7)
        conn.execute("INSERT INTO issued (book_id,student_id,student_name,issue_date,due_date,status) VALUES (?,?,?,?,?,?)",(bid,session['user_id'],sname,str(idate),str(ddate),'issued')); conn.execute("UPDATE books SET available=available-1 WHERE id=?",(bid,)); conn.commit()
    conn.close(); return redirect('/library')

@app.route('/library/return/<int:id>')
@login_required
def return_book(id):
    conn=sqlite3.connect(DB); row=conn.execute("SELECT book_id FROM issued WHERE id=?",(id,)).fetchone(); conn.execute("UPDATE issued SET status='returned', return_date=? WHERE id=?",(str(date.today()),id)); 
    if row: conn.execute("UPDATE books SET available=available+1 WHERE id=?",(row[0],))
    conn.commit(); conn.close(); return redirect('/library')

@app.route('/mentors')
@login_required
def mentors_page():
    conn=sqlite3.connect(DB); conn.row_factory=sqlite3.Row; seniors=conn.execute("SELECT * FROM mentors ORDER BY id DESC").fetchall(); juniors=conn.execute("SELECT * FROM mentees ORDER BY id DESC").fetchall(); conn.close(); return render_template('mentors.html', seniors=seniors, juniors=juniors)

@app.route('/mentors/senior', methods=['GET','POST'])
@app.route('/mentor_senior', methods=['GET','POST'])
@login_required
def senior_register():
    if request.method=='POST':
        f=request.files.get('photo'); filename=""
        if f and f.filename:
            import time; filename=f"{int(time.time())}_{secure_filename(f.filename)}"; f.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        conn=sqlite3.connect(DB); conn.execute("INSERT INTO mentors (user_id,name,branch,year,status,photo,skills,contact,created_at) VALUES (?,?,?,?,?,?,?,?,?)",(session['user_id'],request.form['name'],request.form['branch'],request.form['year'],request.form['status'],filename,request.form['skills'],request.form['contact'],datetime.now().strftime("%d %b"))); conn.commit(); conn.close(); return redirect('/mentors')
    return render_template('mentor_senior.html')

@app.route('/mentors/junior', methods=['GET','POST'])
@app.route('/mentor_junior', methods=['GET','POST'])
@login_required
def junior_register():
    if request.method=='POST': conn=sqlite3.connect(DB); conn.execute("INSERT INTO mentees (user_id,name,branch,year,interest,contact) VALUES (?,?,?,?,?,?)",(session['user_id'],request.form['name'],request.form['branch'],request.form['year'],request.form['interest'],request.form['contact'])); conn.commit(); conn.close(); return redirect('/mentors')
    return render_template('mentor_junior.html')

@app.route('/notes')
@login_required
def notes_page():
    conn=sqlite3.connect(DB); conn.row_factory=sqlite3.Row; items=conn.execute("SELECT * FROM notes ORDER BY id DESC").fetchall(); conn.close(); return render_template('notes.html', items=items)

@app.route('/notes/sell', methods=['GET','POST'])
@app.route('/sell_notes', methods=['GET','POST'])
@login_required
def sell_notes():
    if request.method=='POST': conn=sqlite3.connect(DB); conn.execute("INSERT INTO notes (title,subject,semester,student_name,price,description,contact,created_at) VALUES (?,?,?,?,?,?,?,?)",(request.form['title'],request.form['subject'],request.form['semester'],request.form['student_name'],request.form['price'],request.form['description'],request.form['contact'],datetime.now().strftime("%d %b"))); conn.commit(); conn.close(); return redirect('/notes')
    return render_template('sell_notes.html')

if __name__=='__main__': app.run(host='0.0.0.0', port=5000, debug=True)
''',

"requirements.txt": "Flask==2.3.3\\nWerkzeug==2.3.7\\n",
"Procfile": "web: gunicorn app:app",
".gitignore": "campus_final.db\\n__pycache__/\\nstatic/uploads/*\\n!static/uploads/.gitkeep\\n",
"static/style.css": "*{margin:0;padding:0;box-sizing:border-box;font-family:'Segoe UI',system-ui,sans-serif}body{background:linear-gradient(rgba(0,0,0,0.65),rgba(0,0,0,0.78)),url('https://images.unsplash.com/photo-1481627834876-b7833e8f5570?q=80&w=2000') no-repeat center center fixed;background-size:cover;min-height:100vh;color:#fff}.navbar{background:rgba(8,8,8,0.94);backdrop-filter:blur(12px);border-bottom:1px solid rgba(255,215,0,0.25);padding:14px 18px;display:flex;justify-content:space-between;align-items:center;position:sticky;top:0;z-index:99;flex-wrap:wrap;gap:10px}.brand{color:#FFD700;font-weight:900;letter-spacing:1.8px;font-size:20px;text-decoration:none}.navs{display:flex;gap:14px;flex-wrap:wrap;align-items:center}.navs a{color:#cfcfcf;text-decoration:none;font-size:13px;font-weight:700}.navs a:hover{color:#FFD700}.container{padding:18px 12px;max-width:1200px;margin:0 auto}.main-box{background:rgba(14,14,14,0.88);backdrop-filter:blur(16px);border:1px solid rgba(255,215,0,0.22);border-radius:22px;padding:22px;max-width:760px;margin:18px auto;box-shadow:0 18px 60px rgba(0,0,0,0.6)}.gold-btn{background:linear-gradient(90deg,#F7E27B,#E8A623);color:#000;font-weight:800;border:none;border-radius:30px;padding:11px 20px;text-decoration:none;display:inline-block;cursor:pointer;text-align:center}.gold-input,select{width:100%;padding:13px 15px;border-radius:12px;border:none;background:#FFF9C4;color:#111;margin-bottom:12px;outline:none;font-weight:600;font-size:14px}.card-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:16px;margin-top:18px}.lux-card{background:linear-gradient(135deg,rgba(22,22,22,0.96),rgba(50,38,12,0.92));border:1px solid rgba(255,215,0,0.22);border-radius:20px;padding:22px}.book-card{background:rgba(255,255,255,0.06);border:1px solid rgba(255,255,255,0.08);border-radius:14px;padding:14px;margin-bottom:12px}.table-wrapper{overflow-x:auto;border-radius:12px;margin-top:12px}table{width:100%;min-width:600px;border-collapse:collapse;background:rgba(255,255,255,0.04)}th{color:#FFD700;font-size:11px;padding:12px 8px;text-align:left;text-transform:uppercase}td{font-size:13px;padding:12px 8px;border-top:1px solid rgba(255,255,255,0.06)}.hero{text-align:center;padding:18px 0 8px}.hero h1{font-family:Georgia,serif;font-size:38px;font-weight:900;line-height:1.1;text-shadow:0 4px 18px #000}@media(max-width:600px){.hero h1{font-size:26px}}",
"static/manifest.json": '{"name":"CampusLux","short_name":"CampusLux","start_url":"/","display":"standalone","background_color":"#000","theme_color":"#FFD700"}',
"static/sw.js": "self.addEventListener('install',e=>self.skipWaiting());",
"static/uploads/.gitkeep": "",

"templates/base.html": '''<!DOCTYPE html><html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>CAMPUS LUX</title><link rel="stylesheet" href="/static/style.css"></head><body><div class="navbar"><a class="brand" href="/">CAMPUS LUX ✨</a><div class="navs"><a href="/">Home</a><a href="/library">Library</a><a href="/mentors">Mentors</a><a href="/notes">Notes</a><a href="/logout" style="color:#ff7a7a;">Logout</a></div></div><div class="container">{% block content %}{% endblock %}</div></body></html>''',
"templates/index.html": '''{% extends "base.html" %}{% block content %}<div class="hero"><h1>Galgotias<br>Campus Ecosystem</h1><p style="color:#FFD700;font-size:12px;margin-top:6px;">Kabir Singh | CSE | 3 Module Luxury App</p></div><div class="card-grid"><div class="lux-card"><div>📚 LIBRARY</div><h2 style="margin:10px 0;font-size:28px;">{{ books }} Books</h2><small>{{ issued_count }} Issued | ₹100/Day Fine</small><div style="margin-top:14px;"><a href="/library" class="gold-btn">Manage Library</a></div></div><div class="lux-card"><div>🤝 MENTORS</div><h2 style="margin:10px 0;font-size:28px;">{{ mentors }} Mentors</h2><small>Senior + Junior Connect</small><div style="margin-top:14px;"><a href="/mentors" class="gold-btn">Mentor Hub</a></div></div><div class="lux-card"><div>📝 NOTES</div><h2 style="margin:10px 0;font-size:28px;">{{ notes }} Notes</h2><small>Sell / Buy Notes</small><div style="margin-top:14px;"><a href="/notes" class="gold-btn">Notes Market</a></div></div></div>{% endblock %}''',
"templates/library.html": '''{% extends "base.html" %}{% block content %}<div class="main-box"><h2>📚 Library Management</h2><p style="color:#aaa;font-size:13px;margin:6px 0 12px;">Book Add, Issue, Return, ₹100/Day Fine</p><a href="/library/add" class="gold-btn" style="width:100%;">+ Add New Book</a><h3 style="margin:18px 0 10px;">Available Books</h3>{% for book in books %}<div class="book-card"><b>{{ book.title }}</b><br><small style="color:#bbb;">Author: {{ book.author }} | ISBN: {{ book.isbn }} | Qty: {{ book.available }}/{{ book.quantity }}</small><form action="/library/issue" method="POST" style="display:flex;gap:8px;margin-top:10px;"><input type="hidden" name="book_id" value="{{ book.id }}"><input class="gold-input" name="student_name" placeholder="Student Name" required style="margin:0;flex:1;"><button class="gold-btn">Issue</button></form></div>{% endfor %}<h3 style="margin:20px 0 10px;">Issued History</h3><div class="table-wrapper"><table><tr><th>Book</th><th>Student</th><th>Issue</th><th>Due</th><th>Status</th><th>Fine</th><th>Action</th></tr>{% for h in issued %}<tr><td>{{ h.title }}</td><td>{{ h.student_name }}</td><td>{{ h.issue_date }}</td><td>{{ h.due_date }}</td><td>{{ h.status }}</td><td>₹{{ h.fine }}</td><td>{% if h.status=='issued' %}<a href="/library/return/{{ h.id }}" class="gold-btn" style="padding:5px 12px;font-size:11px;">Return</a>{% else %}Returned{% endif %}</td></tr>{% endfor %}</table></div></div>{% endblock %}''',
"templates/add_book.html": '''{% extends "base.html" %}{% block content %}<div class="main-box" style="max-width:520px;"><h2 style="color:#FFD700;">+ Add New Book</h2><form method="POST" style="margin-top:14px;"><input class="gold-input" name="title" placeholder="Title" required><input class="gold-input" name="author" placeholder="Author" required><input class="gold-input" name="isbn" placeholder="ISBN"><input class="gold-input" name="quantity" type="number" placeholder="Quantity" required><button class="gold-btn" style="width:100%;">Add Book</button></form></div>{% endblock %}''',
"templates/mentors.html": '''{% extends "base.html" %}{% block content %}<div class="main-box"><h2>🤝 Mentor System</h2><div style="display:flex;gap:10px;margin:14px 0;flex-wrap:wrap;"><a href="/mentors/senior" class="gold-btn" style="font-size:12px;">Senior as Mentor Register</a><a href="/mentors/junior" class="gold-btn" style="font-size:12px;">Junior as Student Register</a></div><div style="display:grid;grid-template-columns:1fr 1fr;gap:18px;margin-top:18px;"><div><h4 style="color:#FFD700;margin-bottom:8px;">Senior Mentors</h4>{% for s in seniors %}<div class="book-card"><b>{{ s.name }} - {{ s.branch }}</b><br><small>{{ s.year }} | {{ s.status }}<br>Skills: {{ s.skills }}<br>Contact: {{ s.contact }}</small>{% if s.photo %}<br><img src="/static/uploads/{{ s.photo }}" style="width:60px;height:60px;border-radius:50%;object-fit:cover;margin-top:8px;border:2px solid #FFD700;">{% endif %}</div>{% endfor %}</div><div><h4 style="color:#FFD700;margin-bottom:8px;">Junior Students</h4>{% for j in juniors %}<div class="book-card"><b>{{ j.name }}</b><br><small>{{ j.branch }} | {{ j.interest }}</small></div>{% endfor %}</div></div></div>{% endblock %}''',
"templates/mentor_senior.html": '''{% extends "base.html" %}{% block content %}<div class="main-box" style="max-width:520px;"><h2>Senior Mentor Registration</h2><p style="color:#aaa;font-size:12px;">Passport Photo + Details</p><form method="POST" enctype="multipart/form-data" style="margin-top:14px;"><input class="gold-input" name="name" placeholder="Kabir Singh" required><input class="gold-input" name="branch" placeholder="CSE" required><input class="gold-input" name="year" placeholder="Year" required><select class="gold-input" name="status" required><option>Currently Pursuing</option><option>Passout Placed</option></select><label style="font-size:12px;color:#FFD700;">Passport Photo</label><input class="gold-input" type="file" name="photo" accept="image/*" required><input class="gold-input" name="skills" placeholder="Skills" required><input class="gold-input" name="contact" placeholder="Contact" required><button class="gold-btn" style="width:100%;">Register</button></form></div>{% endblock %}''',
"templates/mentor_junior.html": '''{% extends "base.html" %}{% block content %}<div class="main-box" style="max-width:520px;"><h2>Junior Registration</h2><form method="POST" style="margin-top:14px;"><input class="gold-input" name="name" placeholder="Name" required><input class="gold-input" name="branch" placeholder="Branch" required><input class="gold-input" name="year" placeholder="Year" required><input class="gold-input" name="interest" placeholder="Interest" required><input class="gold-input" name="contact" placeholder="Contact" required><button class="gold-btn" style="width:100%;">Register</button></form></div>{% endblock %}''',
"templates/login.html": '''{% extends "base.html" %}{% block content %}<div class="main-box" style="max-width:420px;text-align:center;"><h2 style="color:#FFD700;font-size:32px;">Login</h2><form method="POST" style="margin-top:16px;"><input class="gold-input" name="email" placeholder="Email" required><input class="gold-input" name="password" type="password" placeholder="Password" required><button class="gold-btn" style="width:100%;">Login</button></form></div>{% endblock %}''',
"templates/register.html": '''{% extends "base.html" %}{% block content %}<div class="main-box" style="max-width:420px;text-align:center;"><h2 style="color:#FFD700;font-size:32px;">Register</h2><form method="POST" style="margin-top:16px;"><input class="gold-input" name="name" placeholder="Name" required><input class="gold-input" name="email" type="email" placeholder="Email" required><input class="gold-input" name="password" type="password" placeholder="Password" required><button class="gold-btn" style="width:100%;">Register</button></form></div>{% endblock %}''',
"templates/forgot_password.html": '''{% extends "base.html" %}{% block content %}<div class="main-box" style="max-width:420px;text-align:center;"><h2 style="color:#FFD700;font-size:28px;">Reset Password</h2><form method="POST" style="margin-top:16px;"><input class="gold-input" name="username" placeholder="Email" required><input class="gold-input" name="new_password" type="password" placeholder="New Password" required><button class="gold-btn" style="width:100%;">Reset</button></form></div>{% endblock %}''',
"templates/notes.html": '''{% extends "base.html" %}{% block content %}<div class="main-box"><h2>📝 Notes Market</h2><a href="/notes/sell" class="gold-btn" style="margin:12px 0;">+ Sell Notes</a>{% for n in items %}<div class="book-card"><b>{{ n.title }}</b><br><small>{{ n.subject }} | ₹{{ n.price }} | {{ n.contact }}</small></div>{% endfor %}</div>{% endblock %}''',
"templates/sell_notes.html": '''{% extends "base.html" %}{% block content %}<div class="main-box" style="max-width:520px;"><h2 style="color:#FFD700;">Sell Notes</h2><form method="POST" style="margin-top:14px;"><input class="gold-input" name="title" placeholder="Title" required><input class="gold-input" name="subject" placeholder="Subject" required><input class="gold-input" name="semester" placeholder="Sem" required><input class="gold-input" name="student_name" placeholder="Your Name" required><input class="gold-input" name="price" type="number" placeholder="Price" required><input class="gold-input" name="description" placeholder="Desc"><input class="gold-input" name="contact" placeholder="Contact" required><button class="gold-btn" style="width:100%;">Sell</button></form></div>{% endblock %}''',
}

for path, content in files.items():
    p = root / path
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding='utf-8')

print("✅ Luxury Campus Hub Ready! Ab python app.py run karo")