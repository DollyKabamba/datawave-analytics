"""
DataWave Analytics — Flask Edition
Reproduction fidèle du projet Django ENSEA 2025-2026
Équipe : KABAMBA LUBANZA Dolly (Chef de projet)
"""
import os
import io
import sqlite3
import hashlib
import smtplib
from email.mime.text import MIMEText
from functools import wraps
from flask import (Flask, render_template, request, redirect, url_for,
                   session, g, flash, send_file)
import pandas as pd

app = Flask(__name__)
app.secret_key = 'datawave_analytics_ensea_secret_2026_xK9!mP#'
app.jinja_env.globals.update(enumerate=enumerate, min=min, max=max,
                              round=round, int=int, abs=abs, len=len)
app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(__file__), 'static', 'uploads')
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024

# Email config (settings.py Django)
app.config['MAIL_SERVER']   = 'smtp.gmail.com'
app.config['MAIL_PORT']     = 587
app.config['MAIL_USERNAME'] = 'kabambadolly5@gmail.com'
app.config['MAIL_PASSWORD'] = 'pulr ijwf kbnr jvwn'
app.config['MAIL_TO']       = 'kabambadolly5@gmail.com'

DATABASE  = os.path.join(os.path.dirname(__file__), 'datawave.db')
DATA_FILE = os.path.join(os.path.dirname(__file__), 'data', 'data.csv')

# ─── RÔLES — accès simplifié pour l'enseignant ───────────────────────────────
# Tous les rôles voient toutes les pages — c'est une illustration
# Les badges de rôle distinguent les niveaux
ROLE_CONFIG = {
    'admin':   {'label': 'Administrateur', 'color': 'red',    'access': ['all']},
    'manager': {'label': 'Gestionnaire',   'color': 'amber',  'access': ['all']},
    'analyst': {'label': 'Analyste',       'color': 'blue',   'access': ['all']},
    'viewer':  {'label': 'Observateur',    'color': 'gray',   'access': ['dashboard','demographic','content']},
}

# ─────────────────────────────────────────────────────────────────────────────
# BASE DE DONNÉES
# ─────────────────────────────────────────────────────────────────────────────
def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
    return g.db

@app.teardown_appcontext
def close_db(e=None):
    db = g.pop('db', None)
    if db: db.close()

def hash_pw(p): return hashlib.sha256(p.encode()).hexdigest()

def init_db():
    db = sqlite3.connect(DATABASE)
    db.executescript('''
        CREATE TABLE IF NOT EXISTS users (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            username   TEXT UNIQUE NOT NULL,
            password   TEXT NOT NULL,
            first_name TEXT DEFAULT '',
            last_name  TEXT DEFAULT '',
            email      TEXT DEFAULT '',
            gender     TEXT DEFAULT '',
            role       TEXT DEFAULT 'viewer',
            photo      TEXT DEFAULT 'default.png',
            is_active  INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS contacts (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            name       TEXT, email TEXT, subject TEXT, message TEXT,
            is_read    INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS search_history (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id    INTEGER,
            query      TEXT,
            results    INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    ''')
    # Comptes officiels — mots de passe identiques au README Django
    accounts = [
        ('admin',   hash_pw('AS3admin2026'), 'KABAMBA LUBANZA', 'Dolly',  'kabambadolly5@gmail.com', 'M', 'admin'),
        ('manager', hash_pw('Manager@2026'), 'Membre',  '2',   'membre2@ensea.edu.ci',  'M', 'manager'),
        ('analyst', hash_pw('Analyst@2026'), 'Membre',  '3',   'membre3@ensea.edu.ci',  'F', 'analyst'),
        ('viewer',  hash_pw('Viewer@2026'),  'Membre',  '4',   'membre4@ensea.edu.ci',  'M', 'viewer'),
    ]
    for u in accounts:
        if not db.execute("SELECT id FROM users WHERE username=?", (u[0],)).fetchone():
            db.execute('INSERT INTO users (username,password,first_name,last_name,email,gender,role) VALUES (?,?,?,?,?,?,?)', u)
    db.commit()
    db.close()

