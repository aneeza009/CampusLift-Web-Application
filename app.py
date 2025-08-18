from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from db import get_conn
import pyodbc
import datetime
from datetime import time, datetime


app = Flask(__name__)
app.secret_key = 'dev_123456_supersecret'  # Required for session storage

# Redirect '/' to login page
@app.route('/')
def home():
    return redirect(url_for('login'))

def serialize(obj):
    if isinstance(obj, (time, datetime)):
        return obj.strftime("%H:%M:%S")  # or "%I:%M %p" for 12-hour
    return obj


# ✅ Login route
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        conn = get_conn()  # 🔧 define connection
        email = request.form['email']
        password = request.form['password']

        cursor = conn.cursor()
        cursor.execute("""
            SELECT User_ID, F_Name, Status FROM Users 
            WHERE Email = ? AND Password = ?
        """, (email, password))  # 🛠 fixed missing parentheses
        user = cursor.fetchone()

        if user:
            user_id = user[0]
            fname = user[1]
            status = user[2]

            if status == 'Active':
                session['user_id'] = user_id
                session['user_name'] = fname
                session['email'] = email

                # ✅ Admin check logic added here
                if email.lower() == 'aneeza@campuslift.com':
                    session['admin'] = True
                    flash('Welcome Admin!', 'success')
                    return redirect(url_for('admin_dashboard'))  # make sure this route exists
                else:
                    session['admin'] = False
                    flash('Welcome back!', 'success')
                    return redirect(url_for('dashboard'))

            else:
                flash('Your account is ' + status, 'warning')
        else:
            flash('Invalid email or password', 'danger')

    return render_template('login.html')


# ✅ Register new user
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        conn = get_conn()  # 🔧 FIXED: define connection here
        fname = request.form['fname']
        lname = request.form['lname']
        email = request.form['email']
        password = request.form['password']
        phone = request.form['phone']
        gender = request.form['gender']
        cnic = request.form['cnic']
        status = 'Active'

        try:
            cursor = conn.cursor()
            cursor.execute("""
                EXEC AddUser 
                @FName=?, @LName=?, @Email=?, @Password=?, 
                @Phone=?, @Gender=?, @CNIC=?, @Status=?
            """, fname, lname, email, password, phone, gender, cnic, status)
            conn.commit()
            flash('Registration successful! You may now log in.', 'success')
            return redirect(url_for('login'))

        except Exception as e:
            flash(f"Registration failed: {e}", 'danger')

    return render_template('register.html')

