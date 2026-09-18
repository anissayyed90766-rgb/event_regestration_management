
import http.server, socketserver, sqlite3, hashlib, secrets, urllib.parse, html, datetime, os, base64, re, smtplib
from email.message import EmailMessage
from http import cookies

BASE=os.path.dirname(os.path.abspath(__file__)); DB=os.path.join(BASE,"compesa.db")
PORT=int(os.environ.get("PORT","8000"))
COLLEGE="COMPESA — Computer Engineering Students Association"; DEPT="Department of Computer Engineering"

CSS="""*{box-sizing:border-box}body{font-family:Inter,Arial,sans-serif;margin:0;background:#f5f7fb;color:#172033}nav{background:#101828;color:#fff;padding:14px 5%;display:flex;gap:16px;align-items:center;flex-wrap:wrap}nav a{color:#fff;text-decoration:none}.brand{font-weight:800;margin-right:auto}.wrap{max-width:1150px;margin:28px auto;padding:0 18px}.hero{background:linear-gradient(135deg,#172554,#4338ca);color:#fff;border-radius:20px;padding:38px}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:18px}.card{background:#fff;border-radius:16px;padding:20px;box-shadow:0 4px 18px #0001;margin:14px 0}.btn{display:inline-block;background:#4338ca;color:#fff;padding:10px 15px;border-radius:9px;text-decoration:none;border:0;cursor:pointer}.alt{background:#0f766e}.danger{background:#b42318}.muted{color:#667085}.badge{padding:5px 9px;border-radius:20px;background:#e0e7ff;display:inline-block}.stats{font-size:28px;font-weight:800}input,select,textarea{width:100%;padding:10px;margin:6px 0 14px;border:1px solid #d0d5dd;border-radius:8px}label{font-weight:600}table{width:100%;border-collapse:collapse;background:#fff}th,td{padding:10px;border-bottom:1px solid #eaecf0;text-align:left}.center{text-align:center}.qr{max-width:260px;max-height:260px;border:8px solid #fff;box-shadow:0 2px 12px #0002}@media(max-width:600px){.hero{padding:25px}table{display:block;overflow:auto;font-size:13px}}"""

def h(x): return html.escape(str(x or ""))
def now(): return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
def q(qs,k,d=""): return qs.get(k,[d])[0]
def conn(): 
    c=sqlite3.connect(DB); c.row_factory=sqlite3.Row; return c
def sha(x): return hashlib.sha256(x.encode()).hexdigest()

