from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

class Role(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)

class Menu(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=True)
    price = db.Column(db.Float, nullable=False)
    image_url = db.Column(db.String(300), nullable=False)  # URL của ảnh
    category = db.Column(db.String(50), nullable=False)  # Loại menu

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    role_id = db.Column(db.Integer, db.ForeignKey('role.id'), nullable=False)
    role = db.relationship('Role', backref=db.backref('users', lazy=True))

    def set_password(self, password):
        self.password = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password, password)

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    product_name = db.Column(db.String(150), nullable=False)
    status = db.Column(db.String(50), nullable=False)
    user = db.relationship('User', backref=db.backref('orders', lazy=True))
    
class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=True)
    price = db.Column(db.Float, nullable=False)
    image_url = db.Column(db.String(300), nullable=False)  # Đường dẫn ảnh
    category = db.Column(db.String(50), nullable=False)

def initialize_database(app):
    with app.app_context():
        db.create_all()

        # Add default roles
        if not Role.query.filter_by(name='Admin').first():
            admin_role = Role(name='Admin')
            db.session.add(admin_role)
        if not Role.query.filter_by(name='User').first():
            user_role = Role(name='User')
            db.session.add(user_role)

        # Add a default admin user
        if not User.query.filter_by(username='admin').first():
            admin_user = User(
                username='admin',
                email='admin@example.com',
                role=Role.query.filter_by(name='Admin').first()
            )
            admin_user.set_password('admin123')  # Set a default password
            db.session.add(admin_user)

        db.session.commit()