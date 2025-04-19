from flask import Flask, render_template, request, jsonify, redirect, url_for
import sqlite3
from datetime import datetime
import calendar

app = Flask(__name__)

# Database initialization
def init_db():
    conn = sqlite3.connect('attendance.db')
    c = conn.cursor()
    
    # Create employees table
    c.execute('''CREATE TABLE IF NOT EXISTS employees
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                 name TEXT NOT NULL,
                 hourly_rate REAL NOT NULL)''')
    
    # Create attendance table
    c.execute('''CREATE TABLE IF NOT EXISTS attendance
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                 employee_id INTEGER NOT NULL,
                 action TEXT NOT NULL,
                 timestamp DATETIME NOT NULL,
                 FOREIGN KEY (employee_id) REFERENCES employees (id))''')
    
    # Insert sample employees if none exist
    c.execute("SELECT COUNT(*) FROM employees")
    if c.fetchone()[0] == 0:
        sample_employees = [
            ('John Doe', 15.00),
            ('Jane Smith', 18.50),
            ('Mike Johnson', 20.00)
        ]
        c.executemany("INSERT INTO employees (name, hourly_rate) VALUES (?, ?)", sample_employees)
    
    conn.commit()
    conn.close()

init_db()

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/api/employees', methods=['GET'])
def get_employees():
    conn = sqlite3.connect('attendance.db')
    c = conn.cursor()
    c.execute("SELECT id, name FROM employees")
    employees = [{'id': row[0], 'name': row[1]} for row in c.fetchall()]
    conn.close()
    return jsonify(employees)

@app.route('/api/attendance', methods=['POST'])
def record_attendance():
    data = request.json
    employee_id = data['employee_id']
    action = data['action']
    
    conn = sqlite3.connect('attendance.db')
    c = conn.cursor()
    c.execute("INSERT INTO attendance (employee_id, action, timestamp) VALUES (?, ?, ?)",
              (employee_id, action, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
    conn.commit()
    conn.close()
    
    return jsonify({'status': 'success'})

@app.route('/api/report/<int:employee_id>/<int:year>/<int:month>', methods=['GET'])
def get_monthly_report(employee_id, year, month):
    conn = sqlite3.connect('attendance.db')
    c = conn.cursor()
    
    # Get employee details
    c.execute("SELECT name, hourly_rate FROM employees WHERE id = ?", (employee_id,))
    employee = c.fetchone()
    if not employee:
        return jsonify({'error': 'Employee not found'}), 404
    
    # Get all attendance records for the month
    first_day = f"{year}-{month:02d}-01"
    last_day = f"{year}-{month:02d}-{calendar.monthrange(year, month)[1]}"
    
    c.execute('''SELECT date(timestamp) as date, 
                        time(timestamp) as time,
                        action 
                 FROM attendance 
                 WHERE employee_id = ? 
                 AND date(timestamp) BETWEEN ? AND ?
                 ORDER BY timestamp''', 
                 (employee_id, first_day, last_day))
    
    records = c.fetchall()
    
    # Process records into days
    days = {}
    for date, time, action in records:
        if date not in days:
            days[date] = {'check_in': None, 'check_out': None}
        if action == 'check_in':
            days[date]['check_in'] = time
        elif action == 'check_out':
            days[date]['check_out'] = time
    
    # Calculate hours per day
    report = []
    total_hours = 0
    for date, times in days.items():
        if times['check_in'] and times['check_out']:
            in_time = datetime.strptime(times['check_in'], '%H:%M:%S')
            out_time = datetime.strptime(times['check_out'], '%H:%M:%S')
            hours = (out_time - in_time).total_seconds() / 3600
            total_hours += hours
            report.append({
                'date': date,
                'check_in': times['check_in'],
                'check_out': times['check_out'],
                'hours': round(hours, 2)
            })
        else:
            report.append({
                'date': date,
                'check_in': times['check_in'],
                'check_out': times['check_out'],
                'hours': 0
            })
    
    conn.close()
    
    return jsonify({
        'employee_id': employee_id,
        'employee_name': employee[0],
        'hourly_rate': employee[1],
        'month': f"{year}-{month:02d}",
        'total_hours': round(total_hours, 2),
        'total_pay': round(total_hours * employee[1], 2),
        'days': report
    })

if __name__ == '__main__':
    app.run(debug=True)