# ✅ User Dashboard
@app.route('/dashboard')
def dashboard():
    if 'user_id' in session:
        conn = get_conn()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT s.Enrollment_No, u.F_Name, s.Department, univ.University_Name, s.Is_Driver
            FROM Student s
            JOIN Users u ON s.User_ID = u.User_ID
            JOIN University univ ON s.University_ID = univ.University_ID
            WHERE s.User_ID = ?
        """, (session['user_id'],))
        
        data = cursor.fetchone()

        if data:
            student = {
                'enrollment': data[0],
                'name': data[1],
                'department': data[2],
                'university': data[3],
                'is_driver': bool(data[4])
            }

            session['is_driver'] = student['is_driver']
            return render_template('dashboard.html', fname=student['name'], student=student, is_driver=student['is_driver'])
        
        else:
            flash("Please complete your student profile first.", "warning")
            return redirect(url_for('complete_profile'))

    return redirect(url_for('login'))


@app.context_processor
def inject_driver_status():
    if 'user_id' in session:
        user_id = session['user_id']
        conn = get_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT Is_Driver FROM Student WHERE User_ID = ?", (user_id,))
        result = cursor.fetchone()
        return dict(is_driver=result and result[0] == 1)
    return dict(is_driver=False)


# ✅ Student Profile
@app.route('/complete_profile', methods=['GET', 'POST'])
def complete_profile():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = get_conn()
    cursor = conn.cursor()

    if request.method == 'POST':
        enrollment = request.form['enrollment']
        university_id = request.form['university']
        department = request.form['department']
        emergency_contact = request.form['emergency']
        is_driver = 1 if request.form.get('is_driver') else 0
        license_no = request.form['license'] if is_driver else None

        try:
            cursor.execute("""
                EXEC RegisterStudent @UserID=?, @Enrollment=?, @UniversityID=?, @Department=?, 
                                     @EmergencyContact=?, @IsDriver=?, @LicenseNo=?, @Verified=1
            """, session['user_id'], enrollment, university_id, department, emergency_contact, is_driver, license_no)
            conn.commit()
            flash("Student profile created!", "success")
            return redirect(url_for('dashboard'))
        except Exception as e:
            flash(f"Failed to save profile: {e}", "danger")

    # GET: Show university list
    cursor.execute("SELECT University_ID, University_Name FROM University WHERE Is_Approved = 1")
    universities = cursor.fetchall()

    return render_template('complete_profile.html', universities=universities)

# ✅ Vehicle Registration
@app.route('/register_vehicle', methods=['GET', 'POST'])
def register_vehicle():
    if 'user_id' not in session:
        flash("Please log in first.", "warning")
        return redirect(url_for('login'))

    user_id = session['user_id']
    conn = get_conn()
    cursor = conn.cursor()

    # 🧠 Check if already a driver
    cursor.execute("SELECT Is_Driver FROM Student WHERE User_ID = ?", (user_id,))
    result = cursor.fetchone()
    is_driver = result and result.Is_Driver == 1

    if request.method == 'POST':
        form = request.form
        license_no = form.get('license_no')

        if not license_no:
            flash("License number is required.", "danger")
            return redirect(url_for('register_vehicle'))

        try:
            if is_driver:
                cursor.execute("UPDATE Student SET License_No = ? WHERE User_ID = ?", (license_no, user_id))
                conn.commit()
            else:
                cursor.execute("UPDATE Student SET License_No = ? WHERE User_ID = ?", (license_no, user_id))
                cursor.execute("EXEC AddVehicle ?, ?, ?, ?, ?, ?", 
                    user_id,
                    form['vehicle_type'],
                    form['plate_no'],
                    form['model'],
                    form['color'],
                    int(form['capacity'])
                )
                cursor.execute("UPDATE Student SET Is_Driver = 1 WHERE User_ID = ?", (user_id,))
                conn.commit()
                flash("You're now registered as a driver!", "success")

            return redirect(url_for('register_vehicle'))

        except Exception as e:
            conn.rollback()
            flash(f"Operation failed: {e}", "danger")

    # 🧾 Fetch vehicle info and license if driver
    vehicle = None
    license_no = None

    if is_driver:
        cursor.execute("""
            SELECT VehicleType, Plate_No, Model, Color, Capacity
            FROM Vehicle
            WHERE User_ID = ? AND Is_Active = 1
        """, (user_id,))
        row = cursor.fetchone()
        if row:
            vehicle = {
                'VehicleType': row.VehicleType,
                'Plate_No': row.Plate_No,
                'Model': row.Model,
                'Color': row.Color,
                'Capacity': row.Capacity
            }

        cursor.execute("SELECT License_No FROM Student WHERE User_ID = ?", (user_id,))
        lic_row = cursor.fetchone()
        if lic_row:
            license_no = lic_row.License_No

    return render_template("register_vehicle.html", is_driver=is_driver, vehicle=vehicle, license_no=license_no)

@app.route('/update_vehicle', methods=['POST'])
def update_vehicle():
    if 'user_id' not in session:
        flash("Please log in first.", "warning")
        return redirect(url_for('login'))

    user_id = session['user_id']
    form = request.form

    license_no = form.get('license_no')
    vehicle_type = form.get('vehicle_type')
    plate_no = form.get('plate_no')
    model = form.get('model')
    color = form.get('color')
    capacity = form.get('capacity')

    # Validate capacity and convert to int safely
    try:
        capacity = int(capacity)
    except (ValueError, TypeError):
        flash("Capacity must be a number.", "danger")
        return redirect(url_for('register_vehicle'))

    # Make sure nothing is empty
    if not all([license_no, vehicle_type, plate_no, model, color, capacity]):
        flash("All fields must be filled to update vehicle.", "danger")
        return redirect(url_for('register_vehicle'))

    try:
        conn = get_conn()
        cursor = conn.cursor()

        # Update license
        cursor.execute("UPDATE Student SET License_No = ? WHERE User_ID = ?", (license_no, user_id))

        # Deactivate old vehicle
        cursor.execute("UPDATE Vehicle SET Is_Active = 0 WHERE User_ID = ? AND Is_Active = 1", (user_id,))

        # Insert new vehicle
        cursor.execute("""
            INSERT INTO Vehicle (User_ID, VehicleType, Plate_No, Model, Color, Capacity, Is_Active)
            VALUES (?, ?, ?, ?, ?, ?, 1)
        """, (user_id, vehicle_type, plate_no, model, color, capacity))

        conn.commit()
        flash("Vehicle details updated successfully!", "success")

    except Exception as e:
        conn.rollback()
        flash(f"Failed to update vehicle info: {e}", "danger")

    return redirect(url_for('register_vehicle'))

@app.route('/offer_ride', methods=['GET', 'POST'])
def offer_ride():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = get_conn()
    cursor = conn.cursor()

    if request.method == 'POST':
        try:
            # 🌍 Form data
            start_coords = request.form.get("start_coords")
            end_coords = request.form.get("end_coords")
            start_address = request.form.get("start_address")
            end_address = request.form.get("end_address")
            ride_date = request.form.get("ride_date")
            ride_time = request.form.get("ride_time")
            vehicle_id = int(request.form.get("vehicle_id"))
            seats = int(request.form.get("seats"))
            fare = float(request.form.get("fare") or 0)

            # 🕐 Parse time & estimate arrival
            ride_time_obj = datetime.strptime(ride_time, "%H:%M")
            est_arrival = (ride_time_obj + timedelta(hours=1)).strftime("%H:%M")

            # 📍 Parse coordinates
            start_lat, start_lon = map(float, start_coords.split(','))
            end_lat, end_lon = map(float, end_coords.split(','))

            # 🧭 Insert Start Location (✅ Fixed Lat/Lon)
            cursor.execute("""
                INSERT INTO Location (Address, Lat, Lon)
                OUTPUT INSERTED.Location_ID
                VALUES (?, ?, ?)
            """, start_address, start_lat, start_lon)
            pickup_id = cursor.fetchone()[0]

            # 🧭 Insert End Location (✅ Fixed Lat/Lon)
            cursor.execute("""
                INSERT INTO Location (Address, Lat, Lon)
                OUTPUT INSERTED.Location_ID
                VALUES (?, ?, ?)
            """, end_address, end_lat, end_lon)
            dropoff_id = cursor.fetchone()[0]

            # 🚗 Insert Ride Offer
            print("=== Executing AddRideOffer ===")
            print("User:", session['user_id'], "Vehicle:", vehicle_id)
            print("Pickup:", pickup_id, "Dropoff:", dropoff_id)
            print("Date:", ride_date, "Time:", ride_time, "ETA:", est_arrival)
            print("Seats:", seats, "Fare:", fare)

            cursor.execute("""
                EXEC AddRideOffer 
                    @UserID = ?, 
                    @VehicleID = ?, 
                    @StartLoc = ?, 
                    @EndLoc = ?, 
                    @PickupLoc = ?, 
                    @DropoffLoc = ?, 
                    @Date = ?, 
                    @DepartTime = ?, 
                    @EstArr = ?, 
                    @Seats = ?, 
                    @Fare = ?, 
                    @Status = ?
            """, session['user_id'], vehicle_id, pickup_id, dropoff_id, pickup_id, dropoff_id,
                 ride_date, ride_time, est_arrival, seats, fare, 'Scheduled')

            conn.commit()
            flash("✅ Ride offer posted successfully!", "success")
            return redirect(url_for('dashboard'))

        except Exception as e:
            conn.rollback()
            print("Ride Offer Insert Failed:", e)
            flash(f"Failed to post ride: {e}", "danger")

    # 🚙 Load vehicles
    cursor.execute("""
        SELECT Vehicle_ID, VehicleType + ' - ' + Plate_No AS name 
        FROM Vehicle 
        WHERE User_ID = ?
    """, session['user_id'])
    vehicles = [{"id": row.Vehicle_ID, "name": row.name} for row in cursor.fetchall()]

    return render_template('offer_ride.html', vehicles=vehicles)

# ✅ Book Rides
from datetime import date, time, datetime  # ✅ needed for isinstance()

@app.route('/book_ride')
def book_ride():
    if 'user_id' not in session:
        flash("Please log in to view rides.", "warning")
        return redirect(url_for('login'))

    conn = get_conn()
    cursor = conn.cursor()
    user_id = session['user_id']

    # Filters
    from_loc = request.args.get('from')
    to_loc = request.args.get('to')
    date_filter = request.args.get('date')
    sort = request.args.get('sort')

    # Base query: only show rides by other users, with seats, in future
    base_query = """
        SELECT 
            r.Ride_ID,
            u.F_Name + ' ' + u.L_Name AS Driver,
            startLoc.Address AS Pickup, 
            endLoc.Address AS Dropoff,
            r.Ride_Date, r.Departure_Time, r.Available_Seats, r.Total_Fare,
            startLoc.Lat AS StartLat, startLoc.Lon AS StartLon,
            endLoc.Lat AS EndLat, endLoc.Lon AS EndLon
        FROM Ride_Offer r
        JOIN Student s ON r.User_ID = s.User_ID
        JOIN Users u ON s.User_ID = u.User_ID
        JOIN Location startLoc ON r.Pickup_Location_ID = startLoc.Location_ID
        JOIN Location endLoc ON r.Dropoff_Location_ID = endLoc.Location_ID
        WHERE 
            r.Status = 'Scheduled'
            AND r.Available_Seats > 0
            AND r.User_ID != ?
    """

    params = [user_id]

    if from_loc:
        base_query += " AND startLoc.Address LIKE ?"
        params.append(f"%{from_loc}%")
    if to_loc:
        base_query += " AND endLoc.Address LIKE ?"
        params.append(f"%{to_loc}%")
    if date_filter:
        base_query += " AND r.Ride_Date = ?"
        params.append(date_filter)

    # Sorting
    if sort == 'earliest':
        base_query += " ORDER BY r.Ride_Date ASC, r.Departure_Time ASC"
    elif sort == 'cheapest':
        base_query += " ORDER BY r.Total_Fare ASC"
    elif sort == 'most_seats':
        base_query += " ORDER BY r.Available_Seats DESC"

    # Execute and fetch
    cursor.execute(base_query, params)

    rides = []
    columns = [column[0] for column in cursor.description]
    for row in cursor.fetchall():
        ride = dict(zip(columns, row))
        for key, value in ride.items():
            if isinstance(value, (date, time)):  # ✅ now this won't crash
                ride[key] = str(value)
        rides.append(ride)

    return render_template("book_ride.html", rides=rides, ride_coords=rides)

# === ROUTE: Confirm Ride Booking ===
@app.route('/confirm_booking', methods=['POST'])
def confirm_booking():
    ride_id = request.form.get('ride_id')
    seat_count = int(request.form.get('seat_count', 1))
    user_id = session.get('user_id')
    
    if not user_id:
        flash("Please log in to book a ride.", "warning")
        return redirect(url_for('login'))

    # Connect to DB
    conn = get_conn()
    cursor = conn.cursor()

    try:
        # Call your stored procedure for booking
        cursor.execute(
    "EXEC BookRides @RideID = ?, @StudentID = ?, @SeatCount = ?",
    (ride_id, user_id, seat_count)
)
        conn.commit()
        flash("Booking successful! 🎉", "success")
    except Exception as e:
        conn.rollback()
        flash(f"Booking failed: {str(e)}", "danger")
        print("Booking error:", e)
    finally:
        conn.close()
    print(f"Booking attempt: ride_id={ride_id}, user_id={user_id}, seats={seat_count}")


    return redirect(url_for('my_bookings', filter='upcoming'))


# === ROUTE: Cancel Booking ===
@app.route('/cancel_booking', methods=['POST'])
def cancel_booking():
    if 'user_id' not in session:
        flash("Please log in to cancel bookings.", "warning")
        return redirect(url_for('login'))

    booking_id = request.form.get('booking_id')
    conn = get_conn()
    cursor = conn.cursor()

    try:
        cursor.execute("EXEC CancelBooking @BookingID = ?", (booking_id,))
        conn.commit()
        flash("Booking successfully cancelled.", "info")
    except Exception as e:
        conn.rollback()
        flash(f"Failed to cancel booking: {e}", "danger")

    return redirect(url_for('my_bookings'))

# === IMPORTS ===
from flask import Flask, render_template, request, redirect, url_for, session, flash
from db import get_conn  # Custom DB connector
from datetime import datetime, timedelta, date

# === ROUTE: My Bookings ===
@app.route('/my_bookings')
def my_bookings():
    if 'user_id' not in session:
        flash("Please log in to view your bookings.", "warning")
        return redirect(url_for('login'))

    user_id = session['user_id']
    filter_type = request.args.get('filter', 'upcoming')
    today = date.today()

    conn = get_conn()
    cursor = conn.cursor()

    try:
        if filter_type == 'upcoming':
            cursor.execute("EXEC GetUpcomingBooking @StudentID = ?", user_id)
        elif filter_type == 'past':
            cursor.execute("SELECT * FROM View_Past_Bookings WHERE Booking_ID IN (SELECT Booking_ID FROM Booking WHERE User_ID = ?)", user_id)
        elif filter_type == 'cancelled':
            cursor.execute("SELECT * FROM View_Cancelled_Bookings WHERE Booking_ID IN (SELECT Booking_ID FROM Booking WHERE User_ID = ?)", user_id)
        else:  # 'all'
            cursor.execute("SELECT * FROM View_All_Bookings WHERE Booking_ID IN (SELECT Booking_ID FROM Booking WHERE User_ID = ?)", user_id)

        bookings = cursor.fetchall()
        return render_template("my_bookings.html", bookings=bookings, filter=filter_type, current_date=today)
    except Exception as e:
        flash(f"Failed to fetch bookings: {e}", "danger")
        return render_template("my_bookings.html", bookings=[], filter=filter_type, current_date=today)


# === ROUTE: My Offered Rides ===
@app.route('/my_offered_rides')
def my_offered_rides():
    if 'user_id' not in session:
        flash("Please log in to view your rides.", "warning")
        return redirect(url_for('login'))

    user_id = session['user_id']
    conn = get_conn()
    cursor = conn.cursor()

    try:
        # 🚗 Fetch this user's upcoming offered rides
        cursor.execute("""
            SELECT 
                R.Ride_ID,
                R.Ride_Date,
                R.Departure_Time,
                R.Estimated_Arrival,
                R.Available_Seats,
                R.Total_Fare,
                R.Status,
                L1.Address AS Start_Address,
                L2.Address AS End_Address
            FROM Ride_Offer R
            JOIN Location L1 ON R.Start_Location_ID = L1.Location_ID
            JOIN Location L2 ON R.End_Location_ID = L2.Location_ID
            WHERE R.User_ID = ? AND R.Status = 'Scheduled'
            ORDER BY R.Ride_Date DESC, R.Departure_Time DESC
        """, (user_id,))

        # 🔄 Convert to list of dicts for template access
        columns = [col[0] for col in cursor.description]
        rides = [dict(zip(columns, row)) for row in cursor.fetchall()]

        return render_template("my_offered_rides.html", rides=rides)

    except Exception as e:
        print("Error loading offered rides:", e)
        flash("Error fetching offered rides. Please try again.", "danger")
        return render_template("my_offered_rides.html", rides=[])

@app.route('/ride/<int:ride_id>/passengers')
def view_passengers(ride_id):
    if not session.get('user_id'):
        return redirect(url_for('login'))

    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT Users.User_ID, Users.F_Name, Users.Email, Users.Phone,
           Booking.Seat_Count, Booking.Booking_Status
    FROM Booking
    JOIN Users ON Booking.User_ID = Users.User_ID
    WHERE Booking.Ride_ID = ?
""", ride_id)

    passengers = cursor.fetchall()
    conn.close()

    return render_template('view_passengers.html', passengers=passengers)