# ─────────────────────────────────────────────────────────────────────────────
# AUTH
# ─────────────────────────────────────────────────────────────────────────────
def login_required(f):
    @wraps(f)
    def dec(*a, **kw):
        if 'user_id' not in session:
            flash('Veuillez vous connecter pour accéder à cette page.', 'warning')
            return redirect(url_for('login'))
        return f(*a, **kw)
    return dec

def role_required(*roles):
    """Accès restreint aux rôles admin/manager/analyst — viewer redirigé avec message."""
    def deco(f):
        @wraps(f)
        def dec(*a, **kw):
            if 'user_id' not in session:
                return redirect(url_for('login'))
            if session.get('role') == 'viewer':
                flash("⚠️ Module réservé aux rôles Analyste, Gestionnaire et Admin. Connectez-vous avec un compte plus élevé.", 'warning')
                return redirect(url_for('dashboard'))
            return f(*a, **kw)
        return dec
    return deco

# ─────────────────────────────────────────────────────────────────────────────
# DONNÉES
# ─────────────────────────────────────────────────────────────────────────────
_df = None
def get_data():
    global _df
    if _df is None:
        try:
            _df = pd.read_csv(DATA_FILE)
        except Exception as e:
            print(f"Data error: {e}")
            _df = pd.DataFrame()
    return _df

# ─────────────────────────────────────────────────────────────────────────────
# ROUTES PUBLIQUES
# ─────────────────────────────────────────────────────────────────────────────
@app.route('/')
def home():
    # If already logged in, go to dashboard
    if session.get('user_id'):
        return redirect(url_for('dashboard'))
    df = get_data()
    stats = {}
    if not df.empty:
        stats = {
            'total': len(df),
            'countries': df['country'].nunique(),
            'avg_followers': int(df['followers_count'].mean()),
            'premium_pct': round((df['subscription_status'] != 'Free').mean() * 100, 1),
        }
    return render_template('home.html', stats=stats)

@app.route('/contact', methods=['GET','POST'])
def contact():
    if request.method == 'POST':
        name    = request.form.get('name','').strip()
        email   = request.form.get('email','').strip()
        subject = request.form.get('subject','').strip()
        message = request.form.get('message','').strip()
        if not all([name, email, subject, message]):
            flash("Tous les champs sont obligatoires.", 'danger')
            return redirect(url_for('contact'))
        db = get_db()
        db.execute('INSERT INTO contacts (name,email,subject,message) VALUES (?,?,?,?)',
                   (name, email, subject, message))
        db.commit()
        # Tentative envoi email (settings.py Django)
        try:
            msg = MIMEText(f"De: {name} <{email}>\n\n{message}")
            msg['Subject'] = f"[DataWave] {subject}"
            msg['From'] = app.config['MAIL_USERNAME']
            msg['To']   = app.config['MAIL_TO']
            with smtplib.SMTP(app.config['MAIL_SERVER'], app.config['MAIL_PORT']) as s:
                s.starttls()
                s.login(app.config['MAIL_USERNAME'], app.config['MAIL_PASSWORD'])
                s.send_message(msg)
        except Exception:
            pass
        flash('✅ Message envoyé avec succès ! Nous vous répondrons rapidement.', 'success')
        return redirect(url_for('contact'))
    return render_template('contact.html')

