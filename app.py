import os
import json
import time
from functools import wraps
from werkzeug.utils import secure_filename
from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from flask_sqlalchemy import SQLAlchemy
import razorpay

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///krishnajawli.db'
app.config['SECRET_KEY'] = 'krishna_jawli_super_secret_2026'
app.config['UPLOAD_FOLDER'] = os.path.join('static', 'uploads')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp'}

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
db = SQLAlchemy(app)

# --- ADMIN CREDENTIALS ---
ADMIN_EMAIL = "joeljoel572y@gmail.com"
ADMIN_PASSWORD = "krishna@jawli2026"

# --- CONFIGURED RAZORPAY TEST CREDENTIALS ---
RAZORPAY_KEY_ID = "rzp_test_TbXzNlIZrtPYMB"
RAZORPAY_KEY_SECRET = "Pb5k61Ku05Evqc27Heebrx3U"

razorpay_client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))

CATEGORY_DATA = {
    "Handloom Products": ["Handloom Sarees", "Cotton Sarees", "Traditional Towels", "Temple Towels", "Handloom Dhoties"],
    "Home Textiles": ["Bedsheets", "Pillow Covers", "Curtains", "Blankets", "Sofa Covers"],
    "Kerchiefs for Men & Women": ["Men Kerchiefs", "Women Kerchiefs", "Cotton Kerchiefs", "Printed Kerchiefs"],
    "Kids & Babywears": ["Baby Dress", "Baby Sets", "Baby Towels", "Baby Innerwear"],
    "Kids Fashion": ["T-Shirts", "Shorts", "Frocks", "Kids Nightwear"],
    "Kids Innerwears": ["Kids Vests", "Kids Briefs", "Kids Slips"],
    "Lungies": ["Cotton Lungies", "Printed Lungies", "Checked Lungies"],
    "Mens Fashion": ["Shirts", "T-Shirts", "Pants", "Shorts"],
    "Mens Innerwear": ["White Vests", "Gym Vests", "Elastic Vests", "Briefs", "Boxers", "Half Drawers"],
    "Women Fashion": ["Leggings", "Nighties", "Sarees", "Shawls"],
    "Women Innerwears": ["Slips", "Adjustable Slips", "Bras", "Panties", "Camisoles"],
    "Pooja Textiles": ["Temple Towels", "God Sarees", "Pooja Cloth", "Traditional Towels"],
    "Towels": ["Bath Towels", "Hand Towels", "Cotton Towels", "Temple Towels"],
    "Nighties": ["Cotton Nighties", "Printed Nighties", "Feeding Nighties"],
    "New Born Baby Dress": ["Baby Kits", "Baby Dress Sets", "Baby Gift Packs"],
    "New Born Baby Gift Boxes": ["Baby Combo Sets", "Gift Packs", "Premium Baby Sets"],
    "Blouse Piece": ["Cotton Blouse Piece", "Silk Blouse Piece", "Designer Blouse Piece"],
    "Lining for Blouse": ["Cotton Lining", "Stretch Lining", "Matching Lining"],
    "Summer Products for Men & Women": ["Cooling Vests", "Summer Towels", "Cotton Wear"],
    "Summer Products for Kids": ["Kids Summer Vest", "Kids Shorts", "Cooling Innerwear"],
    "Old Age Products": ["Easy Wear Vest", "Soft Towels", "Comfortable Innerwear"],
    "Inskirt": ["Cotton Inskirt", "Stretch Inskirt", "Saree Inskirt"],
    "Leggings": ["Cotton Leggings", "Ankle Leggings", "Churidar Leggings"],
    "Shirts": ["Casual Shirts", "Formal Shirts", "Cotton Shirts"]
}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# --- DATABASE MODELS ---
class StoreSetting(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    cgst_percent = db.Column(db.Float, default=2.5)
    sgst_percent = db.Column(db.Float, default=2.5)
    discount_percent = db.Column(db.Float, default=5.0)

class Banner(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    badge = db.Column(db.String(100), default="Direct from Weavers")
    title = db.Column(db.String(200), nullable=False)
    subtitle = db.Column(db.String(300), nullable=True)
    button_text = db.Column(db.String(100), default="Explore Collection")
    link_url = db.Column(db.String(200), default="#catalog")
    image = db.Column(db.String(255), nullable=False)

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    category = db.Column(db.String(100), nullable=False)
    subcategory = db.Column(db.String(100), nullable=False)
    price = db.Column(db.Float, nullable=False)
    sizes_json = db.Column(db.Text, default='[]')
    colors_json = db.Column(db.Text, default='["White"]')
    stock = db.Column(db.Integer, default=25)
    description = db.Column(db.Text, nullable=True)
    tag = db.Column(db.String(50), default="Trending")
    image = db.Column(db.String(255), default="/static/uploads/default.jpg")

    def get_sizes(self):
        try:
            return json.loads(self.sizes_json)
        except Exception:
            return []

    def get_colors(self):
        try:
            return json.loads(self.colors_json)
        except Exception:
            return ["Standard / Default"]

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    customer_name = db.Column(db.String(100), nullable=False)
    customer_phone = db.Column(db.String(20), nullable=False)
    address = db.Column(db.Text, nullable=False)
    items_summary = db.Column(db.Text, default="")
    subtotal = db.Column(db.Float, nullable=False)
    cgst = db.Column(db.Float, nullable=False)
    sgst = db.Column(db.Float, nullable=False)
    discount = db.Column(db.Float, nullable=False)
    grand_total = db.Column(db.Float, nullable=False)
    payment_status = db.Column(db.String(30), default="Pending")
    razorpay_order_id = db.Column(db.String(100), nullable=True)
    razorpay_payment_id = db.Column(db.String(100), nullable=True)
    shipping_notes = db.Column(db.String(250), default="Standard delivery")
    delivery_date = db.Column(db.String(50), default="3-5 Business Days")
    created_at = db.Column(db.DateTime, server_default=db.func.now())

def get_settings():
    setting = StoreSetting.query.first()
    if not setting:
        setting = StoreSetting(cgst_percent=2.5, sgst_percent=2.5, discount_percent=5.0)
        db.session.add(setting)
        db.session.commit()
    return setting

@app.context_processor
def inject_globals():
    cart = session.get('cart', {})
    total_count = sum(item['quantity'] for item in cart.values())
    settings = get_settings()
    return dict(
        cart_count=total_count,
        category_tree=CATEGORY_DATA,
        cgst_rate=settings.cgst_percent,
        sgst_rate=settings.sgst_percent,
        discount_rate=settings.discount_percent
    )

def seed_initial_data():
    if Banner.query.count() == 0:
        b1 = Banner(
            badge="Direct from Weavers",
            title="Authentic Handloom & Traditional Sarees",
            subtitle="Pure cotton Kanchi weave sarees, traditional pooja cloths, and soft double dhoties at direct wholesale prices.",
            button_text="Explore Collection",
            link_url="#catalog",
            image="https://images.unsplash.com/photo-1610030469983-98e550d6193c?w=1600"
        )
        b2 = Banner(
            badge="Premium Comfort",
            title="100% Pure Cotton Home Textiles",
            subtitle="King-size double bedsheets, dust-resistant sofa covers, Turkish-weave bath towels, and pillow covers.",
            button_text="Shop Bedsheets & Towels",
            link_url="/?category=Home+Textiles#catalog",
            image="https://images.unsplash.com/photo-1522771739844-6a9f6d5f14af?w=1600"
        )
        db.session.add_all([b1, b2])

    if Product.query.count() == 0:
        sample1 = Product(
            name="Men's Combed Cotton White Vest",
            category="Mens Innerwear",
            subcategory="White Vests",
            price=100.0,
            sizes_json=json.dumps([
                {"size": "80", "price": 95.0},
                {"size": "85", "price": 100.0},
                {"size": "90", "price": 105.0}
            ]),
            colors_json=json.dumps(["White"]),
            stock=50,
            description="Pure combed cotton sweat-absorbing breathable vest.",
            tag="Bestseller",
            image="https://images.unsplash.com/photo-1583743814966-8936f5b7be1a?w=500"
        )
        sample2 = Product(
            name="Traditional Kanchi Cotton Handloom Saree",
            category="Handloom Products",
            subcategory="Handloom Sarees",
            price=1250.0,
            sizes_json=json.dumps([
                {"size": "Standard (6.3m)", "price": 1250.0}
            ]),
            colors_json=json.dumps(["Maroon", "Mustard Yellow", "Peacock Green"]),
            stock=20,
            description="Pure cotton handloom woven saree with traditional border.",
            tag="Trending",
            image="https://images.unsplash.com/photo-1610030469983-98e550d6193c?w=500"
        )
        db.session.add_all([sample1, sample2])
    db.session.commit()

# --- ADMIN AUTHENTICATION ---
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('admin_logged_in'):
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    error = None
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        pwd = request.form.get('password', '').strip()

        if email == ADMIN_EMAIL.lower() and pwd == ADMIN_PASSWORD:
            session['admin_logged_in'] = True
            session['login_timestamp'] = time.time()
            session['login_time_str'] = time.strftime('%d-%b-%Y, %I:%M %p')
            session['login_ip'] = request.remote_addr or '127.0.0.1'

            ua = request.headers.get('User-Agent', '')
            os_name = "Windows PC" if "Windows" in ua else ("macOS" if "Mac" in ua else ("Android" if "Android" in ua else ("iPhone" if "iPhone" in ua else "Device")))
            browser_name = "Edge" if "Edg" in ua else ("Chrome" if "Chrome" in ua else ("Firefox" if "Firefox" in ua else ("Safari" if "Safari" in ua else "Browser")))
            session['login_device'] = f"{os_name} • {browser_name}"

            return redirect(url_for('admin_dashboard'))
        else:
            error = "Invalid admin email or password."
    return render_template('admin_login.html', error=error)

@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_logged_in', None)
    session.pop('login_timestamp', None)
    session.pop('login_time_str', None)
    session.pop('login_device', None)
    session.pop('login_ip', None)
    return redirect(url_for('admin_login'))

@app.route('/admin')
@admin_required
def admin_dashboard():
    filter_status = request.args.get('status', 'all')
    settings = get_settings()

    query = Order.query.order_by(Order.id.desc())
    if filter_status == 'success':
        orders = query.filter_by(payment_status="Paid / Success").all()
    elif filter_status == 'cancelled':
        orders = query.filter_by(payment_status="Cancelled / Failed").all()
    else:
        orders = query.all()

    products = Product.query.order_by(Product.id.desc()).all()
    banners = Banner.query.order_by(Banner.id.desc()).all()
    paid_orders = Order.query.filter_by(payment_status="Paid / Success").all()
    total_revenue = sum(o.grand_total for o in paid_orders)
    paid_count = len(paid_orders)
    failed_count = Order.query.filter_by(payment_status="Cancelled / Failed").count()

    login_timestamp = session.get('login_timestamp', time.time())
    login_time_str = session.get('login_time_str', time.strftime('%d-%b-%Y, %I:%M %p'))
    login_device = session.get('login_device', 'Windows PC • Browser')
    login_ip = session.get('login_ip', '127.0.0.1')

    return render_template(
        'admin.html',
        products=products,
        banners=banners,
        orders=orders,
        settings=settings,
        filter_status=filter_status,
        total_revenue=total_revenue,
        paid_count=paid_count,
        failed_count=failed_count,
        login_timestamp=login_timestamp,
        login_time_str=login_time_str,
        login_device=login_device,
        login_ip=login_ip
    )

@app.route('/admin/add-banner', methods=['POST'])
@admin_required
def add_banner():
    badge = request.form.get('badge', 'Special Offer')
    title = request.form.get('title')
    subtitle = request.form.get('subtitle', '')
    button_text = request.form.get('button_text', 'Explore Collection')
    link_url = request.form.get('link_url', '#catalog')

    image_url = "https://images.unsplash.com/photo-1610030469983-98e550d6193c?w=1600"
    if 'banner_image' in request.files:
        file = request.files['banner_image']
        if file and allowed_file(file.filename):
            filename = secure_filename("banner_" + file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            image_url = f"/static/uploads/{filename}"

    new_banner = Banner(
        badge=badge,
        title=title,
        subtitle=subtitle,
        button_text=button_text,
        link_url=link_url,
        image=image_url
    )
    db.session.add(new_banner)
    db.session.commit()
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/delete-banner/<int:banner_id>', methods=['POST'])
@admin_required
def delete_banner(banner_id):
    banner = Banner.query.get_or_404(banner_id)
    db.session.delete(banner)
    db.session.commit()
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/add-product', methods=['POST'])
@admin_required
def add_product():
    name = request.form.get('name')
    category = request.form.get('category')
    subcategory = request.form.get('subcategory')
    stock = int(request.form.get('stock', 25))
    tag = request.form.get('tag', 'Trending')
    description = request.form.get('description', '')

    colors_raw = request.form.get('colors', 'White')
    colors_list = [c.strip() for c in colors_raw.split(',') if c.strip()]
    if not colors_list:
        colors_list = ["Standard / Default"]

    sizes = request.form.getlist('sizes[]')
    prices = request.form.getlist('prices[]')

    sizes_list = []
    base_price = 0.0
    for s, p in zip(sizes, prices):
        s_clean = s.strip()
        if s_clean and p.strip():
            price_val = float(p)
            sizes_list.append({"size": s_clean, "price": price_val})
            if base_price == 0.0:
                base_price = price_val

    if not sizes_list:
        base_price = float(request.form.get('single_price', 100.0))
        sizes_list.append({"size": "Standard", "price": base_price})

    image_url = "/static/uploads/default.jpg"
    if 'product_image' in request.files:
        file = request.files['product_image']
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            image_url = f"/static/uploads/{filename}"

    new_prod = Product(
        name=name,
        category=category,
        subcategory=subcategory,
        price=base_price,
        sizes_json=json.dumps(sizes_list),
        colors_json=json.dumps(colors_list),
        stock=stock,
        tag=tag,
        description=description,
        image=image_url
    )
    db.session.add(new_prod)
    db.session.commit()
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/delete-product/<int:product_id>', methods=['POST'])
@admin_required
def delete_product(product_id):
    product = Product.query.get_or_404(product_id)
    db.session.delete(product)
    db.session.commit()
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/update-settings', methods=['POST'])
@admin_required
def update_settings():
    settings = get_settings()
    settings.cgst_percent = float(request.form.get('cgst_percent', 2.5))
    settings.sgst_percent = float(request.form.get('sgst_percent', 2.5))
    settings.discount_percent = float(request.form.get('discount_percent', 5.0))
    db.session.commit()
    return redirect(url_for('admin_dashboard'))

# --- FRONT-END STORE ROUTES ---
@app.route('/')
def home():
    selected_cat = request.args.get('category')
    selected_subcat = request.args.get('subcategory')
    banners = Banner.query.all()
    
    query = Product.query
    if selected_cat:
        query = query.filter_by(category=selected_cat)
    if selected_subcat:
        query = query.filter_by(subcategory=selected_subcat)
        
    if selected_cat or selected_subcat:
        filtered_products = query.all()
        subcategories = CATEGORY_DATA.get(selected_cat, [])
        return render_template(
            'index.html',
            banners=banners,
            selected_category=selected_cat,
            selected_subcategory=selected_subcat,
            subcategories=subcategories,
            filtered_products=filtered_products
        )
    
    trending = Product.query.filter_by(tag="Trending").all()
    bestsellers = Product.query.filter_by(tag="Bestseller").all()
    new_arrivals = Product.query.filter_by(tag="New Arrival").all()
    return render_template('index.html', banners=banners, trending=trending, bestsellers=bestsellers, new_arrivals=new_arrivals)

@app.route('/product/<int:product_id>')
def product_detail(product_id):
    product = Product.query.get_or_404(product_id)
    return render_template('product.html', product=product)

@app.route('/add-to-cart/<int:product_id>', methods=['POST'])
def add_to_cart(product_id):
    product = Product.query.get_or_404(product_id)
    quantity = int(request.form.get('quantity', 1))
    size = request.form.get('size', 'Standard')
    color = request.form.get('color', 'Standard')
    chosen_price = float(request.form.get('price', product.price))
    action = request.form.get('action', 'add_to_cart')
    is_ajax = request.form.get('ajax') == '1'
    
    if 'cart' not in session:
        session['cart'] = {}
    
    cart = session['cart']
    item_key = f"{product_id}_{size}_{color}"
    
    if item_key in cart:
        cart[item_key]['quantity'] += quantity
    else:
        cart[item_key] = {
            'id': product.id,
            'name': product.name,
            'price': chosen_price,
            'size': size,
            'color': color,
            'quantity': quantity,
            'category': product.category,
            'subcategory': product.subcategory
        }
    session.modified = True
    
    total_count = sum(item['quantity'] for item in cart.values())

    if is_ajax:
        return jsonify({'status': 'success', 'cart_count': total_count})
    if action == 'buy_now':
        return redirect(url_for('checkout'))
    return redirect(url_for('view_cart'))

@app.route('/cart')
def view_cart():
    cart = session.get('cart', {})
    subtotal = sum(item['price'] * item['quantity'] for item in cart.values())
    return render_template('cart.html', cart=cart, subtotal=subtotal)

@app.route('/cart/remove/<item_key>')
def remove_from_cart(item_key):
    cart = session.get('cart', {})
    if item_key in cart:
        del cart[item_key]
        session.modified = True
    return redirect(url_for('view_cart'))

@app.route('/checkout', methods=['GET'])
def checkout():
    cart = session.get('cart', {})
    subtotal = sum(item['price'] * item['quantity'] for item in cart.values())
    if subtotal == 0:
        subtotal = 1000.0

    settings = get_settings()
    cgst = round(subtotal * (settings.cgst_percent / 100.0), 2)
    sgst = round(subtotal * (settings.sgst_percent / 100.0), 2)
    discount = round(subtotal * (settings.discount_percent / 100.0), 2)
    grand_total = round(subtotal + cgst + sgst - discount, 2)
    amount_in_paise = int(grand_total * 100)

    try:
        rzp_order = razorpay_client.order.create(data={
            "amount": amount_in_paise,
            "currency": "INR",
            "receipt": f"rcpt_{int(time.time())}",
            "payment_capture": 1
        })
        razorpay_order_id = rzp_order['id']
    except Exception as e:
        print(f"[Razorpay Order Error]: {e}")
        razorpay_order_id = f"order_local_{int(time.time())}"

    return render_template(
        'checkout.html',
        cart=cart,
        subtotal=subtotal,
        cgst=cgst,
        sgst=sgst,
        discount=discount,
        grand_total=grand_total,
        amount_in_paise=amount_in_paise,
        razorpay_order_id=razorpay_order_id,
        razorpay_key_id=RAZORPAY_KEY_ID
    )

@app.route('/payment/success', methods=['POST'])
def payment_success():
    cart = session.get('cart', {})
    items_str = ", ".join([
        f"{item['name']} (Size: {item['size']}, Color: {item.get('color', 'Standard')}) x {item['quantity']}" 
        for item in cart.values()
    ]) or "Direct Order"

    customer_name = request.form.get('customer_name')
    customer_phone = request.form.get('customer_phone')
    address = request.form.get('address')
    shipping_notes = request.form.get('shipping_notes', 'Standard delivery')
    subtotal = float(request.form.get('subtotal', 0))
    cgst = float(request.form.get('cgst', 0))
    sgst = float(request.form.get('sgst', 0))
    discount = float(request.form.get('discount', 0))
    grand_total = float(request.form.get('grand_total', 0))

    razorpay_payment_id = request.form.get('razorpay_payment_id')
    razorpay_order_id = request.form.get('razorpay_order_id')
    razorpay_signature = request.form.get('razorpay_signature')

    if razorpay_signature:
        try:
            razorpay_client.utility.verify_payment_signature({
                'razorpay_order_id': razorpay_order_id,
                'razorpay_payment_id': razorpay_payment_id,
                'razorpay_signature': razorpay_signature
            })
        except Exception as e:
            print(f"[Razorpay Signature Verification Error]: {e}")

    new_order = Order(
        customer_name=customer_name,
        customer_phone=customer_phone,
        address=address,
        items_summary=items_str,
        subtotal=subtotal,
        cgst=cgst,
        sgst=sgst,
        discount=discount,
        grand_total=grand_total,
        payment_status="Paid / Success",
        razorpay_payment_id=razorpay_payment_id,
        razorpay_order_id=razorpay_order_id,
        shipping_notes=shipping_notes
    )
    db.session.add(new_order)
    db.session.commit()
    session.pop('cart', None)

    return redirect(url_for('invoice', order_id=new_order.id))

@app.route('/payment/cancel-record', methods=['POST'])
def payment_cancel_record():
    cart = session.get('cart', {})
    items_str = ", ".join([
        f"{item['name']} (Size: {item['size']}, Color: {item.get('color', 'Standard')}) x {item['quantity']}" 
        for item in cart.values()
    ]) or "Cart Items"

    data = request.get_json(silent=True) or request.form.to_dict() or {}

    def safe_float(v):
        try:
            return float(v)
        except Exception:
            return 0.0

    customer_name = str(data.get('customer_name', '')).strip() or 'Visitor (Incomplete)'
    customer_phone = str(data.get('customer_phone', '')).strip() or 'Not Provided'
    address = str(data.get('address', '')).strip() or 'Not Provided'
    subtotal = safe_float(data.get('subtotal'))
    cgst = safe_float(data.get('cgst'))
    sgst = safe_float(data.get('sgst'))
    discount = safe_float(data.get('discount'))
    grand_total = safe_float(data.get('grand_total'))
    reason = str(data.get('reason', 'Payment window cancelled or rejected by user.'))

    cancelled_order = Order(
        customer_name=customer_name,
        customer_phone=customer_phone,
        address=address,
        items_summary=items_str,
        subtotal=subtotal,
        cgst=cgst,
        sgst=sgst,
        discount=discount,
        grand_total=grand_total,
        payment_status="Cancelled / Failed",
        shipping_notes=f"Failed reason: {reason}"
    )
    db.session.add(cancelled_order)
    db.session.commit()

    return jsonify({"status": "recorded", "order_id": cancelled_order.id})

@app.route('/payment/failed')
def payment_failed():
    reason = request.args.get('reason', 'Payment cancelled or incomplete.')
    return render_template('payment_failed.html', reason=reason)

@app.route('/invoice/<int:order_id>')
def invoice(order_id):
    order = Order.query.get_or_404(order_id)
    if order.payment_status != "Paid / Success":
        return redirect(url_for('payment_failed', reason="Cannot generate invoice for unpaid or cancelled order."))
    return render_template('invoice.html', order=order)

# =========================================================================
# PRODUCTION DATABASE INITIALIZATION
# =========================================================================
with app.app_context():
    db.create_all()
    seed_initial_data()

if __name__ == '__main__':
    app.run(debug=True)