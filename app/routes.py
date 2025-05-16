from flask import Blueprint, render_template, request, redirect, url_for, flash, send_from_directory
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from app import db
from app.models import User, Category, Product, Order, OrderItem
from config import Config
from werkzeug.utils import secure_filename
import os

bp = Blueprint('main', __name__)

@bp.route('/')
@login_required
def index():
    return redirect(url_for('main.categories'))

@bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for('main.index'))
        flash('Неверный логин или пароль', 'danger')
    return render_template('login.html')

@bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('main.login'))

@bp.route('/categories', methods=['GET', 'POST'])
@login_required
def categories():
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'add':
            name = request.form['name']
            if Category.query.filter_by(name=name).first():
                flash('Категория уже существует', 'danger')
            else:
                category = Category(name=name)
                db.session.add(category)
                db.session.commit()
                flash('Категория добавлена', 'success')
        elif action == 'edit':
            category_id = request.form['category_id']
            category = Category.query.get_or_404(category_id)
            category.name = request.form['name']
            db.session.commit()
            flash('Категория обновлена', 'success')
        elif action == 'delete':
            category_id = request.form['category_id']
            category = Category.query.get_or_404(category_id)
            db.session.delete(category)
            db.session.commit()
            flash('Категория удалена', 'success')
    categories = Category.query.all()
    stats = {'total_categories': Category.query.count()}
    return render_template('categories.html', categories=categories, stats=stats)

@bp.route('/products/<int:category_id>', methods=['GET', 'POST'])
@login_required
def products(category_id):
    category = Category.query.get_or_404(category_id)
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'add':
            file = request.files.get('image')
            filename = None
            if file and '.' in file.filename and file.filename.rsplit('.', 1)[1].lower() in Config.ALLOWED_EXTENSIONS:
                filename = secure_filename(file.filename)
                upload_path = os.path.join(Config.UPLOAD_FOLDER, filename)
                os.makedirs(os.path.dirname(upload_path), exist_ok=True)
                file.save(upload_path)
            product = Product(
                name=request.form['name'],
                color=request.form['color'],
                price=float(request.form['price']),
                stock=int(request.form['stock']),
                material=request.form['material'],
                image=filename,
                category_id=category_id
            )
            db.session.add(product)
            db.session.commit()
            flash('Товар добавлен', 'success')
        elif action == 'edit':
            product_id = request.form['product_id']
            product = Product.query.get_or_404(product_id)
            product.name = request.form['name']
            product.color = request.form['color']
            product.price = float(request.form['price'])
            product.stock = int(request.form['stock'])
            product.material = request.form['material']
            file = request.files.get('image')
            if file and '.' in file.filename and file.filename.rsplit('.', 1)[1].lower() in Config.ALLOWED_EXTENSIONS:
                filename = secure_filename(file.filename)
                upload_path = os.path.join(Config.UPLOAD_FOLDER, filename)
                os.makedirs(os.path.dirname(upload_path), exist_ok=True)
                file.save(upload_path)
                product.image = filename
            db.session.commit()
            flash('Товар обновлен', 'success')
        elif action == 'delete':
            product_id = request.form['product_id']
            product = Product.query.get_or_404(product_id)
            db.session.delete(product)
            db.session.commit()
            flash('Товар удален', 'success')
    products = Product.query.filter_by(category_id=category_id).all()
    stats = {'total_products': len(products)}
    return render_template('products.html', category=category, products=products, stats=stats)

@bp.route('/orders')
@login_required
def orders():
    orders = Order.query.all()
    stats = {'total_orders': Order.query.count()}
    return render_template('orders.html', orders=orders, stats=stats)

@bp.route('/uploads/<filename>')
@login_required
def uploaded_file(filename):
    return send_from_directory(Config.UPLOAD_FOLDER, filename)