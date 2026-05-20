"""
=======================================================
  DASHBOARD WEB — Tableau de bord tri des déchets
  Commande : python3 /home/azza/dashboard.py
  Accès     : http://IP_DU_PI:5000
=======================================================
"""

from flask import Flask, jsonify, render_template_string, request, redirect, session
import sqlite3

app = Flask(__name__)
app.secret_key = "ecosort_secret_key_change_me"

DB = "/home/azza/tri_dechets.db"


# =========================
#  LOGIN PAGE
# =========================
LOGIN_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>ECOSORT Login</title>
    <style>
        body{
            margin:0;
            height:100vh;
            display:flex;
            justify-content:center;
            align-items:center;
            background:#0a0f1e;
            font-family:Arial;
            color:white;
        }

        .box{
            padding:30px;
            background:#121a2a;
            border-radius:15px;
            text-align:center;
            box-shadow:0 0 20px rgba(0,255,136,0.2);
        }

        input{
            width:200px;
            padding:10px;
            margin:10px;
            border:none;
            border-radius:8px;
        }

        button{
            padding:10px 20px;
            background:#00ff88;
            border:none;
            cursor:pointer;
            border-radius:8px;
            font-weight:bold;
        }
    </style>
</head>
<body>

<div class="box">
    <h2>♻ ECOSORT ADMIN</h2>
    <form method="POST">
        <input name="user" placeholder="Username"><br>
        <input name="pass" type="password" placeholder="Password"><br>
        <button type="submit">Login</button>
    </form>
</div>

</body>
</html>
"""


# =========================
#  DASHBOARD MODERNE
# =========================
DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<title>ECOSORT Dashboard</title>

<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&display=swap" rel="stylesheet">

<style>
body{
    margin:0;
    background:radial-gradient(circle at top,#0f1a33,#070b14);
    color:white;
    font-family:Inter;
}

header{
    text-align:center;
    padding:20px;
}

header h1{
    color:#00ff88;
    font-size:32px;
}

.live{
    width:70%;
    margin:auto;
    padding:25px;
    margin-top:20px;
    background:rgba(255,255,255,0.06);
    border-radius:20px;
    text-align:center;
    transition:0.4s;
}

.live h2{
    font-size:36px;
}

.grid{
    display:grid;
    grid-template-columns:repeat(3,1fr);
    gap:15px;
    width:70%;
    margin:20px auto;
}

.card{
    background:rgba(255,255,255,0.06);
    padding:15px;
    border-radius:15px;
    text-align:center;
}

.history{
    width:70%;
    margin:auto;
    margin-top:20px;
    background:rgba(255,255,255,0.06);
    padding:15px;
    border-radius:15px;
}

.item{
    display:flex;
    justify-content:space-between;
    padding:6px;
    border-bottom:1px solid rgba(255,255,255,0.1);
}

.cardboard{color:#ff4d4d;}
.glass{color:#00ff88;}
.metal{color:#c8d6e5;}
.paper{color:#ffd700;}
.plastic{color:#1e90ff;}
.trash{color:#b07cff;}

.logout{
    position:absolute;
    top:15px;
    right:15px;
    background:red;
    color:white;
    padding:8px 12px;
    border-radius:8px;
    text-decoration:none;
}
</style>
</head>

<body>

<a href="/logout" class="logout">Logout</a>

<header>
    <h1>♻ ECOSORT</h1>
    <p>Smart Waste AI System</p>
</header>

<div class="live" id="liveBox">
    <h2 id="live">Waiting...</h2>
    <p id="conf">Confidence: -</p>
</div>

<div class="grid">
    <div class="card">
        <h3>Category</h3>
        <p id="cat">-</p>
    </div>
    <div class="card">
        <h3>Confidence</h3>
        <p id="conf2">-</p>
    </div>
    <div class="card">
        <h3>Status</h3>
        <p style="color:#00ff88">ACTIVE</p>
    </div>
</div>

<div class="history">
    <h3> History</h3>
    <div id="history"></div>
</div>

<script>

const colors={
 cardboard:"#ff4d4d",
 glass:"#00ff88",
 metal:"#c8d6e5",
 paper:"#ffd700",
 plastic:"#1e90ff",
 trash:"#b07cff"
};

function setColor(c){
    document.getElementById("liveBox").style.border="2px solid "+(colors[c]||"#333");
    document.getElementById("live").style.color=colors[c]||"#fff";
}

async function update(){

    let r=await fetch('/latest');
    let d=await r.json();

    if(d.categorie){
        document.getElementById("live").innerText=d.categorie.toUpperCase();
        document.getElementById("cat").innerText=d.categorie;
        document.getElementById("conf").innerText="Confidence: "+d.confiance.toFixed(1)+"%";
        document.getElementById("conf2").innerText=d.confiance.toFixed(1)+"%";
        setColor(d.categorie);
    }

    let h=await fetch('/history');
    let data=await h.json();

    document.getElementById("history").innerHTML =
    data.map(x=>`
        <div class="item">
            <span class="${x.categorie}">${x.categorie}</span>
            <span>${x.confiance.toFixed(1)}%</span>
        </div>
    `).join('');
}

setInterval(update,1500);
update();

</script>

</body>
</html>
"""


# =========================
#  LOGIN LOGIC
# =========================
@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user = request.form["user"]
        pwd = request.form["pass"]

        if user == "admin" and pwd == "1234":
            session["admin"] = True
            return redirect("/dashboard")

    return render_template_string(LOGIN_HTML)


# =========================
# DASHBOARD (PROTECTED)
# =========================
@app.route("/dashboard")
def dashboard():
    if not session.get("admin"):
        return redirect("/")
    return render_template_string(DASHBOARD_HTML)


# =========================
#  LOGOUT
# =========================
@app.route("/logout")
def logout():
    session.pop("admin", None)
    return redirect("/")


# =========================
#  LATEST
# =========================
@app.route("/latest")
def latest():
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute("SELECT * FROM tris ORDER BY id DESC LIMIT 1")
    row = cur.fetchone()
    conn.close()

    if row:
        return jsonify({
            "timestamp": row[1],
            "categorie": row[2],
            "confiance": row[3]
        })
    return jsonify({})


# =========================
#  HISTORY
# =========================
@app.route("/history")
def history():
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute("SELECT * FROM tris ORDER BY id DESC LIMIT 20")
    rows = cur.fetchall()
    conn.close()

    return jsonify([
        {"timestamp":r[1], "categorie":r[2], "confiance":r[3]}
        for r in rows
    ])


# =========================
#  RUN
# =========================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)