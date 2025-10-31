from werkzeug.utils import secure_filename
from flask import Flask, render_template, request, redirect, url_for, session
import json
import os

app = Flask(__name__)
app.secret_key = 'supersecretkey'

DATA_FILE = 'data.json'
USERS_FILE = 'users.json'
NOTIFICATIONS_FILE = 'notifications.json'

UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# -------------------------- Helper Functions --------------------------

def read_data():
    try:
        with open(DATA_FILE, "r") as f:
            data = json.load(f)
        if "items" not in data:
            data["items"] = []
        return data
    except FileNotFoundError:
        return {"items": []}


def write_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)


def read_users():
    if os.path.exists(USERS_FILE) and os.path.getsize(USERS_FILE) > 0:
        with open(USERS_FILE, 'r') as f:
            return json.load(f)
    return {}


def write_users(users):
    with open(USERS_FILE, 'w') as f:
        json.dump(users, f, indent=4)


def read_notifications():
    if os.path.exists(NOTIFICATIONS_FILE):
        with open(NOTIFICATIONS_FILE, 'r') as f:
            return json.load(f)
    return []


def write_notifications(notifications):
    with open(NOTIFICATIONS_FILE, 'w') as f:
        json.dump(notifications, f, indent=4)


# -------------------------- ROUTES --------------------------

@app.route('/')
def home():
    return render_template('index.html')


# -------------------------- SIGNUP --------------------------
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        users = read_users()
        username = request.form['username']
        password = request.form['password']
        if username in users:
            
            return redirect(url_for('signup'))
        users[username] = password
        write_users(users)
        
        return redirect(url_for('login'))
    return render_template('signup.html')


# -------------------------- LOGIN --------------------------
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        users = read_users()
        username = request.form['username']
        password = request.form['password']
        role = request.form['role']

        if users.get(username) == password:
         session['user'] = username
         session['role'] = role
         return redirect(url_for('marketplace'))

        else:
            
            return redirect(url_for('login'))
    return render_template('login.html')


# -------------------------- LOGOUT --------------------------
@app.route('/logout')
def logout():
    session.pop('user', None)
    session.pop('role', None)
    return redirect(url_for('login'))


# -------------------------- MARKETPLACE --------------------------
@app.route('/marketplace')
def marketplace():
    if 'user' not in session:
        return redirect(url_for('login'))

    data = read_data()
    items = data.get("items", [])
    role = session.get('role')

    if role in ['ngo', 'buyer']:
        return render_template('marketplace_restricted.html', items=items, role=role)
    else:
        return render_template('marketplace.html', items=items)


# -------------------------- ADD ITEM --------------------------

@app.route('/add_item', methods=['GET', 'POST'])
def add_item():
    if 'user' not in session:
        
        return redirect(url_for('login'))

    if request.method == 'POST':
        # Load existing data
        data = read_data()

        # Handle image upload
        image_file = request.files.get('image')
        image_filename = None

        if image_file and image_file.filename != '':
            upload_folder = os.path.join('static', 'uploads')
            os.makedirs(upload_folder, exist_ok=True)

            filename = secure_filename(image_file.filename)
            image_path = os.path.join(upload_folder, filename)
            image_file.save(image_path)

            image_filename = filename  # store only filename (not full path)

        # Create new item dictionary
        item = {
            'id': len(data['items']) + 1,
            'name': request.form['name'],
            'description': request.form['description'],
            'quantity': request.form['quantity'],
            'price': request.form['price'],
            'location': request.form['location'],
            'image': image_filename,
            'owner': session['user']
        }

        # Add item and save
        data['items'].append(item)
        write_data(data)

       
        return redirect(url_for('marketplace'))

    return render_template('add_item.html')

# -------------------------- DELETE ITEM --------------------------
@app.route('/delete_item/<int:item_id>', methods=['POST'])
def delete_item(item_id):
    if 'user' not in session:
       
        return redirect(url_for('login'))

    data = read_data()
    new_items = [item for item in data['items'] if item['id'] != item_id]

    if len(new_items) == len(data['items']):
        pass
    else:
        data['items'] = new_items
        write_data(data)

    return redirect(url_for('marketplace'))


# -------------------------- BUY ITEM --------------------------
@app.route('/buy_item/<int:item_id>', methods=['POST'])
def buy_item(item_id):
    if 'user' not in session:
        return redirect(url_for('login'))

    data = read_data()
    notifications = read_notifications()
    buyer = session.get('user')
    role = session.get('role')
    item_to_buy = None

    for item in data['items']:
        if item['id'] == item_id:
            item_to_buy = item
            break

    if not item_to_buy:
        return redirect(url_for('marketplace'))

    location = item_to_buy.get('location', 'Unknown Location')

    # Create notification
    quantity = item_to_buy.get('quantity', 'unknown quantity')
    notifications.append({
        "owner": item_to_buy['owner'],
        "message": f"{buyer} has ordered {quantity} of {item_to_buy['name']} from {item_to_buy['location']}.",
        "read": False
    })
    write_notifications(notifications)

    # Remove bought item
    data['items'] = [item for item in data['items'] if item['id'] != item_id]
    write_data(data)

    # ✅ Pass a query parameter to trigger alert
    return redirect(url_for('marketplace', ordered=item_to_buy['location']))


# -------------------------- NOTIFICATIONS --------------------------
@app.route('/notification')
def notifications():
    if 'user' not in session:
        return redirect(url_for('login'))

    user = session.get('user')
    role = session.get('role')

    if role not in ['farmer', 'business']:
        
        return redirect(url_for('marketplace'))

    all_notifications = read_notifications()
    user_notifications = [n for n in all_notifications if n['owner'] == user]
    return render_template('notifications.html', notifications=user_notifications)


@app.route('/clear_notifications', methods=['POST'])
def clear_notifications():
    user = session.get('user')
    all_notifications = read_notifications()
    remaining = [n for n in all_notifications if n['owner'] != user]
    write_notifications(remaining)
    return redirect(url_for('notifications'))


# -------------------------- OTHER ROUTES --------------------------
@app.route('/education')
def education():
    return render_template('education.html')


@app.route('/crisis')
def crisis():
    return render_template('crisis.html')


# -------------------------- MAIN --------------------------
if __name__ == '__main__':
    app.run(debug=True)