@app.route('/login', methods=['GET','POST'])
def login():
    if 'user_id' in session: return redirect(url_for('dashboard'))
    error = None
    if request.method == 'POST':
        username = request.form.get('username','').strip()
        password = request.form.get('password','').strip()
        # Connexion rapide par rôle (bouton 1-clic enseignant)
        quick = request.form.get('quick_role','')
        if quick:
            quick_map = {
                'admin':   ('admin',   'AS3admin2026'),
                'manager': ('manager', 'Manager@2026'),
                'analyst': ('analyst', 'Analyst@2026'),
                'viewer':  ('viewer',  'Viewer@2026'),
            }
            if quick in quick_map:
                username, password = quick_map[quick]
        user = get_db().execute(
            'SELECT * FROM users WHERE username=? AND password=? AND is_active=1',
            (username, hash_pw(password))
        ).fetchone()
        if user:
            session.update({
                'user_id': user['id'], 'username': user['username'],
                'role': user['role'], 'first_name': user['first_name'],
                'last_name': user['last_name'], 'photo': user['photo']
            })
            role_labels = {'admin':'Administrateur','manager':'Gestionnaire','analyst':'Analyste','viewer':'Observateur'}
            flash(f"Bienvenue {user['first_name']} {user['last_name']} — Connecté en tant que {role_labels.get(user['role'], user['role'])} !", 'success')
            return redirect(url_for('dashboard'))
        error = "Identifiant ou mot de passe incorrect."
    return render_template('login.html', error=error)

@app.route('/register', methods=['GET','POST'])
def register():
    if 'user_id' in session: return redirect(url_for('dashboard'))
    if request.method == 'POST':
        username   = request.form.get('username','').strip()
        first_name = request.form.get('first_name','').strip()
        last_name  = request.form.get('last_name','').strip()
        email      = request.form.get('email','').strip()
        password   = request.form.get('password','').strip()
        password2  = request.form.get('password2','').strip()
        if not all([username, first_name, last_name, email, password]):
            flash("Tous les champs sont obligatoires.", 'danger')
            return redirect(url_for('register'))
        if password != password2:
            flash("Les mots de passe ne correspondent pas.", 'danger')
            return redirect(url_for('register'))
        if len(password) < 8:
            flash("Le mot de passe doit contenir au moins 8 caractères.", 'danger')
            return redirect(url_for('register'))
        try:
            get_db().execute(
                'INSERT INTO users (username,password,first_name,last_name,email,role) VALUES (?,?,?,?,?,?)',
                (username, hash_pw(password), first_name, last_name, email, 'viewer')
            )
            get_db().commit()
            flash(f"Compte créé avec succès ! Vous pouvez vous connecter.", 'success')
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash("Ce nom d'utilisateur est déjà pris.", 'danger')
            return redirect(url_for('register'))
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Vous avez été déconnecté.', 'info')
    return redirect(url_for('home'))

# ─────────────────────────────────────────────────────────────────────────────
# DASHBOARD — analytics:dashboard
# ─────────────────────────────────────────────────────────────────────────────
@app.route('/analytics/dashboard')
@app.route('/dashboard')
@login_required
def dashboard():
    df = get_data()
    kpi, charts = {}, {}
    if not df.empty:
        kpi = {
            'total':         len(df),
            'avg_followers': int(df['followers_count'].mean()),
            'avg_posts':     round(df['posts_created_per_week'].mean(), 1),
            'premium_count': int((df['subscription_status'] != 'Free').sum()),
            'premium_pct':   round((df['subscription_status'] != 'Free').mean() * 100, 1),
            'max_followers': int(df['followers_count'].max()),
            'countries':     df['country'].nunique(),
            'avg_age':       round(df['age'].mean(), 1),
        }
        g_val = df['gender'].value_counts()
        charts['gender_labels'] = g_val.index.tolist()
        charts['gender_counts'] = g_val.values.tolist()

        top_c = df['country'].value_counts().head(10)
        charts['country_labels'] = top_c.index.tolist()
        charts['country_counts'] = top_c.values.tolist()

        sub = df['subscription_status'].value_counts()
        charts['sub_labels'] = sub.index.tolist()
        charts['sub_counts'] = sub.values.tolist()

        emp = df.groupby('employment_status')['posts_created_per_week'].mean().sort_values(ascending=False)
        charts['emp_labels'] = emp.index.tolist()
        charts['emp_values'] = emp.round(2).values.tolist()

        fc = df.groupby('country')['followers_count'].mean().nlargest(8).round(0)
        charts['fc_labels'] = fc.index.tolist()
        charts['fc_values'] = [int(v) for v in fc.values]

    return render_template('dashboard.html', kpi=kpi, charts=charts)

