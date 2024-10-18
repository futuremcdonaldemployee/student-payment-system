from flask import Flask, render_template, request
from flask_mail import Mail, Message
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.getenv('EMAIL_USER')
app.config['MAIL_PASSWORD'] = os.getenv('EMAIL_PASS')
mail = Mail(app)

def calculate_penalties(installments):
    penalties = 0.0
    for installment in installments:
        if installment == "1081.50":  # Downpayment
            penalties += 51.50
        elif installment in ["1733.13"]:  # 1st to 4th Installments
            penalties += 82.53
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

    # Get the payment made from the form or set a default value
    payment_made = float(request.form.get('payment_made', 0.0))  # Default to 0.0 if not provided
    balance = total_due - payment_made  # Calculate the balance

    send_confirmation_email(name, student_number, reference_number, email, selected_installments, total_due, penalties, balance)

    return "Payment processed. Confirmation email sent."

if __name__ == "__main__":
    app.run(debug=True)
