from app import app, db, User

with app.app_context():
    user = User.query.filter_by(email='konradnath@gmail.com').first()
    if user:
        print(f"User '{user.email}' has is_admin = {user.is_admin}")
    else:
        print("User not found.")
