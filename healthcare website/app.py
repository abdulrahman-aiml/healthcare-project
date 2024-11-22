from flask import Flask, request, render_template, redirect, url_for, jsonify, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
from model import health_care_query
import numpy as np, base64
import pymysql
import mysql
import random
import os
import mysql.connector
from mysql.connector import Error
import logging

app = Flask(__name__)

app.secret_key = os.environ.get('SECRET_KEY', 'your_default_secret_key_here')


# MySQL Configuration
db_config = {
    'host': '127.0.0.1',
    'user': 'root',
    'password': os.environ.get('DB_CRED'),
    'database': 'healthcare',
    'charset': 'utf8mb4',
    'cursorclass': pymysql.cursors.DictCursor,  # pymysql-specific
}

def get_db_connection():
    try:
        connection = pymysql.connect(**db_config)
        return connection
    except pymysql.MySQLError as e:
        print(f"Error connecting to the database: {e}")
        return None

# Home Page
@app.route('/')
def index():
    return render_template('index.html')

# Signup Route
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        fullname = request.form.get('fullname')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        # Basic validation
        if not fullname or not email or not password or not confirm_password:
            flash('Please fill in all fields.', 'danger')
            return redirect(url_for('signup'))

        # Check if passwords match
        if password != confirm_password:
            flash('Passwords do not match. Please try again.', 'danger')
            return redirect(url_for('signup'))

        # Hash the password
        hashed_password = generate_password_hash(password)

        # Store data in the database
        connection = get_db_connection()
        if connection is None:
            flash("Database connection failed. Please try again.", "danger")
            return redirect(url_for('signup'))

        cursor = connection.cursor()
        try:
            # Insert user into the database
            cursor.execute(
                '''INSERT INTO users (fullname, email, password) VALUES (%s, %s, %s)''',
                (fullname, email, hashed_password)
            )
            connection.commit()
            flash('Registration successful! You can now log in.', 'success')
            return redirect(url_for('login'))
        except pymysql.err.IntegrityError:
            flash('Email already exists. Please use a different email.', 'danger')
            return redirect(url_for('signup'))
        except pymysql.MySQLError as e:
            flash(f"An error occurred: {e}", 'danger')
            return redirect(url_for('signup'))
        finally:
            cursor.close()
            connection.close()

    return render_template('signup.html')

# Login Route
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        # Basic validation
        if not email or not password:
            flash('Please fill in all fields.', 'danger')
            return redirect(url_for('login'))

        # Database connection
        connection = get_db_connection()
        if connection is None:
            flash("Database connection failed. Please try again.", "danger")
            return redirect(url_for('login'))

        cursor = connection.cursor()
        try:
            # Check if the user exists
            cursor.execute('SELECT * FROM users WHERE email = %s', (email,))
            user = cursor.fetchone()

            if user and check_password_hash(user['password'], password):
                # Store session data
                session['logged_in'] = True
                session['user_id'] = user['id']
                session['user_email'] = user['email']

                flash('Login successful!', 'success')
                return redirect(url_for('book'))
            else:
                flash('Login failed. Incorrect email or password.', 'danger')
                return redirect(url_for('login'))
        except pymysql.MySQLError as e:
            flash(f"An error occurred: {e}", 'danger')
            return redirect(url_for('login'))
        finally:
            cursor.close()
            connection.close()

    return render_template('login.html')

# Book Appointment Page
@app.route('/book', methods=['GET', 'POST'])
def book():
    if request.method == 'POST':
        patient_name = request.form['patient_name']
        appointment_date = request.form['appointment_date']
        reason = request.form['reason']
        
        # Insert into the database
        connection = pymysql.connect(**db_config)
        try:
            with connection.cursor() as cursor:
                query = """
                INSERT INTO appointments (patient_name, appointment_date, reason) 
                VALUES (%s, %s, %s)
                """
                cursor.execute(query, (patient_name, appointment_date, reason))
            connection.commit()
        finally:
            connection.close()
        
        return redirect(url_for('appointments'))
    
    return render_template('book.html')

# Reschedule Appointment Page
@app.route('/reschedule', methods=['GET', 'POST'])
def reschedule():
    if request.method == 'POST':
        appointment_id = request.form['appointment_id']
        new_date = request.form['new_date']
        
        # Update the appointment in the database
        connection = pymysql.connect(**db_config)
        try:
            with connection.cursor() as cursor:
                query = """
                UPDATE appointments 
                SET appointment_date = %s 
                WHERE id = %s
                """
                cursor.execute(query, (new_date, appointment_id))
            connection.commit()
        finally:
            connection.close()
        
        return redirect(url_for('appointments'))
    
    return render_template('reschedule.html')