# ─────────────────────────────────────────────────────────────────────────────
# MODULE 1 – DÉMOGRAPHIQUE
# ─────────────────────────────────────────────────────────────────────────────
@app.route('/analytics/demographic')
@login_required
def analytics_demographic():
    df = get_data()
    s = {}
    if not df.empty:
        bins   = [12,18,25,35,45,55,65]
        labels = ['13–17','18–24','25–34','35–44','45–54','55–65']
        df2 = df.copy()
        df2['age_range'] = pd.cut(df2['age'], bins=bins, labels=labels, right=True)
        ag = df2['age_range'].value_counts().reindex(labels).fillna(0)
        s['age_labels'] = labels; s['age_counts'] = [int(v) for v in ag.values]

        gen = df['gender'].value_counts()
        s['gen_labels'] = gen.index.tolist(); s['gen_counts'] = gen.values.tolist()

        top_c = df['country'].value_counts().head(10)
        s['country_labels'] = top_c.index.tolist(); s['country_counts'] = top_c.values.tolist()

        emp = df['employment_status'].value_counts()
        s['emp_labels'] = emp.index.tolist(); s['emp_counts'] = emp.values.tolist()

        rel = df['relationship_status'].value_counts()
        s['rel_labels'] = rel.index.tolist(); s['rel_counts'] = rel.values.tolist()

        order = ['Low','Lower-middle','Middle','Upper-middle','High']
        inc = df['income_level'].value_counts().reindex(order).fillna(0)
        s['inc_labels'] = order; s['inc_counts'] = [int(v) for v in inc.values]

        ch = df['has_children'].value_counts()
        s['ch_labels'] = ch.index.tolist(); s['ch_counts'] = ch.values.tolist()

        s['avg_age']    = round(df['age'].mean(), 1)
        s['avg_hours']  = round(df['weekly_work_hours'].mean(), 1)
        s['avg_events'] = round(df['social_events_per_month'].mean(), 1)
        s['avg_books']  = round(df['books_read_per_year'].mean(), 1)
    return render_template('analytics_demographic.html', s=s)

# ─────────────────────────────────────────────────────────────────────────────
# MODULE 2 – CONTENU
# ─────────────────────────────────────────────────────────────────────────────
@app.route('/analytics/content')
@login_required
def analytics_content():
    df = get_data()
    s = {}
    if not df.empty:
        ct = df['content_type_preference'].value_counts()
        s['ct_labels'] = ct.index.tolist(); s['ct_counts'] = ct.values.tolist()

        theme = df['preferred_content_theme'].value_counts()
        s['theme_labels'] = theme.index.tolist(); s['theme_counts'] = theme.values.tolist()

        priv = df['privacy_setting_level'].value_counts()
        s['priv_labels'] = priv.index.tolist(); s['priv_counts'] = priv.values.tolist()

        pct = df.groupby('content_type_preference')['posts_created_per_week'].mean().sort_values(ascending=False)
        s['pct_labels'] = pct.index.tolist(); s['pct_values'] = pct.round(2).values.tolist()

        pth = df.groupby('preferred_content_theme')['posts_created_per_week'].mean().sort_values(ascending=False)
        s['pth_labels'] = pth.index.tolist(); s['pth_values'] = pth.round(2).values.tolist()

        fth = df.groupby('preferred_content_theme')['followers_count'].mean().sort_values(ascending=False)
        s['fth_labels'] = fth.index.tolist(); s['fth_values'] = [int(v) for v in fth.values]

        hm = df.pivot_table(values='posts_created_per_week', index='gender',
                             columns='content_type_preference', aggfunc='mean').round(2)
        s['hm_rows'] = hm.index.tolist(); s['hm_cols'] = hm.columns.tolist()
        s['hm_data'] = [[round(float(v),2) if not pd.isna(v) else 0 for v in row] for row in hm.values]

        s['avg_posts']   = round(df['posts_created_per_week'].mean(), 1)
        s['max_posts']   = int(df['posts_created_per_week'].max())
        s['public_pct']  = round((df['privacy_setting_level']=='Public').mean()*100, 1)
        s['private_pct'] = round((df['privacy_setting_level']=='Private').mean()*100, 1)
    return render_template('analytics_content.html', s=s)

