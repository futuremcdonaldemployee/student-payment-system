from flask import Flask, render_template, request, redirect, flash, url_for
from flask_mail import Mail, Message
from flask_wtf.csrf import CSRFProtect
import os
import re
from dotenv import load_dotenv
from datetime import datetime

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY') or 'default_secret_key'

# Enable CSRF protection
csrf = CSRFProtect(app)

# Email configuration
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.getenv('EMAIL_USER')
app.config['MAIL_PASSWORD'] = os.getenv('EMAIL_PASS')
app.config['MAIL_DEFAULT_SENDER'] = os.getenv('EMAIL_USER')

mail = Mail(app)

# In-memory storage for payment records
payments = []

# Initial balance
initial_balance = 8366.00

# Installment and penalty information
installments_info = {
    "1030.00": {"due_date": "2024-08-14", "penalty_rate": 0.05},
    "1650.60": {"due_date": "2024-09-02", "penalty_rate": 0.05},
    "1650.60": {"due_date": "2024-09-16", "penalty_rate": 0.05},
    "1650.60": {"due_date": "2024-10-01", "penalty_rate": 0.05},
    "1650.60": {"due_date": "2024-10-16", "penalty_rate": 0.05},
    "733.60": {"due_date": "2024-10-30", "penalty_rate": 0.05},
}

# Validate email format
def is_valid_email(email):
    return re.match(r"[^@]+@[^@]+\.[^@]+", email)

# Calculate penalties for overdue installments
def calculate_penalties(installments):
    penalties = 0.0
    current_date = datetime.now().date()

    for installment in installments:
        value = installment.split('_')[0]
        if value in installments_info:
            due_date = datetime.strptime(installments_info[value]["due_date"], "%Y-%m-%d").date()
            if current_date > due_date:
                penalty_amount = float(value) * installments_info[value]["penalty_rate"]
                penalties += penalty_amount

    return round(penalties, 2)

# Send confirmation email
def send_confirmation_email(name, student_number, email, payment_details, total_due, penalties, balance):
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

# Save payment details to memory
def save_payment_to_memory(name, student_number, email, total_due, penalties, balance):
    payment = {
        "name": name,
        "student_number": student_number,
        "email": email,
        "total_due": total_due,
        "penalties": penalties,
        "balance": balance,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    payments.append(payment)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/pay', methods=['POST'])
def pay():
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

    if not is_valid_email(email):
        flash('Please provide a valid email address.', 'error')
        return redirect(url_for('index'))

    total_due = sum(float(installment.split('_')[0]) for installment in selected_installments)
    penalties = calculate_penalties(selected_installments)
    total_payments_made = total_due + penalties
    balance = max(initial_balance - total_payments_made, 0)
    balance = round(balance, 2)

    payment_summary = {
        "total_due": f"{total_due:.2f}",
        "penalties": f"{penalties:.2f}",
        "total_paid": f"{total_payments_made:.2f}",
        "remaining_balance": f"{balance:.2f}",
    }

    try:
        send_confirmation_email(name, student_number, email, selected_installments, total_due, penalties, balance)
        save_payment_to_memory(name, student_number, email, total_due, penalties, balance)
        flash('Payment processed successfully. Confirmation email sent.', 'success')
    except Exception as e:
        flash(f'An error occurred while processing your payment: {e}', 'error')

    return render_template('index.html', payment_summary=payment_summary)

if __name__ == "__main__":
    app.run(debug=True)