# View All Appointments
@app.route('/appointments')
def appointments():
    connection = pymysql.connect(**db_config)
    try:
        with connection.cursor() as cursor:
            # Select only relevant columns to avoid fetching unnecessary data like created_at
            query = "SELECT id,patient_name, appointment_date, reason FROM appointments ORDER BY appointment_date"
            cursor.execute(query)
            appointments = cursor.fetchall()
    finally:
        connection.close()
    
    # Pass the fetched appointments data to the template
    return render_template('appointments.html', appointments=appointments)

@app.route('/update_status', methods=['POST'])
def update_status():
    try:
        # Get appointment ID and status from the request form
        appointment_id = request.form.get('appointment_id')
        status = request.form.get('status')

        # Validate the inputs
        if not appointment_id or not status:
            return jsonify({
                'status': 'error',
                'message': 'Invalid request. Please provide valid appointment ID and status.'
            }), 400

        # Establish a database connection
        connection = get_db_connection()
        if not connection:
            return jsonify({
                'status': 'error',
                'message': 'Error connecting to the database.'
            }), 500

        with connection.cursor() as cursor:
            # Fetch the current status of the appointment
            cursor.execute("SELECT appointment_status FROM appointments WHERE id = %s", (appointment_id,))
            current_status = cursor.fetchone()

            if not current_status:
                return jsonify({
                    'status': 'error',
                    'message': f"Appointment with ID {appointment_id} not found."
                }), 404

            # Check if the status is already the same
            if current_status['appointment_status'] == status:
                return jsonify({
                    'status': 'no_change',
                    'message': 'No changes made. The status is already set to the requested value.'
                })

            # Update the status in the database
            cursor.execute(
                "UPDATE appointments SET appointment_status = %s WHERE id = %s",
                (status, appointment_id)
            )
            connection.commit()

            # Fetch the updated appointment details
            cursor.execute(
                "SELECT id, patient_name, appointment_date, reason, appointment_status "
                "FROM appointments WHERE id = %s",
                (appointment_id,)
            )
            updated_appointment = cursor.fetchone()

            if updated_appointment:
                return jsonify({
                    'status': updated_appointment['appointment_status'],  # appointment_status
                    'appointment': {
                        'id': updated_appointment['id'],
                        'patient_name': updated_appointment['patient_name'],
                        'appointment_date': updated_appointment['appointment_date'],
                        'reason': updated_appointment['reason']
                    }
                })
            else:
                return jsonify({
                    'status': 'error',
                    'message': 'Failed to fetch updated appointment details.'
                }), 500

    except Exception as e:
        # Log the error for debugging purposes
        print(f"Error updating appointment status: {e}")
        return jsonify({
            'status': 'error',
            'message': f'Error updating appointment status. Please try again later. Details: {str(e)}'
        }), 500

    finally:
        # Ensure the connection is closed
        if connection:
            connection.close()

@app.route('/chatbot')
def chatbot():
    return render_template('chatbot.html')

@app.route('/generate-response', methods=['POST'])
def generate_response():
    try:
        # Get JSON data from the request (user input)
        data = request.get_json()
        user_input = data.get('user_input')

        # Check if user_input is not empty
        if user_input:
            # Check if user input is a greeting
            salutation_response = [
                "You're welcome", 
                "My pleasure", 
                "It's my job", 
                "Happy to help", 
                "No problem", 
                "Glad I could assist", 
                "Anytime", 
                "It was nothing", 
                "I'm here for you", 
                "Always happy to help"
            ]

            salutations = ['thanks', 'nice', 'good', 'wonderful', 'excellent', 'awesome', 'great','perfect']
            greetings = ["hi", "hello", "hey", "greetings", "good morning", "good evening", "howdy"]
            
            if any(greeting in user_input.lower() for greeting in greetings):
                answer = "Hello! How can I assist you today?"
            # Check if it's a salutation message
            elif any(salutation in user_input.lower() for salutation in salutations):
                answer = random.choice(salutation_response) + '. Let me know if you need anything else!'
            else:
                # Otherwise, treat it as a text generation request
                answer = health_care_query(user_input)
        else:
            answer = "Sorry, I didn't get that. Can you please rephrase?"

        # Return the chatbot response as JSON
        return jsonify({'response': answer})
    
    except Exception as e:
        # Handle any exceptions and return a generic error message
        return jsonify({'response': "An error occurred. Please try again later."})

@app.route('/medstore')
def medstore():
    return render_template('medstore.html')

@app.route('/wishlist')
def wishlist():
    return render_template('wishlist.html')