def init():
    c=conn()
    c.executescript("""
    CREATE TABLE IF NOT EXISTS admins(id INTEGER PRIMARY KEY,username TEXT UNIQUE,password TEXT,role TEXT);
    CREATE TABLE IF NOT EXISTS students(id INTEGER PRIMARY KEY AUTOINCREMENT,student_uid TEXT UNIQUE,name TEXT,student_id TEXT UNIQUE,email TEXT UNIQUE,password TEXT,mobile TEXT,branch TEXT,year TEXT,division TEXT,gender TEXT,college TEXT,created TEXT);
    CREATE TABLE IF NOT EXISTS events(id INTEGER PRIMARY KEY AUTOINCREMENT,code TEXT UNIQUE,name TEXT,date TEXT,time TEXT,venue TEXT,description TEXT,rules TEXT,eligibility TEXT,mode TEXT,max_team INTEGER,deadline TEXT,coordinator TEXT,contact TEXT,prize TEXT,status TEXT DEFAULT 'Open',payment_mode TEXT DEFAULT 'Cash / Online',payment_qr TEXT,created TEXT);
    CREATE TABLE IF NOT EXISTS registrations(id INTEGER PRIMARY KEY AUTOINCREMENT,reg_id TEXT UNIQUE,event_id INTEGER,student_uid TEXT,name TEXT,student_id TEXT,email TEXT,mobile TEXT,branch TEXT,year TEXT,division TEXT,gender TEXT,college TEXT,team_name TEXT,team_members TEXT,payment_method TEXT,payment_ref TEXT,payment_status TEXT DEFAULT 'Pending',status TEXT DEFAULT 'Pending',created TEXT);
    CREATE TABLE IF NOT EXISTS bookmarks(id INTEGER PRIMARY KEY AUTOINCREMENT,student_uid TEXT,event_id INTEGER,UNIQUE(student_uid,event_id));
    CREATE TABLE IF NOT EXISTS notifications(id INTEGER PRIMARY KEY AUTOINCREMENT,student_uid TEXT,title TEXT,body TEXT,read_flag INTEGER DEFAULT 0,created TEXT);
    CREATE TABLE IF NOT EXISTS attendance(id INTEGER PRIMARY KEY AUTOINCREMENT,reg_id TEXT UNIQUE,checked_in TEXT);
    CREATE TABLE IF NOT EXISTS results(id INTEGER PRIMARY KEY AUTOINCREMENT,event_id INTEGER,reg_id TEXT,position TEXT,prize TEXT,published INTEGER DEFAULT 0);
    CREATE TABLE IF NOT EXISTS announcements(id INTEGER PRIMARY KEY AUTOINCREMENT,title TEXT,body TEXT,created TEXT);
    """)
    if not c.execute("select 1 from admins where username='admin'").fetchone():
        c.execute("insert into admins(username,password,role) values(?,?,?)",("admin",sha("admin123"),"Super Admin"))
    if not c.execute("select 1 from events").fetchone():
        es=[("CC26","Code Clash","2026-09-25","10:00","Computer Engineering Lab","Competitive coding challenge.","Bring college ID. Follow coordinator instructions.","Engineering students.","Individual",1,"2026-09-24","COMPESA Team","compesa@example.com","Winner ₹5,000 | Runner-up ₹3,000 | Third ₹2,000","Open","Cash / Online",""),
            ("WB26","Web Battle","2026-09-27","11:00","Innovation Lab","Build a responsive web solution.","Follow the published theme.","Engineering students.","Team",3,"2026-09-26","COMPESA Team","compesa@example.com","Winner ₹7,000 | Runner-up ₹4,000 | Third ₹2,000","Open","Cash / Online","")]
        c.executemany("insert into events(code,name,date,time,venue,description,rules,eligibility,mode,max_team,deadline,coordinator,contact,prize,status,payment_mode,payment_qr,created) values(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",[x+(now(),) for x in es])
        c.execute("insert into announcements(title,body,created) values(?,?,?)",("Registrations Open","COMPESA 2026 registrations are open.","2026-09-18"))
    c.commit(); c.close()
init()

def layout(title,body,student=None):
    c=conn(); unread=0
    if student: unread=c.execute("select count(*) from notifications where student_uid=? and read_flag=0",(student["student_uid"],)).fetchone()[0]
    c.close()
    nav=f'<a class=brand href="/">COMPESA 3.0</a><a href="/">Home</a><a href="/events">Events</a><a href="/results">Results</a><a href="/announcements">Announcements</a>'
    if student: nav+=f'<a href="/student">My Panel{" 🔔"+str(unread) if unread else ""}</a><a href="/student/logout">Logout</a>'
    else: nav+='<a href="/student/login">Student Login</a><a href="/admin/login">Admin</a>'
    return f"<!doctype html><html><head><meta charset=utf-8><meta name=viewport content='width=device-width,initial-scale=1'><title>{h(title)}</title><style>{CSS}</style></head><body><nav>{nav}</nav><main class=wrap>{body}</main><footer class='wrap muted center'>© 2026 {COLLEGE} · {DEPT}</footer></body></html>"

def student_from(handler):
    ck=cookies.SimpleCookie(handler.headers.get("Cookie","")); token=ck.get("student_session")
    if not token:return None
    c=conn(); s=c.execute("select * from students where student_uid=?",(token.value,)).fetchone(); c.close(); return s

def set_session(handler,uid):
    handler.send_header("Set-Cookie",f"student_session={uid}; Path=/; HttpOnly; SameSite=Lax")

def event_card(e,student=None):
    c=conn(); marked=False
    if student: marked=bool(c.execute("select 1 from bookmarks where student_uid=? and event_id=?",(student["student_uid"],e["id"])).fetchone())
    c.close()
    star="❤️" if marked else "♡"
    return f"""<div class=card><span class=badge>{h(e["status"])}</span><h2>{h(e["name"])}</h2><p>📅 {h(e["date"])} · ⏰ {h(e["time"])}<br>📍 {h(e["venue"])}</p><p>{h(e["description"])}</p><a class=btn href="/event?id={e["id"]}">View Event</a> {"<span class=muted>"+star+" Bookmarked</span>" if student else ""}</div>"""

