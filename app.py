from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import (
    LoginManager,
    UserMixin,
    login_user,
    logout_user,
    login_required,
    current_user
)
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

# =========================================
# APP CONFIG
# =========================================

app = Flask(__name__)

app.config['SECRET_KEY'] = 'courtbook-secret-key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# =========================================
# LOGIN MANAGER
# =========================================

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# =========================================
# DATABASE MODELS
# =========================================

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)

    username = db.Column(db.String(100), unique=True, nullable=False)

    password = db.Column(db.String(200), nullable=False)

    role = db.Column(db.String(20), default='viewer')


class Case(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    listing_date = db.Column(db.String(20))

    court_no = db.Column(db.String(20))

    bench = db.Column(db.String(200))

    serial_no = db.Column(db.String(20))

    case_no = db.Column(db.String(200))

    connected_cases = db.Column(db.Text)

    record_type = db.Column(db.String(50))

    status = db.Column(db.String(20), default='PO')

    received = db.Column(db.Boolean, default=False)

    remarks = db.Column(db.Text)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    bc_received = db.Column(db.Boolean, default=False)
    
    jr_received = db.Column(db.Boolean, default=False)

# =========================================
# LOGIN LOADER
# =========================================

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# =========================================
# INITIALIZE DATABASE
# =========================================

@app.route('/initdb')
def initdb():

    db.create_all()

    admin = User.query.filter_by(username='admin').first()

    if not admin:

        admin_user = User(
            username='admin',
            password=generate_password_hash('admin12345'),
            role='admin'
        )

        db.session.add(admin_user)
        db.session.commit()

    return 'Database Initialized Successfully'

# =========================================
# LOGIN
# =========================================

@app.route('/login', methods=['GET', 'POST'])
def login():

    if request.method == 'POST':

        username = request.form['username']
        password = request.form['password']

        user = User.query.filter_by(username=username).first()

        if user and check_password_hash(user.password, password):

            login_user(user)

            return redirect(url_for('dashboard'))

        flash('Invalid Username or Password')

    return render_template('login.html')

# =========================================
# LOGOUT
# =========================================

@app.route('/logout')
@login_required
def logout():

    logout_user()

    return redirect(url_for('login'))

# =========================================
# DASHBOARD
# =========================================

@app.route('/')
@login_required
def dashboard():

    pending_bc = Case.query.filter_by(
        status='BC',
        bc_received=False
    ).count()

    jr_cases = Case.query.filter_by(
        status='JR'
    ).count()

    latest_date = db.session.query(
        db.func.max(Case.listing_date)
    ).scalar()

    latest_cases = []

    if latest_date:

        latest_cases = db.session.query(
            Case.court_no,
            db.func.count(Case.id)
        ).filter(
            Case.listing_date == latest_date
        ).group_by(
            Case.court_no
        ).order_by(
            Case.court_no
        ).all()

    return render_template(
        'dashboard.html',
        pending_bc=pending_bc,
        jr_cases=jr_cases,
        latest_cases=latest_cases,
        latest_date=latest_date
    )

# =========================================
# ADD CASE
# =========================================

@app.route('/add-case', methods=['GET', 'POST'])
@login_required
def add_case():

    if request.method == 'POST':

        new_case = Case(

            listing_date=request.form['listing_date'],

            court_no=request.form['court_no'],

            bench=request.form['bench'],

            serial_no=request.form['serial_no'],

            case_no=request.form['case_no'],

            connected_cases=request.form['connected_cases'],

            record_type=request.form['record_type'],

            status=request.form['status'],

            remarks=request.form['remarks']
        )

        db.session.add(new_case)

        db.session.commit()

        flash('Case Added Successfully')

        return redirect(url_for('dashboard'))

    return render_template('add_case.html')

# =========================================
# UPDATE STATUS
# =========================================

@app.route('/update-status/<int:case_id>/')
@login_required
def update_status(case_id):

    case = Case.query.get_or_404(case_id)

    new_status = request.args.get('status')

    if new_status:

        case.status = new_status

        if new_status == 'BC':

            case.bc_received = False

        if new_status == 'JR':

            case.jr_received = False

        db.session.commit()

        flash('Status Updated')

    selected_date = request.args.get('date')

    if selected_date:

        return redirect(
            url_for(
                'all_cases',
                date=selected_date
            )
        )

    return redirect(url_for('all_cases'))

# =========================================
# MARK FILE RECEIVED
# =========================================

@app.route('/mark-received/<int:case_id>')
@login_required
def mark_received(case_id):

    case = Case.query.get_or_404(case_id)

    received_date = datetime.now().strftime(
        '%Y-%m-%d'
    )

    if case.remarks:

        case.remarks += (
            f' | BC Received on {received_date}'
        )

    else:

        case.remarks = (
            f'BC Received on {received_date}'
        )

    case.bc_received = True

    db.session.commit()

    flash('BC File Marked as Received')

    return redirect(url_for('pending_bc'))

# =========================================
# MARK JR RECEIVED
# =========================================

@app.route('/mark-jr-received/<int:case_id>')
@login_required
def mark_jr_received(case_id):

    case = Case.query.get_or_404(case_id)

    received_date = datetime.now().strftime(
        '%Y-%m-%d'
    )

    if case.remarks:

        case.remarks += (
            ' | JR Delivered on {}'.format(
                received_date
            )
        )

    else:

        case.remarks = (
            'JR Delivered on {}'.format(
                received_date
            )
        )

    case.jr_received = True

    db.session.commit()

    flash('JR Marked as Delivered/Received')

    return redirect(url_for('jr_cases'))
    
# =========================================
# PENDING BC PAGE
# =========================================

@app.route('/pending-bc')
@login_required
def pending_bc():

    cases = Case.query.filter_by(
    status='BC',
    bc_received=False
).all()

    return render_template(
        'pending_bc.html',
        cases=cases
    )

# =========================================
# SEARCH
# =========================================

@app.route('/search', methods=['GET'])
@login_required
def search():

    query = request.args.get('query')

    results = []

    if query:

        results = Case.query.filter(
            Case.case_no.contains(query)
        ).all()

    return render_template(
        'search.html',
        results=results
    )

# =========================================
# DELETE CASE
# =========================================

@app.route('/delete-case/<int:case_id>')
@login_required
def delete_case(case_id):

    case = Case.query.get_or_404(case_id)

    db.session.delete(case)

    db.session.commit()

    flash('Case Deleted Successfully')

    return redirect(url_for('all_cases'))

# =========================================
# EDIT CASE
# =========================================

@app.route('/edit-case/<int:case_id>', methods=['GET', 'POST'])
@login_required
def edit_case(case_id):

    case = Case.query.get_or_404(case_id)

    if request.method == 'POST':

        case.listing_date = request.form['listing_date']

        case.court_no = request.form['court_no']

        case.bench = request.form['bench']

        case.serial_no = request.form['serial_no']

        case.case_no = request.form['case_no']

        case.connected_cases = request.form['connected_cases']

        case.record_type = request.form['record_type']

        case.status = request.form['status']

        case.remarks = request.form['remarks']

        db.session.commit()

        flash('Case Updated Successfully')

        return redirect(url_for('dashboard'))

    return render_template(
        'add_case.html',
        case=case
    )

# =========================================
# LOGGED IN USER
# =========================================

@app.context_processor
def inject_user():
    return dict(current_user=current_user)

# =========================================
# IMPORT CAUSE LIST
# =========================================

import re

@app.route('/import-cause-list', methods=['GET', 'POST'])
@login_required
def import_cause_list():

    if request.method == 'POST':

        raw_text = request.form['raw_text']

        current_court = ''
        current_bench = ''
        current_date = ''

        last_case = None

        lines = raw_text.splitlines()

        for line in lines:

            line = line.strip()

            if not line:
                continue

            # =========================
            # COURT NUMBER
            # =========================

            court_match = re.search(
                r'Court\s+(\d+)',
                line
            )

            if court_match:

                current_court = court_match.group(1)

                current_bench = ''

                
            # =========================
            # DATE
            # =========================

            date_match = re.search(
                r'DATE:\s*([0-9\-]+)',
                line
            )

            if date_match:

                raw_date = date_match.group(1)

                try:

                    parsed_date = datetime.strptime(
                        raw_date,
                        '%d-%m-%Y'
                    )

                    current_date = parsed_date.strftime(
                        '%Y-%m-%d'
                    )

                except:

                    current_date = raw_date

                continue

            # =========================
            # BENCH
            # =========================

            if 'HON' in line.upper():

                current_bench += line + ' '

                continue

            # =========================
            # MAIN CASE LINE
            # =========================

            case_match = re.match(
                r'^(\d+)\s+([A-Z,\/]+)\s+([A-Z]+\/\d+\/\d+)',
                line
            )

            if case_match:

                serial_no = case_match.group(1)

                status = case_match.group(2).strip(',')

                case_no = case_match.group(3)

                new_case = Case(

                    listing_date=current_date,

                    court_no=current_court,

                    bench=current_bench.strip(),

                    serial_no=serial_no,

                    case_no=case_no,

                    connected_cases='',

                    record_type='PB+R',

                    status=status,

                    remarks=''
                )

                db.session.add(new_case)

                db.session.flush()

                last_case = new_case

                continue

            # =========================
            # CONNECTED CASES
            # =========================

            connected_match = re.match(
                r'^WITH\s+([A-Z]+\/\d+\/\d+)',
                line
            )

            if connected_match and last_case:

                connected_case = connected_match.group(1)

                if last_case.connected_cases:

                    last_case.connected_cases += (
                        '\n' + connected_case
                    )

                else:

                    last_case.connected_cases = connected_case

        db.session.commit()

        flash('Cause List Imported Successfully')

        return redirect(url_for('all_cases'))

    return render_template('import_cause_list.html')

# =========================================
# JR CASES
# =========================================

@app.route('/jr-cases')
@login_required
def jr_cases():

    cases = Case.query.filter_by(
        status='JR',
        jr_received=False
    ).order_by(
        Case.listing_date.desc(),
        Case.court_no
    ).all()

    return render_template(
        'jr_cases.html',
        cases=cases
    )

# =========================================
# ALL CASES
# =========================================

@app.route('/all-cases')
@login_required
def all_cases():

    selected_date = request.args.get('date')

    if selected_date:

        cases = Case.query.filter_by(
            listing_date=selected_date
        ).order_by(
            Case.court_no,
            Case.serial_no
        ).all()

    else:

        cases = Case.query.order_by(
            Case.created_at.desc()
        ).all()

    return render_template(
        'all_cases.html',
        cases=cases,
        selected_date=selected_date
    )

# =========================================
# RUN APPLICATION
# =========================================

if __name__ == '__main__':

    app.run(
        debug=True,
        host='0.0.0.0',
        port=5000
    )
