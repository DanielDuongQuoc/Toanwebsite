import os
from werkzeug.utils import secure_filename
from flask import Flask, render_template, redirect, url_for, flash, request
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from manage_sql import Product,db , Role, User, Order, initialize_database
from werkzeug.security import generate_password_hash, check_password_hash
from flask import session, jsonify

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

db.init_app(app)

login_manager = LoginManager(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))
@app.route('/')
def index():
    return render_template('base.html')

@app.route('/products')
def products():
    return "<h1>Products Page</h1><p>List of products will be displayed here.</p>"

@app.route('/cart')
def cart():
    cart = session.get('cart', {})
    total = sum(item['price'] * item['quantity'] for item in cart.values())
    return render_template('cart.html', cart=cart, total=total)

@app.route('/account_redirect')
def account_redirect():
    if current_user.is_authenticated:
        # Nếu đã đăng nhập, chuyển đến trang tài khoản
        return redirect(url_for('account'))
    else:
        # Nếu chưa đăng nhập, chuyển đến trang đăng nhập
        return redirect(url_for('login'))

@app.route('/account')
@login_required
def account():
    return render_template('account.html', user=current_user)

@app.route('/manage', methods=['GET', 'POST'])
@login_required
def manage():
    if current_user.role.name != 'Admin':
        flash('Access denied! Only admins can access this page.', 'danger')
        return redirect(url_for('index'))

    # Lấy danh sách sản phẩm từ cơ sở dữ liệu
    products = Product.query.all()

    return render_template('manage.html', products=products)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            flash('Đăng nhập thành công!', 'success')
            return redirect(url_for('index'))
        flash('Tên đăng nhập hoặc mật khẩu không đúng.', 'danger')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        role_name = request.form.get('role')
        role = Role.query.filter_by(name=role_name).first()
        if not role:
            flash('Invalid role selected', 'danger')
            return redirect(url_for('register'))
        new_user = User(username=username, email=email, role=role)
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()
        flash('Registration successful! You can now log in.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/search', methods=['GET'])
def search_products():
    name = request.args.get('name', '').strip()
    min_price = request.args.get('min_price', type=float)
    max_price = request.args.get('max_price', type=float)
    category = request.args.get('category', '').strip()

    # Bắt đầu truy vấn
    query = Product.query

    # Lọc theo tên
    if name:
        query = query.filter(Product.name.ilike(f"%{name}%"))

    # Lọc theo khoảng giá
    if min_price is not None:
        query = query.filter(Product.price >= min_price)
    if max_price is not None:
        query = query.filter(Product.price <= max_price)

    # Lọc theo category
    if category:
        query = query.filter(Product.category == category)

    # Lấy danh sách sản phẩm
    products = query.all()

    return render_template('search_results.html', products=products)

@app.route('/admin_dashboard')
@login_required
def admin_dashboard():
    if current_user.role.name != 'Admin':
        flash('Access denied!', 'danger')
        return redirect(url_for('user_dashboard'))
    users = User.query.all()
    orders = Order.query.all()
    return render_template('admin_dashboard.html', users=users, orders=orders)

@app.route('/user_dashboard')
@login_required
def user_dashboard():
    orders = Order.query.filter_by(user_id=current_user.id).all()
    return render_template('user_dashboard.html', orders=orders)

@app.route('/add_product', methods=['GET', 'POST'])
@login_required
def add_product():
    if current_user.role.name != 'Admin':
        flash('Access denied!', 'danger')
        return redirect(url_for('index'))

    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        price = request.form.get('price')
        category = request.form.get('category')

        # Xử lý ảnh tải lên
        if 'image' not in request.files:
            flash('No file part', 'danger')
            return redirect(request.url)
        file = request.files['image']
        if file.filename == '':
            flash('No selected file', 'danger')
            return redirect(request.url)
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            image_url = f"uploads/{filename}"  # Lưu đường dẫn tương đối

            # Lưu sản phẩm vào cơ sở dữ liệu
            new_product = Product(name=name, description=description, price=price, image_url=image_url, category=category)
            db.session.add(new_product)
            db.session.commit()
            flash('Product added successfully!', 'success')
            return redirect(url_for('manage'))

    return render_template('add_product.html')



@app.route('/edit_product/<int:product_id>', methods=['GET', 'POST'])
@login_required
def edit_product(product_id):
    if current_user.role.name != 'Admin':
        flash('Access denied!', 'danger')
        return redirect(url_for('index'))

    product = Product.query.get_or_404(product_id)

    if request.method == 'POST':
        # Cập nhật thông tin sản phẩm
        product.name = request.form.get('name')
        product.description = request.form.get('description')
        product.price = request.form.get('price')
        product.category = request.form.get('category')

        # Xử lý ảnh tải lên
        if 'image' in request.files and request.files['image'].filename != '':
            file = request.files['image']
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                product.image_url = f"uploads/{filename}"  # Cập nhật đường dẫn ảnh mới

        db.session.commit()
        flash('Product updated successfully!', 'success')
        return redirect(url_for('manage'))

    return render_template('edit_product.html', product=product)

@app.route('/delete_product/<int:product_id>', methods=['POST'])
@login_required
def delete_product(product_id):
    if current_user.role.name != 'Admin':
        flash('Access denied!', 'danger')
        return redirect(url_for('index'))

    product = Product.query.get_or_404(product_id)
    db.session.delete(product)
    db.session.commit()
    flash('Product deleted successfully!', 'success')
    return redirect(url_for('manage'))

@app.route('/category/<string:category_name>')
def category_products(category_name):
    # Lấy danh sách sản phẩm thuộc category
    products = Product.query.filter_by(category=category_name).all()
    return render_template('category_products.html', products=products, category_name=category_name)

@app.route('/add_to_cart/<int:product_id>', methods=['POST'])
def add_to_cart(product_id):
    product = Product.query.get_or_404(product_id)
    cart = session.get('cart', {})

    if str(product_id) in cart:
        cart[str(product_id)]['quantity'] += 1
    else:
        cart[str(product_id)] = {
            'name': product.name,
            'price': product.price,
            'quantity': 1
        }

    session['cart'] = cart
    return jsonify({'message': f'{product.name} has been added to your cart!'})

@app.route('/checkout', methods=['POST'])
def checkout():
    session.pop('cart', None)
    flash('Thank you for your purchase!', 'success')
    return redirect(url_for('index'))

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

if __name__ == '__main__':
    initialize_database(app)  # Initialize the database with default data
    app.run(debug=True)