# ─────────────────────────────────────────────────────────────────────────────
# MODULE 3 – COMPORTEMENTAL
# ─────────────────────────────────────────────────────────────────────────────
@app.route('/analytics/behavioral')
@login_required
def analytics_behavioral():
    df = get_data()
    s = {}
    if not df.empty:
        fb = [0,500,1000,2500,5000,10000,200000]
        fl = ['<500','500–1K','1K–2.5K','2.5K–5K','5K–10K','>10K']
        df2 = df.copy()
        df2['foll_range'] = pd.cut(df2['followers_count'], bins=fb, labels=fl)
        fd = df2['foll_range'].value_counts().reindex(fl).fillna(0)
        s['foll_labels'] = fl; s['foll_counts'] = [int(v) for v in fd.values]

        yf = df.groupby('account_creation_year')['followers_count'].mean().sort_index()
        s['yf_years'] = yf.index.tolist(); s['yf_values'] = [int(v) for v in yf.values]

        order = ['Low','Lower-middle','Middle','Upper-middle','High']
        fi = df.groupby('income_level')['followers_count'].mean().reindex(order).dropna()
        s['fi_labels'] = fi.index.tolist(); s['fi_values'] = [int(v) for v in fi.values]

        rs = df.groupby('relationship_status')['posts_created_per_week'].mean().sort_values(ascending=False)
        s['rs_labels'] = rs.index.tolist(); s['rs_values'] = rs.round(2).values.tolist()

        smp = df.sample(min(600, len(df)), random_state=42)
        s['sc_age']  = smp['age'].tolist()
        s['sc_foll'] = smp['followers_count'].tolist()

        smp2 = df.sample(min(500, len(df)), random_state=7)
        s['sc2_hours']  = smp2['weekly_work_hours'].tolist()
        s['sc2_events'] = smp2['social_events_per_month'].tolist()

        ch = df.groupby('has_children')['social_events_per_month'].mean()
        s['ch_labels'] = ch.index.tolist(); s['ch_values'] = ch.round(2).values.tolist()

        s['avg_foll']   = int(df['followers_count'].mean())
        s['med_foll']   = int(df['followers_count'].median())
        s['max_foll']   = int(df['followers_count'].max())
        s['avg_events'] = round(df['social_events_per_month'].mean(), 1)
    return render_template('analytics_behavioral.html', s=s)

# ─────────────────────────────────────────────────────────────────────────────
# MODULE 4 – ABONNEMENTS (admin/manager/analyst)
# ─────────────────────────────────────────────────────────────────────────────
@app.route('/analytics/subscriptions')
@role_required('admin','manager','analyst')
def analytics_subscriptions():
    df = get_data()
    s = {}
    if not df.empty:
        sub = df['subscription_status'].value_counts()
        s['sub_labels'] = sub.index.tolist(); s['sub_counts'] = sub.values.tolist()

        sp = df.groupby(['country','subscription_status']).size().unstack(fill_value=0)
        sp = sp.loc[sp.sum(axis=1).nlargest(8).index]
        s['sp_countries'] = sp.index.tolist()
        s['sp_datasets']  = [{'label': col, 'data': [int(v) for v in sp[col].values]} for col in sp.columns]

        inc_order = ['Low','Lower-middle','Middle','Upper-middle','High']
        sr = df.groupby(['income_level','subscription_status']).size().unstack(fill_value=0)
        sr = sr.reindex([x for x in inc_order if x in sr.index])
        s['sr_incomes']  = sr.index.tolist()
        s['sr_datasets'] = [{'label': col, 'data': [int(v) for v in sr[col].values]} for col in sr.columns]

        se = df.groupby(['employment_status','subscription_status']).size().unstack(fill_value=0)
        s['se_emploi']   = se.index.tolist()
        s['se_datasets'] = [{'label': col, 'data': [int(v) for v in se[col].values]} for col in se.columns]

        sf = df.groupby('subscription_status')['followers_count'].mean().sort_values(ascending=False)
        s['sf_labels'] = sf.index.tolist(); s['sf_values'] = [int(v) for v in sf.values]

        s['free_count']     = int((df['subscription_status']=='Free').sum())
        s['premium_count']  = int((df['subscription_status']=='Premium').sum())
        s['business_count'] = int((df['subscription_status']=='Business').sum())
        s['free_pct']       = round(s['free_count']/len(df)*100, 1)
        s['premium_pct']    = round(s['premium_count']/len(df)*100, 1)
        s['business_pct']   = round(s['business_count']/len(df)*100, 1)
    return render_template('analytics_subscriptions.html', s=s)

