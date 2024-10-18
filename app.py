from flask import Flask, render_template, request
from flask_mail import Mail, Message
import os
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

app = Flask(__name__)
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.getenv('EMAIL_USER')
app.config['MAIL_PASSWORD'] = os.getenv('EMAIL_PASS')
mail = Mail(app)

# Define installment due dates and penalties
installments_info = {
    "1081.50": {"due_date": "2024-08-15", "penalty": 51.50},
    "1733.13": {"due_date": "2024-09-03", "penalty": 82.53},
    "1733.13": {"due_date": "2024-09-17", "penalty": 82.53},
    "1733.13": {"due_date": "2024-10-02", "penalty": 82.53},
    "1733.13": {"due_date": "2024-10-17", "penalty": 82.53},
    "733.60": {"due_date": "2024-10-31", "penalty": 0.0},
}

def calculate_penalties(installments):
    penalties = 0.0
    current_date = datetime.now().date()

    for installment in installments:
        due_date = datetime.strptime(installments_info[installment]["due_date"], "%Y-%m-%d").date()
        if current_date > due_date:
            penalties += installments_info[installment]["penalty"]
    
    return penalties

def send_confirmation_email(name, student_number, reference_number, email, payment_details, total_due, penalties, balance):
    msg = Message("Payment Confirmation", sender=os.getenv('EMAIL_USER'), recipients=[email])
    
    msg.body = f"""
    Dear {name},

    Thank you for your payment. Below are your payment details:

    Student Number: {student_number}
    Reference Number: {reference_number}
    Selected Installments: {', '.join(payment_details)}

    Total Amount Due: {total_due} PHP
    Penalties Applied: {penalties} PHP
    Balance: {balance} PHP

    If you have any questions, please contact ICCT Colleges at info@icct.edu.ph or call 270014228.

    Regards,
    ICCT Colleges
    """
    
    mail.send(msg)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/pay', methods=['POST'])
def pay():
    name = request.form['name']
    student_number = request.form['student_number']
    reference_number = request.form['reference_number']
    email = request.form['email']
    selected_installments = request.form.getlist('installments')
    
    total_due = sum(float(installment) for installment in selected_installments)
    penalties = calculate_penalties(selected_installments)

    # Calculate balance: Total due + penalties - payments made
    balance = (total_due + penalties) - total_payments_made

    send_confirmation_email(name, student_number, reference_number, email, selected_installments, total_due, penalties, balance)

    return "Payment processed. Confirmation email sent."

if __name__ == "__main__":
    app.run(debug=True)