@app.route('/order', methods=['POST', 'GET'])
def place_order():
    if request.method == 'POST':
        try:
            # Extract customer and payment form data from the POST request
            medicine_name = request.form.get('medicineName', '').strip()
            medicine_description = request.form.get('medicineDescription', '').strip()
            try:
                medicine_price = float(request.form.get('medicinePrice', 0.0))
            except ValueError:
                medicine_price = 0.0

            customer_name = request.form.get('customerName', '').strip()
            shipping_address = request.form.get('shippingAddress', '').strip()
            payment_method = request.form.get('paymentMethod', '').strip()

            # Handle UPI-specific fields
            upi_method = request.form.get('upiMethod', None) if payment_method == 'upi' else None
            upi_id = request.form.get('upiId', None) if payment_method == 'upi' else None

            # Handle card-specific fields
            card_type = request.form.get('cardType', None) if payment_method == 'card' else None
            card_number = request.form.get('cardNumber', None) if payment_method == 'card' else None
            expiry_date = request.form.get('expiryDate', None) if payment_method == 'card' else None
            cvv = request.form.get('cvv', None) if payment_method == 'card' else None

            # Validate required fields
            if not all([medicine_name, medicine_description, medicine_price, customer_name, shipping_address, payment_method]):
                flash('Please fill in all required fields.', 'danger')
                return render_template('order.html')

            # Connect to the database
            connection = get_db_connection()

            if connection:
                try:
                    with connection.cursor() as cursor:
                        # Insert the medicine data into the 'medicine' table
                        cursor.execute(
                            "INSERT INTO Medicine (name, description, price) VALUES (%s, %s, %s)",
                            (medicine_name, medicine_description, medicine_price)
                        )
                        connection.commit()
                        medicine_id = cursor.lastrowid  # Get the ID of the inserted medicine

                        # Insert customer data into the 'customer' table
                        cursor.execute(
                            "INSERT INTO Customer (name, address) VALUES (%s, %s)",
                            (customer_name, shipping_address)
                        )
                        connection.commit()
                        customer_id = cursor.lastrowid  # Get the ID of the inserted customer

                        # Handle payment data insertion based on payment method
                        payment_id = None
                        if payment_method == 'upi':
                            cursor.execute(
                                """
                                INSERT INTO Payment (payment_method, upi_method, upi_id, customer_id)
                                VALUES (%s, %s, %s, %s)
                                """,
                                (payment_method, upi_method, upi_id, customer_id)
                            )
                            connection.commit()
                            payment_id = cursor.lastrowid
                        elif payment_method == 'card':
                            cursor.execute(
                                """
                                INSERT INTO Payment (payment_method, card_type, card_number, expiry_date, cvv, customer_id)
                                VALUES (%s, %s, %s, %s, %s, %s)
                                """,
                                (payment_method, card_type, card_number, expiry_date, cvv, customer_id)
                            )
                            connection.commit()
                            payment_id = cursor.lastrowid
                        elif payment_method == 'cod':
                            cursor.execute(
                                """
                                INSERT INTO Payment (payment_method, customer_id)
                                VALUES (%s, %s)
                                """,
                                (payment_method, customer_id)
                            )
                            connection.commit()
                            payment_id = cursor.lastrowid

                        # Insert the order into the 'orders' table, linking to the medicine and payment
                        cursor.execute(
                            """
                            INSERT INTO Orders (medicine_id, customer_id, payment_id, order_status)
                            VALUES (%s, %s, %s, 'pending')
                            """,
                            (medicine_id, customer_id, payment_id)
                        )
                        connection.commit()

                        return jsonify({'success': True, 'deliveryTime': 'Your order will be delivered within 3-5 business days.'})
                        # flash('Your order has been placed successfully!', 'success')
                        # return redirect(url_for('medstore'))  # Redirect to home page after success

                except pymysql.MySQLError as e:
                    connection.rollback()  # Rollback in case of an error
                    flash(f"An error occurred while processing your order: {e}", 'danger')
                    return jsonify({'success': False})
                finally:
                    connection.close()  # Ensure connection is always closed

            else:
                flash('Failed to connect to the database', 'danger')
                return jsonify({'success': False})

        except Exception as e:
            flash(f"An error occurred: {e}", 'danger')
            return jsonify({'success': False})

    # Fetch the medicine details from the query parameters if available (using request.args.get)
    medicine_name = request.args.get('medicine', None)
    medicine_description = request.args.get('description', None)
    medicine_price = request.args.get('price', None)

    # If medicine details are available in query params, populate them in the form
    if medicine_name and medicine_description and medicine_price:
        try:
            medicine_price = float(medicine_price)
            return render_template('order.html', medicine_name=medicine_name, medicine_description=medicine_description, medicine_price=medicine_price)
        except ValueError:
            flash('Invalid price value provided.', 'danger')
            return render_template('order.html')

    return render_template('order.html')  # Render order form if any error occurs or no query params

@app.route('/logout')
def logout():
    # Clear the session to log out the user
    session.clear()
    return redirect(url_for('login'))  # Redirect to login page after logout

if __name__=="__main__":
    app.run(debug=True)