# ─────────────────────────────────────────────────────────────────────────────
# MODULE 5 – RECHERCHE
# ─────────────────────────────────────────────────────────────────────────────
@app.route('/analytics/search')
@login_required
def analytics_search():
    df = get_data()
    results = None; query_info = {}

    country  = request.args.get('country', '')
    gender   = request.args.get('gender', '')
    sub      = request.args.get('subscription', '')
    age_min  = request.args.get('age_min', '')
    age_max  = request.args.get('age_max', '')
    foll_min = request.args.get('foll_min', '')
    content  = request.args.get('content', '')
    theme    = request.args.get('theme', '')
    privacy  = request.args.get('privacy', '')
    sort_by  = request.args.get('sort_by', 'followers_count')
    order    = request.args.get('order', 'desc')

    filters_applied = any([country, gender, sub, age_min, age_max, foll_min, content, theme, privacy])

    if not df.empty:
        fdf = df.copy()
        if country:  fdf = fdf[fdf['country'] == country]
        if gender:   fdf = fdf[fdf['gender'] == gender]
        if sub:      fdf = fdf[fdf['subscription_status'] == sub]
        if content:  fdf = fdf[fdf['content_type_preference'] == content]
        if theme:    fdf = fdf[fdf['preferred_content_theme'] == theme]
        if privacy:  fdf = fdf[fdf['privacy_setting_level'] == privacy]
        if age_min:
            try: fdf = fdf[fdf['age'] >= int(age_min)]
            except: pass
        if age_max:
            try: fdf = fdf[fdf['age'] <= int(age_max)]
            except: pass
        if foll_min:
            try: fdf = fdf[fdf['followers_count'] >= int(foll_min)]
            except: pass

        valid = ['followers_count','posts_created_per_week','age','account_creation_year']
        if sort_by not in valid: sort_by = 'followers_count'
        fdf = fdf.sort_values(sort_by, ascending=(order=='asc'))

        query_info = {
            'total': len(fdf),
            'avg_foll':  int(fdf['followers_count'].mean()) if len(fdf) > 0 else 0,
            'avg_posts': round(fdf['posts_created_per_week'].mean(), 1) if len(fdf) > 0 else 0,
        }
        results = fdf.head(100).to_dict(orient='records')

        if filters_applied and 'user_id' in session:
            qstr = '&'.join([f"{k}={v}" for k,v in request.args.items() if v])
            get_db().execute('INSERT INTO search_history (user_id, query, results) VALUES (?,?,?)',
                             (session['user_id'], qstr, len(fdf)))
            get_db().commit()

        countries = sorted(df['country'].unique())
        genders   = sorted(df['gender'].unique())
        subs      = sorted(df['subscription_status'].unique())
        contents  = sorted(df['content_type_preference'].unique())
        themes    = sorted(df['preferred_content_theme'].unique())
        privacies = sorted(df['privacy_setting_level'].unique())
    else:
        countries = genders = subs = contents = themes = privacies = []

    return render_template('analytics_search.html',
                           results=results, query_info=query_info,
                           filters_applied=filters_applied,
                           countries=countries, genders=genders, subs=subs,
                           contents=contents, themes=themes, privacies=privacies,
                           current_filters=request.args)

