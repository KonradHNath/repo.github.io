# Correct import of app instance
from app import app, db
from models import User

# Run the code within the app's context
with app.app_context():
    user = User.query.filter_by(email='konradnath@gmail.com').first()
    if user:
        user.is_admin = True
        db.session.commit()
        print("User set as administrator.")
    else:
        print("User not found.")
