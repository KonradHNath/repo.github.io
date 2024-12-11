from flask import Flask, request, redirect, url_for, flash, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_socketio import SocketIO, emit
from flask_dance.contrib.google import make_google_blueprint, google
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os
import time
from datetime import datetime

# Import models from models.py
from models import db, User, Meeting, MeetingParticipants

app = Flask(__name__, template_folder='custom_templates_folder')
app.secret_key = os.urandom(24)

# Database setup with absolute path
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

migrate = Migrate(app, db)

# Flask-Login setup
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Flask-Dance Google OAuth setup
google_bp = make_google_blueprint(
    client_id="783838472485-hlrgppdm7b8oshpfnmpn6vssq8rfu2sn.apps.googleusercontent.com",
    client_secret="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",
    redirect_to="google_login_callback"
)
app.register_blueprint(google_bp, url_prefix="/login")

socketio = SocketIO(app)

# Routes
@app.route("/")
def home():
    return render_template("home.html", timestamp=int(time.time()))

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            flash("Du er logget ind!", "success")
            return redirect(url_for("dashboard"))
        flash("Forkert email eller adgangskode.", "danger")
    return render_template("login.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        first_name = request.form.get("first_name")
        last_name = request.form.get("last_name")
        email = request.form.get("email")
        password = request.form.get("password")
        birth_date = request.form.get("birth_date")  # Hent fødselsdato

        if not first_name or not last_name or not email or not password:
            flash("Alle felter skal udfyldes.", "danger")
            return redirect(url_for("register"))

        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash("Denne email er allerede registreret.", "danger")
            return redirect(url_for("register"))

        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')

        # Opret en ny bruger med de ekstra oplysninger
        new_user = User(
            first_name=first_name,
            last_name=last_name,
            email=email,
            password=hashed_password,
            birth_date=datetime.strptime(birth_date, "%Y-%m-%d") if birth_date else None
        )
        db.session.add(new_user)
        db.session.commit()
        flash("Din profil er oprettet! Log venligst ind.", "success")
        return redirect(url_for("login"))
    return render_template("register.html")

@app.route("/google_login_callback")
def google_login_callback():
    if not google.authorized:
        return redirect(url_for("google.login"))
    resp = google.get("https://www.googleapis.com/oauth2/v2/userinfo")
    if resp.ok:
        google_info = resp.json()
        user = User.query.filter_by(google_id=google_info["id"]).first()
        if not user:
            user = User(email=google_info["email"], google_id=google_info["id"])
            db.session.add(user)
            db.session.commit()
        login_user(user)
        return redirect(url_for("dashboard"))
    flash("Kunne ikke hente brugeroplysninger fra Google.", "danger")
    return redirect(url_for("login"))

@app.route("/dashboard")
@login_required
def dashboard():
    user_meetings = current_user.meetings if current_user.meetings else []
    available_meetings = Meeting.query.filter(~Meeting.id.in_([m.id for m in user_meetings])).all()
    return render_template("dashboard.html", user_meetings=user_meetings, available_meetings=available_meetings)

@app.route("/logout")
def logout():
    logout_user()  # Log brugeren ud
    flash("Du er logget ud.", "info")
    return redirect(url_for("home"))  # Omdirigér til forsiden

@app.route("/chat")
@login_required
def chat():
    return render_template("chat.html")

@socketio.on('message')
def handle_message(data):
    name = data.get('name')
    age = data.get('age')
    time = data.get('time')
    message = data.get('message')

@app.route("/anonymous_chat")
@login_required
def anonymous_chat():
    return render_template("anonymous_chat.html")

@socketio.on('anonymous_message', namespace='/anonymous')
def handle_anonymous_message(data):
    """
    Håndterer anonyme beskeder og sender dem til alle klienter forbundet til namespace '/anonymous'.
    """
    print(f"Modtaget besked: {data}")  # Debug: Log beskeden på serveren
    emit('anonymous_message', data, broadcast=True, namespace='/anonymous')

    # Send besked til alle tilsluttede klienter
    emit('message', {
        'name': name,
        'age': age,
        'time': time,
        'message': message
    }, broadcast=True)

@app.route("/register_for_meeting/<int:meeting_id>", methods=["POST"])
@login_required
def register_for_meeting(meeting_id):
    meeting = Meeting.query.get(meeting_id)
    if not meeting:
        flash("Mødet findes ikke.", "danger")
        return redirect(url_for("dashboard"))

    # Check if max_participants is None or invalid
    if meeting.max_participants is None:
        flash("Dette møde har ikke et deltagerloft.", "warning")
        return redirect(url_for("dashboard"))
    
    if len(meeting.participants) >= meeting.max_participants:
        flash("Mødet er fuldt booket.", "danger")
        return redirect(url_for("dashboard"))
    
    if current_user in meeting.participants:
        flash("Du er allerede tilmeldt mødet.", "info")
        return redirect(url_for("dashboard"))
    
    # Add the current user to the participants list and commit changes
    meeting.participants.append(current_user)
    db.session.commit()
    flash("Du er blevet tilmeldt mødet!", "success")
    return redirect(url_for("dashboard"))

@app.route("/unregister_from_meeting/<int:meeting_id>", methods=["POST"])
@login_required
def unregister_from_meeting(meeting_id):
    meeting = Meeting.query.get(meeting_id)
    if not meeting:
        flash("Mødet findes ikke.", "danger")
        return redirect(url_for("dashboard"))

    if current_user not in meeting.participants:
        flash("Du er ikke tilmeldt dette møde.", "info")
        return redirect(url_for("dashboard"))

    # Remove the current user from the participants list and commit changes
    meeting.participants.remove(current_user)
    db.session.commit()
    flash("Du er blevet frameldt fra mødet.", "success")
    return redirect(url_for("dashboard"))

@app.route("/admin", methods=["GET", "POST"])
@login_required
def admin_dashboard():
    if not current_user.is_admin:
        flash("Du har ikke tilladelse til at tilgå denne side.", "danger")
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        name = request.form.get("name")
        description = request.form.get("description")
        date = request.form.get("date")
        max_participants = int(request.form.get("max_participants"))
        
        # Opdateret datoformat
        date = datetime.strptime(date, "%Y-%m-%dT%H:%M")

        new_meeting = Meeting(
            name=name,
            description=description,
            date=date,
            max_participants=max_participants,
            created_by=current_user.id
        )
        db.session.add(new_meeting)
        db.session.commit()
        flash("Mødet er oprettet!", "success")
        return redirect(url_for("admin_dashboard"))
    
    meetings = Meeting.query.all()
    return render_template("admin_dashboard.html", meetings=meetings)

@app.route('/edit_meeting/<int:meeting_id>', methods=['GET', 'POST'])
@login_required
def edit_meeting(meeting_id):
    meeting = Meeting.query.get_or_404(meeting_id)
    if request.method == 'POST':
        meeting.name = request.form['name']
        meeting.description = request.form['description']
        meeting.date = request.form['date']
        meeting.max_participants = request.form['max_participants']
        db.session.commit()
        flash('Mødet er blevet opdateret.', 'success')
        return redirect(url_for('admin_dashboard'))
    return render_template('edit_meeting.html', meeting=meeting)

@app.route('/delete_meeting/<int:meeting_id>', methods=['POST'])
@login_required
def delete_meeting(meeting_id):
    # Logik for at slette mødet fra databasen
    meeting = Meeting.query.get_or_404(meeting_id)
    db.session.delete(meeting)
    db.session.commit()
    flash('Mødet er blevet slettet.', 'success')
    return redirect(url_for('admin_dashboard'))

if __name__ == "__main__":
    app.run(debug=True)
    socketio.run(app, debug=True)