@app.route('/ride/<int:ride_id>/edit', methods=['GET', 'POST'])
def edit_ride(ride_id):
    if not session.get('user_id'):
        return redirect(url_for('login'))

    conn = get_conn()
    cursor = conn.cursor()

    if request.method == 'POST':
        new_date = request.form['ride_date']
        new_time = request.form['ride_time']
        new_fare = request.form['fare']
        new_seats = request.form['seats']

        cursor.execute("""
            UPDATE Ride_Offer SET Ride_Date = ?, Departure_Time = ?, Total_Fare = ?, Available_Seats = ?
            WHERE Ride_ID = ? AND User_ID = ?
        """, (new_date, new_time, new_fare, new_seats, ride_id, session['user_id']))
        conn.commit()
        conn.close()
        return redirect(url_for('my_offered_rides'))

    cursor.execute("SELECT * FROM Ride_Offer WHERE Ride_ID = ? AND User_ID = ?", (ride_id, session['user_id']))
    ride = cursor.fetchone()
    conn.close()

    if not ride:
        return "Ride not found or unauthorized", 404

    return render_template('edit_ride.html', ride=ride)


@app.route('/ride/<int:ride_id>/cancel')
def cancel_ride(ride_id):
    if not session.get('user_id'):
        return redirect(url_for('login'))

    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("UPDATE Ride_Offer SET Status = 'Cancelled' WHERE Ride_ID = ? AND User_ID = ?", (ride_id, session['user_id']))
    conn.commit()
    conn.close()

    return redirect(url_for('my_offered_rides'))