# ─────────────────────────────────────────────────────────────────────────────
# EXPORT EXCEL
# ─────────────────────────────────────────────────────────────────────────────
@app.route('/export/excel')
@role_required('admin','manager')
def export_excel():
    df = get_data()
    if df.empty:
        flash("Aucune donnée à exporter.", 'warning')
        return redirect(url_for('dashboard'))
    buf = io.BytesIO()
    from datetime import date
    fname = f'DataWave_Export_{date.today()}.xlsx'
    with pd.ExcelWriter(buf, engine='openpyxl') as writer:
        # Stats only (fast - no 50K rows raw sheet)
        stats = pd.DataFrame({
            'Indicateur': ['Total profils','Followers moyens','Posts/semaine moy.','Comptes payants (%)','Pays couverts','Age moyen','Max followers'],
            'Valeur': [len(df), round(df['followers_count'].mean(),0), round(df['posts_created_per_week'].mean(),2),
                       round((df['subscription_status']!='Free').mean()*100,1), df['country'].nunique(),
                       round(df['age'].mean(),1), df['followers_count'].max()]
        })
        stats.to_excel(writer, index=False, sheet_name='Statistiques')
        df.groupby('country').agg(
            Profils=('user_id','count'),
            Followers_moy=('followers_count','mean'),
            Age_moy=('age','mean'),
            Posts_moy=('posts_created_per_week','mean')
        ).round(1).reset_index().to_excel(writer, index=False, sheet_name='Par pays')
        df.groupby('subscription_status').agg(
            Count=('user_id','count'),
            Followers_moy=('followers_count','mean'),
            Age_moy=('age','mean')
        ).round(1).reset_index().to_excel(writer, index=False, sheet_name='Par abonnement')
        df.groupby('employment_status').agg(
            Count=('user_id','count'),
            Posts_moy=('posts_created_per_week','mean'),
            Followers_moy=('followers_count','mean')
        ).round(2).reset_index().to_excel(writer, index=False, sheet_name='Par emploi')
        df.groupby('preferred_content_theme').agg(
            Count=('user_id','count'),
            Posts_moy=('posts_created_per_week','mean'),
            Followers_moy=('followers_count','mean')
        ).round(2).reset_index().to_excel(writer, index=False, sheet_name='Par theme')
        # Sample only 2000 rows for dataset sheet (fast)
        df.sample(min(2000,len(df))).to_excel(writer, index=False, sheet_name='Echantillon 2000')
    buf.seek(0)
    return send_file(buf, as_attachment=True, download_name=fname,
                     mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

# ─────────────────────────────────────────────────────────────────────────────
# PROFIL
# ─────────────────────────────────────────────────────────────────────────────
@app.route('/accounts/profile', methods=['GET','POST'])
@app.route('/profile', methods=['GET','POST'])
@login_required
def profile():
    db = get_db()
    user = db.execute('SELECT * FROM users WHERE id=?', (session['user_id'],)).fetchone()
    if request.method == 'POST':
        fn = request.form.get('first_name','').strip()
        ln = request.form.get('last_name','').strip()
        em = request.form.get('email','').strip()
        ge = request.form.get('gender','')
        photo = user['photo']
        file = request.files.get('photo')
        if file and file.filename:
            ext = file.filename.rsplit('.',1)[-1].lower()
            if ext in ['jpg','jpeg','png','gif','webp']:
                fname = f"user_{session['user_id']}.{ext}"
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], fname))
                photo = fname
        db.execute('UPDATE users SET first_name=?,last_name=?,email=?,gender=?,photo=? WHERE id=?',
                   (fn, ln, em, ge, photo, session['user_id']))
        db.commit()
        session.update({'first_name': fn, 'last_name': ln, 'photo': photo})
        flash('✅ Profil mis à jour avec succès !', 'success')
        return redirect(url_for('profile'))
    return render_template('profile.html', user=user)

