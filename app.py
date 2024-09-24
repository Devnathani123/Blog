from flask import Flask, request, redirect, url_for, render_template_string, session
import sqlite3
import uuid
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from hashlib import sha256
from datetime import datetime, timedelta

app = Flask(__name__)
app.secret_key = 'supersecretkey'  # Needed for sessions

# Email configuration
smtp_server = 'smtp.gmail.com'
smtp_port = 587
smtp_user = 'devnathani5697@gmail.com'
smtp_password = 'lqco hmvy ohpv njqb'

# Temporary storage for users who haven't verified their email
unverified_users = {}

# Connect to SQLite database
def init_db():
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        email TEXT NOT NULL,
                        password TEXT NOT NULL,
                        verified INTEGER DEFAULT 0)''')
    conn.commit()
    conn.close()

# Function to send verification email
def send_verification_email(to_email, token):
    subject = 'Verify your email address'
    body = f'Click the link to verify your account: http://127.0.0.1:5000/verify/{token}'
    
    msg = MIMEMultipart()
    msg['From'] = smtp_user
    msg['To'] = to_email
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))
    
    try:
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_password)
            server.sendmail(smtp_user, to_email, msg.as_string())
            print('Verification email sent successfully')
    except Exception as e:
        print(f'Failed to send email: {e}')

# Route for signup
@app.route('/', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        token = str(uuid.uuid4())  # Generate a unique token for verification
        signup_time = datetime.now()  # Record the time when the user signs up
        
        # Store user data in temporary storage until verified
        hashed_password = sha256(password.encode()).hexdigest()
        unverified_users[token] = {'email': email, 'password': hashed_password, 'signup_time': signup_time}

        # Store session info to track the user
        session['token'] = token
        session['email'] = email
        
        # Send verification email
        send_verification_email(email, token)
        
        # Display the countdown timer on the signup page
        return render_template_string('''
        <p>A verification email has been sent to {{ email }}. Please verify your email within 60 seconds.</p>
        <p id="timer"></p>

        <script>
        var timeLeft = 60;
        var timer = document.getElementById('timer');
        var countdown = setInterval(function() {
            if (timeLeft <= 0) {
                clearInterval(countdown);
                timer.innerHTML = "Your verification link has expired.";
            } else {
                timer.innerHTML = "Time remaining: " + timeLeft + " seconds.";
            }
            timeLeft -= 1;
        }, 1000);
        </script>
        ''', email=email)

    return render_template_string('''
    <form method="POST">
        Email: <input type="email" name="email"><br>
        Password: <input type="password" name="password"><br>
        <input type="submit" value="Sign Up">
    </form>
    ''')

# Route for verifying email
@app.route('/verify/<token>')
def verify(token):
    if token in unverified_users:
        user_data = unverified_users[token]
        current_time = datetime.now()
        time_difference = current_time - user_data['signup_time']
        
        if time_difference > timedelta(seconds=60):
            # Token has expired
            del unverified_users[token]
            return 'Your verification link has expired. Please sign up again.'
        
        # Store verified user data in the database
        conn = sqlite3.connect('users.db')
        cursor = conn.cursor()
        cursor.execute('INSERT INTO users (email, password, verified) VALUES (?, ?, ?)', 
                       (user_data['email'], user_data['password'], 1))
        conn.commit()
        conn.close()

        # Remove the user from the unverified list and mark as verified
        del unverified_users[token]
        session['verified'] = True

        return f"Your account ({user_data['email']}) has been verified successfully."
    else:
        return 'Invalid or expired token.'

# Route for login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        hashed_password = sha256(password.encode()).hexdigest()
        
        conn = sqlite3.connect('users.db')
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE email=? AND password=?', (email, hashed_password))
        user = cursor.fetchone()
        
        if user and user[3] == 1:  # Check if user is verified
            session['logged_in'] = True
            session['email'] = email
            session['password'] = password
            return f"Login successful. Welcome, {email}!"
        elif user and user[3] == 0:
            return 'Please verify your email before logging in.'
        else:
            return 'Invalid email or password.'
    
    return render_template_string('''
    <form method="POST">
        Email: <input type="email" name="email"><br>
        Password: <input type="password" name="password"><br>
        <input type="submit" value="Login">
    </form>
    ''')

# Route to show email and password for verified users
@app.route('/show_credentials')
def show_credentials():
    if 'logged_in' in session and session.get('verified', False):
        email = session.get('email')
        password = session.get('password')
        return f"Email: {email}<br>Password: {password}"
    else:
        return "You are not verified or not logged in from the same browser."

if __name__ == '__main__':
    init_db()  # Initialize the database
    app.run(debug=True)