# === RIDE MAP VIEW FOR A SPECIFIC RIDE ===
@app.route('/ride_map/<int:ride_id>')
def ride_map(ride_id):
    conn = get_conn()
    cursor = conn.cursor()
    # Fetch start and end location details for the ride
    cursor.execute("""
        SELECT l1.Address, l1.Latitude, l1.Longitude,
               l2.Address, l2.Latitude, l2.Longitude
        FROM Ride_Offer r
        JOIN Location l1 ON r.Pickup_Location_ID = l1.Location_ID
        JOIN Location l2 ON r.Dropoff_Location_ID = l2.Location_ID
        WHERE r.Ride_ID = ?
    """, ride_id)
    ride = cursor.fetchone()
    return render_template('ride_map.html', ride=ride)

@app.route('/my_reviews')
def my_reviews():
    if 'user_id' not in session:
        flash('Please login to view your reviews')
        return redirect(url_for('login'))

    return render_template('my_reviews.html')


# === EDIT A REVIEW ===
@app.route('/edit_review/<int:review_id>', methods=['POST'])
def edit_review(review_id):
    new_rating = int(request.form['rating'])
    new_comment = request.form['comment']

    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE Reviews
        SET Rating = ?, Comment = ?
        WHERE Review_ID = ? AND Reviewer_ID = ?
    """, (new_rating, new_comment, review_id, session['user_id']))
    conn.commit()

    flash("Review updated successfully.")
    return redirect(url_for('my_reviews'))

# === DELETE A REVIEW ===
@app.route('/delete_review/<int:review_id>', methods=['POST'])
def delete_review(review_id):
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("""
        DELETE FROM Reviews
        WHERE Review_ID = ? AND Reviewer_ID = ?
    """, (review_id, session['user_id']))
    conn.commit()

    flash("Review deleted.")
    return redirect(url_for('my_reviews'))

# === SUBMIT A NEW REVIEW ===
@app.route('/submit_review', methods=['GET', 'POST'])
def submit_review():
    conn = get_conn()
    cursor = conn.cursor()

    if request.method == 'POST':
        form = request.form
        reviewer_id = session['user_id']
        reviewee_id = form['reviewee_id']
        ride_id = form['ride_id']
        rating = int(form['rating'])
        comment = form['comment']

        try:
            # Call stored procedure to insert a review
            cursor.execute("EXEC SubmitReview ?, ?, ?, ?, ?", 
                reviewer_id, reviewee_id, ride_id, rating, comment)
            conn.commit()
            flash("Review submitted successfully.", "success")
        except Exception as e:
            flash(f"Review failed: {e}", "danger")

    # Fetch past rides for which a review can be submitted
    cursor.execute("""
        SELECT r.Ride_ID, u.F_Name + ' ' + u.L_Name AS Driver
        FROM Ride_Offer r
        JOIN Users u ON r.User_ID = u.User_ID
        WHERE r.Ride_Date <= CAST(GETDATE() AS DATE)
    """)
    rides = cursor.fetchall()
    return render_template("review_form.html", rides=rides)

@app.route('/profile')
def profile():
    cursor = get_conn().cursor()
    cursor.execute("""
        SELECT s.Enrollment_No, u.F_Name + ' ' + u.L_Name, u.Email, u.Phone, 
               u.CNIC, u.Gender, s.Department, univ.University_Name, univ.City
        FROM Student s
        JOIN Users u ON s.User_ID = u.User_ID
        JOIN University univ ON s.University_ID = univ.University_ID
        WHERE s.User_ID = ?
    """, session['user_id'])
    p = cursor.fetchone()

    profile = {
        "enrollment": p[0],
        "name": p[1],
        "email": p[2],
        "phone": p[3],
        "cnic": p[4],
        "gender": p[5],
        "department": p[6],
        "university": p[7],
        "city": p[8]
    }
    return render_template("profile.html", profile=profile)

# ✅ Edit Profile
@app.route('/edit_profile')
def edit_profile():
    if 'user_id' not in session:
        flash("Please log in first!", "warning")
        return redirect(url_for('login'))

    user_id = session['user_id']
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM Users WHERE User_ID = ?", user_id)
    user_data = cursor.fetchone()

    return render_template("edit_profile.html", profile=user_data)


# ✅ Admin Dashboard
@app.route('/admin/dashboard')
def admin_dashboard():
    if not session.get('admin'):
        return redirect(url_for('login'))

    conn = get_conn()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM Student")
    total_students = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM Student WHERE Is_Driver = 1")
    total_drivers = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM Users WHERE Status = 'Blocked'")
    blocked_users = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM University")
    total_universities = cursor.fetchone()[0]

    return render_template('admin_dashboard.html',
                           total_students=total_students,
                           total_drivers=total_drivers,
                           blocked_users=blocked_users,
                           total_universities=total_universities)

# ✅ Admin Pages for Management
@app.route('/admin/students')
def manage_students():
    if not session.get('admin'):
        return redirect(url_for('login'))

    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM vw_BasicUserInfo WHERE Email != 'aneeza@campuslift.com'")

    rows = cursor.fetchall()
    columns = [column[0] for column in cursor.description]
    students = [dict(zip(columns, row)) for row in rows]
    return render_template('manage_students.html', students=students)

from collections import defaultdict

@app.route('/admin/student_details/<int:user_id>')
def student_details(user_id):
    if not session.get('admin'):
        return redirect(url_for('login'))

    conn = get_conn()
    cursor = conn.cursor()

    cursor.execute("SELECT Email FROM Users WHERE User_ID = ?", (user_id,))
    result = cursor.fetchone()
    if result and result[0].lower() == 'aneeza@campuslift.com':
        return jsonify({})  # skip admin

    cursor.execute("SELECT * FROM vw_UserFullDetails WHERE User_ID = ?", (user_id,))
    rows = cursor.fetchall()
    columns = [col[0] for col in cursor.description]

    grouped = defaultdict(list)
    for row in rows:
        record = dict(zip(columns, row))
        
        # Static details (only once)
        for key in ['Enrollment_No', 'University_Name', 'Department', 'Emergency_Contact', 'Is_Verified',
                    'VehicleType', 'Plate_No', 'Model', 'Color', 'Capacity', 'Vehicle_Active']:
            if key in record and record[key] not in grouped:
                grouped[key] = record[key]

        # Rides
        if record['Offered_Ride_ID']:
            grouped['Rides'].append({
                'Start_Location': record['Start_Location'],
                'End_Location': record['End_Location'],
                'Ride_Date': str(record['Ride_Date']),
                'Departure_Time': str(record['Departure_Time']),
                'Available_Seats': record['Available_Seats'],
                'Ride_Status': record['Ride_Status']
            })

        # Bookings
        if record['Booking_ID']:
            grouped['Bookings'].append({
                'Booking_ID': record['Booking_ID'],
                'Seat_Count': record['Seat_Count'],
                'Booking_Status': record['Booking_Status']
            })

        # Reviews (both received and given)
        if record['Given_Comment']:
            grouped['Reviews'].append({
                'Type': 'Given',
                'Rating': record['Given_Rating'],
                'Comment': record['Given_Comment'],
                'Timestamp': str(record['Given_Timestamp'])
            })
        if record['Received_Comment']:
            grouped['Reviews'].append({
                'Type': 'Received',
                'Rating': record['Received_Rating'],
                'Comment': record['Received_Comment'],
                'Timestamp': str(record['Received_Timestamp'])
            })

    conn.close()
    return jsonify(grouped)



@app.route('/students/<int:user_id>')
def view_student(user_id):
    conn = get_conn()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM vw_BasicUserInfo WHERE User_ID = ?", user_id)
    row = cursor.fetchone()

    if not row:
        return "Student not found", 404

    columns = [col[0] for col in cursor.description]
    student = dict(zip(columns, row))

    return render_template("manage_students.html", students=[student])

 
@app.route('/view-vehicles')
@app.route('/view-vehicles/<int:vehicle_id>')
def view_vehicles(vehicle_id=None):
    conn = get_conn()
    cursor = conn.cursor()

    if vehicle_id:
        cursor.execute("SELECT * FROM dbo.vw_BasicVehicleInfo WHERE Vehicle_ID = ?", (vehicle_id,))
    else:
        cursor.execute("SELECT * FROM dbo.vw_BasicVehicleInfo")

    vehicles = [dict(zip([column[0] for column in cursor.description], row)) for row in cursor.fetchall()]
    conn.close()
    return render_template("vehicles.html", vehicles=vehicles)

@app.route('/view-student/<int:user_id>')
def view_student_profile(user_id):
    if not session.get('admin'):
        return redirect(url_for('login'))

    conn = get_conn()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM vw_BasicUserInfo WHERE User_ID = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()

    if not row:
        student = None
    else:
        columns = [col[0] for col in cursor.description]
        student = dict(zip(columns, row))

    return render_template("student_profile.html", student=student)


@app.route('/view_rides')
def view_rides():
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM vw_BasicRideInfo")
    rides = cursor.fetchall()
    conn.close()
    return render_template('view_rides.html', rides=rides)


@app.route('/view_bookings')
def view_bookings():
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM vw_BookingDetails")
    bookings = cursor.fetchall()

    # Optional: Column names for clarity (if needed in Jinja)
    columns = [column[0] for column in cursor.description]
    booking_list = [dict(zip(columns, row)) for row in bookings]
    conn.close()
    return render_template('view_bookings.html', bookings=booking_list)


@app.route('/admin/reviews')
def view_reviews():
    if not session.get('admin'):
        return redirect(url_for('login'))
    return render_template('view_reviews.html')

@app.route('/admin/manage_university', methods=['GET', 'POST'])
def manage_university():
    if not session.get('admin'):
        return redirect(url_for('login'))

    conn = get_conn()
    cursor = conn.cursor()

    if request.method == 'POST':
        name = request.form['university_name']
        city = request.form['city']
        email = request.form['contact_email']
        is_approved = 1 if request.form.get('is_approved') == 'on' else 0
        try:
            cursor.execute("EXEC AddUniversity ?, ?, ?, ?", (name, city, email, is_approved))
            conn.commit()
            flash("University added successfully!", "success")
        except Exception as e:
            flash(f"Error adding university: {e}", "danger")

    cursor.execute("SELECT University_ID, University_Name, City, Contact_Email, Is_Approved FROM University")
    universities = cursor.fetchall()
    conn.close()

    return render_template('manage_university.html', universities=universities)

# ✅ Logout
@app.route('/logout')
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)