# ─────────────────────────────────────────────────────────────────────────────
# ADMINISTRATION
# ─────────────────────────────────────────────────────────────────────────────
@app.route('/admin-panel')
@login_required
def admin_panel():
    # Accessible à tous mais actions réservées admin
    db = get_db()
    users    = db.execute('SELECT * FROM users ORDER BY id ASC').fetchall()
    contacts = db.execute('SELECT * FROM contacts ORDER BY created_at DESC LIMIT 50').fetchall()
    searches = db.execute('''SELECT sh.*, u.username FROM search_history sh
                             LEFT JOIN users u ON sh.user_id=u.id
                             ORDER BY sh.created_at DESC LIMIT 20''').fetchall()
    df = get_data()
    dstats = {}
    if not df.empty:
        dstats['total']    = len(df)
        dstats['countries']= df['country'].nunique()
        dstats['premium']  = int((df['subscription_status'] != 'Free').sum())
        dstats['themes']   = df['preferred_content_theme'].nunique()
    return render_template('admin.html', users=users, contacts=contacts, searches=searches, dstats=dstats)

@app.route('/admin-panel/user/create', methods=['POST'])
@login_required
def admin_create_user():
    if session.get('role') != 'admin':
        flash("Action réservée à l'administrateur.", 'danger')
        return redirect(url_for('admin_panel'))
    u = (request.form.get('username'), hash_pw(request.form.get('password','')),
         request.form.get('first_name',''), request.form.get('last_name',''),
         request.form.get('email',''), request.form.get('gender','M'),
         request.form.get('role','viewer'))
    try:
        get_db().execute('INSERT INTO users (username,password,first_name,last_name,email,gender,role) VALUES (?,?,?,?,?,?,?)', u)
        get_db().commit()
        flash(f"Utilisateur « {u[0]} » créé.", 'success')
    except sqlite3.IntegrityError:
        flash("Ce nom d'utilisateur existe déjà.", 'danger')
    return redirect(url_for('admin_panel'))

@app.route('/admin-panel/user/<int:uid>/toggle', methods=['POST'])
@login_required
def admin_toggle_user(uid):
    if session.get('role') != 'admin':
        flash("Action réservée à l'administrateur.", 'danger')
        return redirect(url_for('admin_panel'))
    if uid == session['user_id']:
        flash("Impossible de désactiver votre propre compte.", 'danger')
        return redirect(url_for('admin_panel'))
    db = get_db()
    u = db.execute('SELECT is_active FROM users WHERE id=?', (uid,)).fetchone()
    new = 0 if u['is_active'] else 1
    db.execute('UPDATE users SET is_active=? WHERE id=?', (new, uid))
    db.commit()
    flash(f"Compte {'activé' if new else 'désactivé'}.", 'success')
    return redirect(url_for('admin_panel'))

@app.route('/admin-panel/user/<int:uid>/delete', methods=['POST'])
@login_required
def admin_delete_user(uid):
    if session.get('role') != 'admin':
        flash("Action réservée à l'administrateur.", 'danger')
        return redirect(url_for('admin_panel'))
    if uid == session['user_id']:
        flash("Vous ne pouvez pas supprimer votre propre compte.", 'danger')
        return redirect(url_for('admin_panel'))
    get_db().execute('DELETE FROM users WHERE id=?', (uid,))
    get_db().commit()
    flash('Utilisateur supprimé.', 'success')
    return redirect(url_for('admin_panel'))

@app.route('/admin-panel/contact/<int:cid>/read', methods=['POST'])
@login_required
def admin_mark_read(cid):
    get_db().execute('UPDATE contacts SET is_read=1 WHERE id=?', (cid,))
    get_db().commit()
    return redirect(url_for('admin_panel'))

# ─────────────────────────────────────────────────────────────────────────────
# ERREURS
# ─────────────────────────────────────────────────────────────────────────────
@app.errorhandler(404)
def custom_404(e):
    return render_template('404.html'), 404

@app.errorhandler(500)
def custom_500(e):
    return render_template('404.html', error=True), 500

if __name__ == '__main__':
    init_db()
    app.run(debug=True, host='0.0.0.0', port=5000)

# Mise à jour test