from flask import Flask, request, render_template, redirect, url_for, jsonify
import pymysql
import os
from model import health_care_query
import random

app = Flask(__name__)

# MySQL Configuration
db_config = {
    'host': '127.0.0.1',
    'user': 'root',
    'password': os.environ.get('DB_CRED'),
    'database': 'healthcare',
    'charset': 'utf8mb4',
    'cursorclass': pymysql.cursors.DictCursor,  # pymysql-specific
}

# Home Page
@app.route('/')
def index():
    return render_template('index.html')

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
        
        return redirect(url_for('index'))
    
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

@app.route('/order')
def order():
    return render_template('order.html')

if __name__ == '__main__':
    app.run(debug=True)