def send_mail(to,subject,text):
    host=os.environ.get("SMTP_HOST"); port=int(os.environ.get("SMTP_PORT","587")); user=os.environ.get("SMTP_USER"); pw=os.environ.get("SMTP_PASSWORD"); sender=os.environ.get("SMTP_FROM",user or "")
    if not (host and user and pw and sender): return False,"SMTP not configured"
    try:
        m=EmailMessage(); m["From"]=sender; m["To"]=to; m["Subject"]=subject; m.set_content(text)
        with smtplib.SMTP(host,port,timeout=10) as s:
            s.starttls(); s.login(user,pw); s.send_message(m)
        return True,"sent"
    except Exception as ex:return False,str(ex)

class App(http.server.BaseHTTPRequestHandler):
    def read(self):
        n=int(self.headers.get("Content-Length","0")); return urllib.parse.parse_qs(self.rfile.read(n).decode(),keep_blank_values=True)
    def out(self,code=200,ctype="text/html",data=b"",cookie=None):
        self.send_response(code); self.send_header("Content-Type",ctype); self.send_header("Content-Length",str(len(data)))
        if cookie:self.send_header("Set-Cookie",cookie)
        self.end_headers(); self.wfile.write(data)
    def redir(self,u,cookie=None):
        self.send_response(303); self.send_header("Location",u)
        if cookie:self.send_header("Set-Cookie",cookie)
        self.end_headers()
    def GET(self):
        u=urllib.parse.urlparse(self.path); p=u.path; qs=urllib.parse.parse_qs(u.query); c=conn(); s=student_from(self)
        if p=="/":
            es=c.execute("select * from events order by date,time").fetchall()
            body=f"<section class=hero><h1>{COLLEGE}</h1><p>Events, private student panel, registrations, payments, passes, results and certificates.</p><a class=btn href=/events>Browse Events</a></section><h2>Upcoming Events</h2><div class=grid>{''.join(event_card(e,s) for e in es)}</div>"
        elif p=="/events":
            term=q(qs,"q").lower(); es=c.execute("select * from events where lower(name) like ? or lower(venue) like ? order by date",("%"+term+"%","%"+term+"%")).fetchall()
            body=f"<h1>Events</h1><form><input name=q value='{h(q(qs,'q'))}' placeholder='Search events or venue'><button class=btn>Search</button></form><div class=grid>{''.join(event_card(e,s) for e in es)}</div>"
        elif p=="/event":
            e=c.execute("select * from events where id=?",(q(qs,"id"),)).fetchone()
            if not e:return self.out(404,data=b"Event not found")
            qr=f"<p><b>Online payment QR</b><br><img class=qr src='{h(e['payment_qr'])}'></p>" if e["payment_qr"] else "<p class=muted>Online payment QR will be shown here when configured by admin.</p>"
            cal=urllib.parse.quote(f"https://calendar.google.com/calendar/render?action=TEMPLATE&text={e['name']}&dates={e['date'].replace('-','')}T{e['time'].replace(':','')}00/{e['date'].replace('-','')}T{e['time'].replace(':','')}00&location={e['venue']}")
            body=f"""<div class=card><span class=badge>{h(e['status'])}</span><h1>{h(e['name'])}</h1><p>📅 {h(e['date'])} · ⏰ {h(e['time'])} · 📍 {h(e['venue'])}</p><p>{h(e['description'])}</p><h3>Rules</h3><p>{h(e['rules'])}</p><h3>Eligibility</h3><p>{h(e['eligibility'])}</p><p><b>{h(e['mode'])}</b> · Max team {h(e['max_team'])} · Deadline {h(e['deadline'])}</p><p>Coordinator: {h(e['coordinator'])} · {h(e['contact'])}</p><p>Prizes: {h(e['prize'])}</p><p>Payment: <b>{h(e['payment_mode'])}</b></p>{qr}<p><a class=btn href='/calendar?event={e['id']}'>Add to Calendar</a></p>"""
            if s: body+=f"""<form method=post action=/student/bookmark><input type=hidden name=event_id value={e['id']}><button class=btn alt>♡ Bookmark / Remove</button></form><br><a class=btn href='/register?event={e["id"]}'>Register Now</a>"""
            else: body+="<a class=btn href='/student/login'>Login to Register</a>"
            body+="</div>"
        elif p=="/register":
            if not s:return self.redir("/student/login?next="+urllib.parse.quote(self.path))
            e=c.execute("select * from events where id=?",(q(qs,"event"),)).fetchone()
            if not e:return self.out(404,data=b"Event not found")
            qr=f"<img class=qr src='{h(e['payment_qr'])}'>" if e["payment_qr"] else "<p class=muted>No online QR uploaded yet.</p>"
            body=f"""<h1>Register: {h(e['name'])}</h1><div class=card><p>Payment method</p><form method=post action=/register><input type=hidden name=event value={e['id']}><label>Payment</label><select name=payment_method><option>Cash</option><option>Online</option></select>{qr}<label>Payment reference (online, if available)</label><input name=payment_ref placeholder='Transaction ID / UTR'><label>Team name</label><input name=team_name><label>Team members</label><textarea name=team_members placeholder='One member per line'></textarea><button class=btn>Confirm Registration</button></form></div>"""
        elif p=="/student/login":
            body="<h1>Student Login</h1><div class=card><form method=post action=/student/login><label>Email</label><input name=email type=email required><label>Password</label><input name=password type=password required><button class=btn>Login</button></form><p>New student? <a href=/student/signup>Sign up</a></p></div>"
        elif p=="/student/signup":
            body="<h1>Student Signup</h1><div class=card><form method=post action=/student/signup>"+''.join(f"<label>{x.replace('_',' ').title()}</label><input name={x} required>" for x in ["name","student_id","email","mobile","branch","year","division","college"])+"<label>Gender</label><select name=gender><option>Prefer not to say</option><option>Male</option><option>Female</option><option>Other</option></select><label>Password</label><input name=password type=password minlength=6 required><button class=btn>Create Student Account</button></form></div>"
        elif p=="/student":
            if not s:return self.redir("/student/login")
            regs=c.execute("select r.*,e.name en,e.date,e.time,e.venue from registrations r join events e on e.id=r.event_id where r.student_uid=? order by r.id desc",(s["student_uid"],)).fetchall()
            ns=c.execute("select * from notifications where student_uid=? order by id desc",(s["student_uid"],)).fetchall()
            body=f"<h1>👤 My Student Panel</h1><div class=grid><div class=card><h2>{h(s['name'])}</h2><p><b>Unique Student ID:</b> {h(s['student_uid'])}</p><p>{h(s['student_id'])} · {h(s['email'])}<br>{h(s['branch'])} · Year {h(s['year'])} · Div {h(s['division'])}</p><a class=btn href=/student/profile>Edit Profile</a></div><div class=card><h2>🔔 Notifications</h2>{''.join(f"<p><b>{h(n['title'])}</b><br>{h(n['body'])}<br><small>{h(n['created'])}</small></p>" for n in ns[:8]) or '<p>No notifications.</p>'}</div></div><h2>🎟️ My Registrations</h2>"
            for r in regs:
                body+=f"<div class=card><h3>{h(r['en'])}</h3><p>{h(r['date'])} · {h(r['time'])} · {h(r['venue'])}</p><p>Registration ID: <b>{h(r['reg_id'])}</b> · Status: <span class=badge>{h(r['status'])}</span></p><p>Payment: {h(r['payment_method'])} · {h(r['payment_status'])}</p><a class=btn href='/pass?id={r["reg_id"]}'>Event Pass</a> <a class=btn alt href='/certificate?id={r["reg_id"]}'>Certificate</a></div>"
            bs=c.execute("select e.* from bookmarks b join events e on e.id=b.event_id where b.student_uid=?",(s["student_uid"],)).fetchall()
            body+="<h2>❤️ Bookmarked Events</h2><div class=grid>"+''.join(event_card(e,s) for e in bs)+"</div>"
        elif p=="/student/profile":
            if not s:return self.redir("/student/login")
            body=f"<h1>Profile</h1><div class=card><form method=post action=/student/profile><label>Name</label><input name=name value='{h(s['name'])}' required><label>Mobile</label><input name=mobile value='{h(s['mobile'])}'><label>Branch</label><input name=branch value='{h(s['branch'])}'><label>Year</label><input name=year value='{h(s['year'])}'><label>Division</label><input name=division value='{h(s['division'])}'><label>College</label><input name=college value='{h(s['college'])}'><button class=btn>Save</button></form></div>"
        elif p=="/student/logout":
            return self.redir("/", "student_session=; Path=/; Max-Age=0")
        elif p=="/pass":
            r=c.execute("select r.*,e.name en,e.date,e.time,e.venue,e.coordinator from registrations r join events e on e.id=r.event_id where r.reg_id=?",(q(qs,"id"),)).fetchone()
            if not r or not s or r["student_uid"]!=s["student_uid"]:return self.out(403,data=b"Private pass")
            body=f"<div class=card center><h1>🎟️ COMPESA Digital Event Pass</h1><h2>{h(r['en'])}</h2><div class=hero><h2>{h(r['reg_id'])}</h2><p>{h(r['name'])} · {h(r['student_id'])}</p><p>{h(r['date'])} · {h(r['time'])} · {h(r['venue'])}</p></div><p>Present this pass at entry.</p><button class=btn onclick='print()'>Print / Save as PDF</button></div>"
        elif p=="/certificate":
            r=c.execute("select r.*,e.name en,e.date,res.position,res.prize from registrations r join events e on e.id=r.event_id join results res on res.reg_id=r.reg_id where r.reg_id=? and res.published=1",(q(qs,"id"),)).fetchone()
            if not r or not s or r["student_uid"]!=s["student_uid"]:return self.out(403,data=b"Private certificate")
            body=f"<div class=card center style='padding:60px'><h1>CERTIFICATE OF ACHIEVEMENT</h1><p>This is proudly presented to</p><h1>{h(r['name'])}</h1><p>Student ID: {h(r['student_id'])}</p><p>for securing <b>{h(r['position'])}</b> in</p><h2>{h(r['en'])}</h2><p>held on {h(r['date'])}</p><p>Certificate ID: <b>CMP-{h(r['reg_id'])}</b></p><p>________________ &nbsp;&nbsp;&nbsp; ________________</p><p>Coordinator &nbsp;&nbsp;&nbsp;&nbsp;&nbsp; Head of Department</p><button class=btn onclick='print()'>Print / Save as PDF</button></div>"
        elif p=="/verify":
            rid=q(qs,"id"); r=c.execute("select r.name,r.student_id,e.name en,e.date,res.position from registrations r join events e on e.id=r.event_id join results res on res.reg_id=r.reg_id where r.reg_id=? and res.published=1",(rid,)).fetchone()
            body=f"<div class=card><h1>📜 Certificate Verification</h1>{('<h2>Valid Certificate</h2><p>'+h(r['name'])+' · '+h(r['en'])+' · '+h(r['position'])+'</p><p>Certificate ID: CMP-'+h(rid)+'</p>') if r else '<h2>Certificate not found or not published.</h2>'}</div>"
        elif p=="/results":
            rr=c.execute("select e.name en,r.name pn,x.position,x.prize from results x join events e on e.id=x.event_id join registrations r on r.reg_id=x.reg_id where x.published=1").fetchall()
            body="<h1>🏆 Live Results</h1><div class=card><table><tr><th>Event</th><th>Participant</th><th>Position</th><th>Prize</th></tr>"+''.join(f"<tr><td>{h(x['en'])}</td><td>{h(x['pn'])}</td><td>{h(x['position'])}</td><td>{h(x['prize'])}</td></tr>" for x in rr)+"</table></div>"
        elif p=="/announcements":
            aa=c.execute("select * from announcements order by id desc").fetchall()
            body="<h1>📢 Announcements</h1>"+''.join(f"<div class=card><h2>{h(a['title'])}</h2><p>{h(a['body'])}</p><small>{h(a['created'])}</small></div>" for a in aa)
        elif p=="/calendar":
            e=c.execute("select * from events where id=?",(q(qs,"event"),)).fetchone()
            if not e:return self.out(404,data=b"Event not found")
            google="https://calendar.google.com/calendar/render?action=TEMPLATE&text="+urllib.parse.quote(e["name"])+"&dates="+e["date"].replace("-","")+"T"+e["time"].replace(":","")+"00&location="+urllib.parse.quote(e["venue"])
            body=f"<div class=card><h1>Add Event to Calendar</h1><a class=btn href='{h(google)}' target=_blank>Google Calendar</a><p class=muted>For Outlook, use the event details and your calendar's Add Event option.</p></div>"
        elif p=="/admin/login":
            body="<h1>Admin Login</h1><div class=card><form method=post action=/admin/login><input name=username placeholder=Username required><input name=password type=password placeholder=Password required><button class=btn>Login</button></form></div>"
        elif p=="/admin":
            body=f"<h1>Admin Dashboard</h1><div class=grid><div class=card><div class=stats>{c.execute('select count(*) from events').fetchone()[0]}</div>Events</div><div class=card><div class=stats>{c.execute('select count(*) from students').fetchone()[0]}</div>Students</div><div class=card><div class=stats>{c.execute('select count(*) from registrations').fetchone()[0]}</div>Registrations</div><div class=card><div class=stats>{c.execute('select count(*) from attendance').fetchone()[0]}</div>Attendance</div></div><p><a class=btn href=/admin/events>Manage Events</a> <a class=btn href=/admin/participants>Participants</a> <a class=btn href=/admin/attendance>Attendance</a> <a class=btn href=/admin/results>Results & Certificates</a> <a class=btn href=/admin/announcements>Announcements</a> <a class=btn alt href=/admin/export>Export CSV</a></p><div class=card><h3>Email setup</h3><p>Set SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD and SMTP_FROM before starting the app to send real registration emails.</p></div>"
        elif p=="/admin/events":
            es=c.execute("select * from events order by date").fetchall()
            body="<h1>Manage Events</h1><a class=btn href=/admin/event/edit>Add Event</a><div class=card><table><tr><th>Event</th><th>Date</th><th>Time</th><th>Venue</th><th>Status</th><th>Actions</th></tr>"+''.join(f"<tr><td>{h(e['name'])}</td><td>{h(e['date'])}</td><td>{h(e['time'])}</td><td>{h(e['venue'])}</td><td>{h(e['status'])}</td><td><a href=/admin/event/edit?id={e['id']}>Edit</a> · <a href=/event?id={e['id']}>View</a></td></tr>" for e in es)+"</table></div>"
        elif p=="/admin/event/edit":
            e=c.execute("select * from events where id=?",(q(qs,"id"),)).fetchone()
            fs=["code","name","date","time","venue","description","rules","eligibility","mode","max_team","deadline","coordinator","contact","prize","status","payment_mode","payment_qr"]
            body="<h1>"+("Edit Event" if e else "Add Event")+"</h1><div class=card><form method=post action=/admin/event/save><input type=hidden name=id value='"+h(e['id'] if e else "")+"'>"+''.join(f"<label>{x.replace('_',' ').title()}</label><input name={x} value='{h(e[x] if e else '')}'>" for x in fs)+"<p>For Payment QR, paste a <b>data:image/...;base64,...</b> image string. This avoids extra software and keeps the package offline.</p><button class=btn>Save Event</button></form></div>"
        elif p=="/admin/participants":
            rs=c.execute("select r.*,e.name en from registrations r join events e on e.id=r.event_id order by r.id desc").fetchall()
            body="<h1>Participants (admin only)</h1><div class=card><table><tr><th>Registration</th><th>Student</th><th>Email</th><th>Event</th><th>Payment</th><th>Status</th></tr>"+''.join(f"<tr><td>{h(r['reg_id'])}</td><td>{h(r['name'])}</td><td>{h(r['email'])}</td><td>{h(r['en'])}</td><td>{h(r['payment_method'])}/{h(r['payment_status'])}</td><td>{h(r['status'])}</td></tr>" for r in rs)+"</table></div>"
        elif p=="/admin/attendance":
            body="<h1>Attendance</h1><div class=card><form method=post action=/admin/attendance><input name=reg_id placeholder='COMPESA-2026-XXXXX' required><button class=btn>Check In</button></form></div>"
        elif p=="/admin/results":
            es=c.execute("select * from events order by date").fetchall()
            body="<h1>Results & Certificates</h1>"
            for e in es:
                body+=f"<div class=card><h2>{h(e['name'])}</h2><form method=post action=/admin/results><input type=hidden name=event_id value={e['id']}><input name=reg_id placeholder='Registration ID' required><input name=position placeholder='Winner / Runner-up / Third' required><input name=prize placeholder='Prize'><label><input type=checkbox name=published> Publish result & certificate</label><button class=btn>Save Result</button></form></div>"
            body+="<p>Published certificates are available privately in the student's panel. Public verification uses the certificate ID.</p>"
        elif p=="/admin/announcements":
            body="<h1>Announcements</h1><div class=card><form method=post action=/admin/announcements><input name=title placeholder=Title required><textarea name=body placeholder=Announcement required></textarea><button class=btn>Publish</button></form></div>"
        elif p=="/admin/export":
            rs=c.execute("select r.reg_id,e.name event,r.name,r.student_id,r.email,r.mobile,r.branch,r.year,r.division,r.college,r.payment_method,r.payment_status,r.status,r.created from registrations r join events e on e.id=r.event_id order by r.id").fetchall()
            out=",".join(rs[0].keys())+"\\n" if rs else "reg_id,event,name\\n"
            for r in rs: out+=",".join('"'+str(x or "").replace('"','""')+'"' for x in r)+"\\n"
            return self.out(200,"text/csv",out.encode())
        else:return self.out(404,data=b"Not found")
        c.close(); self.out(200,data=layout(title if 'title' in locals() else p,body,s).encode())

    def POST(self):
        p=urllib.parse.urlparse(self.path).path; d=self.read(); c=conn(); s=student_from(self)
        if p=="/student/signup":
            if c.execute("select 1 from students where email=? or student_id=?",(q(d,"email"),q(d,"student_id"))).fetchone():
                return self.out(409,data=layout("Signup","<h1>Account already exists</h1><p>Email or student ID is already registered.</p>").encode())
            uid="STU-"+secrets.token_hex(4).upper()
            c.execute("insert into students(student_uid,name,student_id,email,password,mobile,branch,year,division,gender,college,created) values(?,?,?,?,?,?,?,?,?,?,?,?)",(uid,q(d,"name"),q(d,"student_id"),q(d,"email"),sha(q(d,"password")),q(d,"mobile"),q(d,"branch"),q(d,"year"),q(d,"division"),q(d,"gender"),q(d,"college"),now()))
            c.execute("insert into notifications(student_uid,title,body,created) values(?,?,?,?)",(uid,"Welcome to COMPESA","Your student account was created successfully. Your unique ID is "+uid,now())); c.commit()
            ok,msg=send_mail(q(d,"email"),"COMPESA Student Account Created",f"Welcome {q(d,'name')}! Your COMPESA student ID is {uid}.")
            return self.redir("/student",f"student_session={uid}; Path=/; HttpOnly; SameSite=Lax")
        if p=="/student/login":
            srow=c.execute("select * from students where email=? and password=?",(q(d,"email"),sha(q(d,"password")))).fetchone()
            if not srow:return self.out(401,data=layout("Login","<h1>Login failed</h1><a href=/student/login>Try again</a>").encode())
            return self.redir("/student",f"student_session={srow['student_uid']}; Path=/; HttpOnly; SameSite=Lax")
        if p=="/student/profile":
            if not s:return self.redir("/student/login")
            c.execute("update students set name=?,mobile=?,branch=?,year=?,division=?,college=? where student_uid=?",(q(d,"name"),q(d,"mobile"),q(d,"branch"),q(d,"year"),q(d,"division"),q(d,"college"),s["student_uid"])); c.commit(); return self.redir("/student")
        if p=="/student/bookmark":
            if not s:return self.redir("/student/login")
            eid=q(d,"event_id")
            if c.execute("select 1 from bookmarks where student_uid=? and event_id=?",(s["student_uid"],eid)).fetchone(): c.execute("delete from bookmarks where student_uid=? and event_id=?",(s["student_uid"],eid))
            else:c.execute("insert or ignore into bookmarks(student_uid,event_id) values(?,?)",(s["student_uid"],eid))
            c.commit(); return self.redir("/event?id="+eid)
        if p=="/register":
            if not s:return self.redir("/student/login")
            eid=q(d,"event"); e=c.execute("select * from events where id=?",(eid,)).fetchone()
            if not e:return self.out(400,data=b"Invalid event")
            if c.execute("select 1 from registrations where event_id=? and student_uid=?",(eid,s["student_uid"])).fetchone():
                return self.out(409,data=layout("Already Registered","<h1>Already registered</h1><a href=/student>Open My Panel</a>",s).encode())
            rid=f"COMPESA-2026-{secrets.randbelow(90000)+10000}"
            while c.execute("select 1 from registrations where reg_id=?",(rid,)).fetchone(): rid=f"COMPESA-2026-{secrets.randbelow(90000)+10000}"
            c.execute("""insert into registrations(reg_id,event_id,student_uid,name,student_id,email,mobile,branch,year,division,gender,college,team_name,team_members,payment_method,payment_ref,created) values(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",(rid,eid,s["student_uid"],s["name"],s["student_id"],s["email"],s["mobile"],s["branch"],s["year"],s["division"],s["gender"],s["college"],q(d,"team_name"),q(d,"team_members"),q(d,"payment_method"),q(d,"payment_ref"),now()))
            c.execute("insert into notifications(student_uid,title,body,created) values(?,?,?,?)",(s["student_uid"],"Registration Successful",f"Your registration for {e['name']} is successful. Registration ID: {rid}.",now())); c.commit()
            mail=f"""Hello {s['name']},

Your COMPESA event registration is successful.

Event: {e['name']}
Date: {e['date']} {e['time']}
Venue: {e['venue']}
Registration ID: {rid}
Student ID: {s['student_id']}
Payment: {q(d,'payment_method')} / {q(d,'payment_ref')}

Your private digital event pass is available after login in My Panel.
"""
            sent,msg=send_mail(s["email"],f"COMPESA Registration — {e['name']}",mail)
            body=f"<div class=card center><h1>Registration Successful ✅</h1><h2>{rid}</h2><p>{h(e['name'])}</p><p>{'Confirmation email sent.' if sent else 'Registration saved. Real email sending is pending SMTP configuration in this offline package.'}</p><a class=btn href=/pass?id={rid}>Open Event Pass</a></div>"
            return self.out(200,data=layout("Success",body,s).encode())
        if p=="/admin/login":
            u=q(d,"username"); pw=sha(q(d,"password"))
            if c.execute("select 1 from admins where username=? and password=?",(u,pw)).fetchone(): return self.redir("/admin")
            return self.out(401,data=layout("Login Failed","<h1>Login failed</h1>").encode())
        if p=="/admin/event/save":
            fs=["code","name","date","time","venue","description","rules","eligibility","mode","max_team","deadline","coordinator","contact","prize","status","payment_mode","payment_qr"]; vals=[q(d,x) for x in fs]
            if q(d,"id"): c.execute("update events set "+",".join(x+"=?" for x in fs)+" where id=?",vals+[q(d,"id")])
            else:c.execute("insert into events("+",".join(fs)+",created) values("+",".join("?" for _ in fs)+",?)",vals+[now()])
            c.commit(); return self.redir("/admin/events")
        if p=="/admin/attendance":
            rid=q(d,"reg_id"); r=c.execute("select * from registrations where reg_id=?",(rid,)).fetchone()
            if not r:return self.out(404,data=b"Participant not found")
            if not c.execute("select 1 from attendance where reg_id=?",(rid,)).fetchone():c.execute("insert into attendance(reg_id,checked_in) values(?,?)",(rid,now())); c.commit()
            return self.redir("/admin/attendance")
        if p=="/admin/results":
            pub=1 if "published" in d else 0; eid=q(d,"event_id"); rid=q(d,"reg_id")
            c.execute("insert into results(event_id,reg_id,position,prize,published) values(?,?,?,?,?)",(eid,rid,q(d,"position"),q(d,"prize"),pub))
            r=c.execute("select * from registrations where reg_id=?",(rid,)).fetchone()
            if r and pub:c.execute("insert into notifications(student_uid,title,body,created) values(?,?,?,?)",(r["student_uid"],"Result Published",f"Your result is published. Position: {q(d,'position')}. Your certificate is available in My Panel.",now()))
            c.commit(); return self.redir("/admin/results")
        if p=="/admin/announcements":
            c.execute("insert into announcements(title,body,created) values(?,?,?)",(q(d,"title"),q(d,"body"),now()))
            for x in c.execute("select student_uid from students").fetchall(): c.execute("insert into notifications(student_uid,title,body,created) values(?,?,?,?)",(x["student_uid"],q(d,"title"),q(d,"body"),now()))
            c.commit(); return self.redir("/announcements")
        return self.out(404,data=b"Not found")
    def do_GET(self): self.GET()
    def do_POST(self): self.POST()
    def log_message(self,*a): pass

if __name__=="__main__":
    print("COMPESA 3.0 running at http://localhost:"+str(PORT))
    with socketserver.ThreadingTCPServer(("127.0.0.1",PORT),App) as server: server.serve_forever()
