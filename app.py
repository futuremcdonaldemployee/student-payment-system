from flask import Flask, render_template, request, redirect, flash, url_for
from flask_mail import Mail, Message
from flask_wtf.csrf import CSRFProtect
import firebase_admin
from firebase_admin import credentials, firestore
import os
from dotenv import load_dotenv
import json
from datetime import datetime

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY') or 'default_secret_key'  # Load secret key with a default option

# Enable CSRF protection
csrf = CSRFProtect(app)

# Email configuration
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.getenv('EMAIL_USER')
app.config['MAIL_PASSWORD'] = os.getenv('EMAIL_PASS')

mail = Mail(app)

# Initialize Firebase
try:
    # Load the credentials from the environment variable
    firebase_key = json.loads(os.getenv('FIREBASE_KEY'))  # Use the loaded JSON directly
    cred = credentials.Certificate(firebase_key)  # Create credentials
    firebase_admin.initialize_app(cred)  # Initialize Firebase
    db = firestore.client()  # Firestore database client
    print("Firebase successfully connected.")
except Exception as e:
    print(f"Error initializing Firebase: {e}")

# Initial balance
initial_balance = 8366.00

# Installments and penalties info
installments_info = {
    "1081.50": {"due_date": "2024-08-14", "penalty_rate": 0.05},
    "1733.13_1st": {"due_date": "2024-09-02", "penalty_rate": 0.05},
    "1733.13_2nd": {"due_date": "2024-09-16", "penalty_rate": 0.05},
    "1733.13_3rd": {"due_date": "2024-10-01", "penalty_rate": 0.05},
    "1733.13_4th": {"due_date": "2024-10-16", "penalty_rate": 0.05},
    "733.60": {"due_date": "2024-10-30", "penalty_rate": 0.05},
}

def calculate_penalties(installments):
    """Calculate total penalties for selected installments."""
    penalties = 0.0
    current_date = datetime.now().date()

    for installment in installments:
        # Split to get the base installment amount
        value = installment.split('_')[0]  # Get the base amount, e.g., '1733.13'
        
        # Check if the value is in installments_info
        if value in installments_info:
            due_date = datetime.strptime(installments_info[value]["due_date"], "%Y-%m-%d").date()
            # Calculate penalties if the current date is past the due date
            if current_date > due_date:
                # Calculate the days overdue
                days_overdue = (current_date - due_date).days
                # Calculate penalty based on the amount and rate
                penalty_amount = float(value) * installments_info[value]["penalty_rate"] * days_overdue
                penalties += penalty_amount
        else:
            print(f"Warning: {value} not found in installments_info.")  # Log for debugging

    return round(penalties, 2)  # Round penalties to 2 decimal places

def send_confirmation_email(name, student_number, email, payment_details, total_due, penalties, balance):
    """Send payment confirmation email."""
    total_paid = total_due + penalties

    msg = Message("Payment Confirmation", sender=os.getenv('EMAIL_USER'), recipients=[email])
    msg.body = f"""
    Dear {name},

    Thank you for your payment. Here are your details:

    Student Number: {student_number}
    Installments Paid: {', '.join(payment_details)}

    Total Due: {total_due:.2f} PHP
    Penalties: {penalties:.2f} PHP
    Total Paid (including penalties): {total_paid:.2f} PHP
    Remaining Balance: {balance:.2f} PHP

    Regards,
    ICCT Colleges
    """
    mail.send(msg)

def save_payment_to_firestore(name, student_number, email, total_due, penalties, balance):
    """Save payment details to Firestore."""
    payment_data = {
        "name": name,
        "student_number": student_number,
        "email": email,
        "total_due": total_due,
        "penalties": penalties,
        "balance": balance,
        "timestamp": datetime.now()
    }
    try:
        db.collection('payments').add(payment_data)
        print("Payment successfully saved to Firestore.")
    except Exception as e:
        print(f"Error saving payment to Firestore: {e}")

@app.route('/')
def index():
    """Render the home page."""
    return render_template('index.html')

@app.route('/pay', methods=['POST'])
def pay():
    """Handle payment submission."""
    name = request.form.get('name', '').strip()
    student_number = request.form.get('student_number', '').strip()
    email = request.form.get('email', '').strip()
    selected_installments = request.form.getlist('installments')

    if not name or not student_number or not email:
        flash('Please fill in all required fields.', 'error')
        return redirect(url_for('index'))

    if not selected_installments:
        flash('Please select at least one installment before submitting.', 'error')
        return redirect(url_for('index'))

    total_due = sum(float(installment.split('_')[0]) for installment in selected_installments)
    penalties = calculate_penalties(selected_installments)

    total_payments_made = total_due + penalties
    balance = max(initial_balance - total_payments_made, 0)
    balance = round(balance, 2)

    # Send email and save payment details
    send_confirmation_email(name, student_number, email, selected_installments, total_due, penalties, balance)
    save_payment_to_firestore(name, student_number, email, total_due, penalties, balance)

    flash('Payment processed successfully. Confirmation email sent.', 'success')
    return redirect(url_for('payments'))  # Redirect to payments page after processing

@app.route('/payments')
def payments():
    """Render the payments page with payment records."""
    try:
        # Fetch payment records from Firestore
        payments_ref = db.collection('payments')
        payment_records = payments_ref.order_by('timestamp', direction=firestore.Query.DESCENDING).stream()
        
        payments = []
        for record in payment_records:
            payment_data = record.to_dict()  # Convert Firestore document to a dictionary
            payment_data['id'] = record.id  # Add the document ID if needed
            payments.append(payment_data)

        return render_template('payments.html', payments=payments)
    except Exception as e:
        print(f"Error retrieving payments: {e}")
        flash("Error retrieving payment records.", 'error')
        return redirect(url_for('index'))

if __name__ == "__main__":
    app.run(debug=True)
