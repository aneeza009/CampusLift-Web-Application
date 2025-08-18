CREATE DATABASE campus_lift;

USE campus_lift;

CREATE TABLE Users(
    User_ID INT PRIMARY KEY IDENTITY (1,1),
    F_Name VARCHAR(20) NOT NULL,
    L_Name VARCHAR(20) NOT NULL,
    Email VARCHAR(30) UNIQUE NOT NULL,
    Password VARCHAR(12) NOT NULL,
    Phone VARCHAR(11),
    Gender VARCHAR(10) CHECK (Gender IN ('Male', 'Female')),
    CNIC VARCHAR(13) UNIQUE,
    Status VARCHAR(20) CHECK (Status IN ('Active', 'Suspended', 'Blocked'))
);


CREATE TABLE University (
    University_ID INT PRIMARY KEY IDENTITY(1,1),
    University_Name VARCHAR(50) NOT NULL,
    City VARCHAR(20),
    Contact_Email VARCHAR(30) UNIQUE,
    Is_Approved BIT DEFAULT 0
);

CREATE TABLE Student (
    User_ID INT PRIMARY KEY,
    Enrollment_No VARCHAR(20) UNIQUE,
    University_ID INT,
    Department VARCHAR(50),
    Emergency_Contact VARCHAR(11),
    Is_Driver BIT DEFAULT 0,
    License_No VARCHAR(30),
    Verified BIT DEFAULT 0,
    FOREIGN KEY (User_ID) REFERENCES Users(User_ID),
    FOREIGN KEY (University_ID) REFERENCES University(University_ID)
);

CREATE TABLE Admin (
    User_ID INT PRIMARY KEY,
    Role VARCHAR(50) CHECK (Role IN ('Moderator', 'SuperAdmin')),
    Created_At DATETIME DEFAULT GETDATE(),
    FOREIGN KEY (User_ID) REFERENCES Users(User_ID)
);

CREATE TABLE Vehicle (
    Vehicle_ID INT PRIMARY KEY IDENTITY(1,1),
    User_ID INT,
    VehicleType VARCHAR(10),
    Plate_No VARCHAR(20) UNIQUE,
    Model VARCHAR(20),
    Color VARCHAR(15),
    Capacity INT CHECK (Capacity > 0),
    Is_Active BIT DEFAULT 1,
    FOREIGN KEY (User_ID) REFERENCES Student(User_ID)
);

CREATE TABLE Location (
    Location_ID INT PRIMARY KEY IDENTITY(1,1),
    Address VARCHAR(100),
    Lat FLOAT,
    Lon FLOAT
);

CREATE TABLE Ride_Offer (
    Ride_ID INT PRIMARY KEY IDENTITY(1,1),
    User_ID INT,
    Vehicle_ID INT,
    Start_Location_ID INT,
    End_Location_ID INT,
    Pickup_Location_ID INT,
    Dropoff_Location_ID INT,
    Ride_Date DATE,
    Departure_Time TIME,
    Estimated_Arrival TIME,
    Available_Seats INT CHECK (Available_Seats >= 0),
    Total_Fare DECIMAL(10,2) CHECK (Total_Fare >= 0),
    Status VARCHAR(50) CHECK (Status IN ('Scheduled', 'Completed', 'Cancelled')),
    FOREIGN KEY (User_ID) REFERENCES Student(User_ID),
    FOREIGN KEY (Vehicle_ID) REFERENCES Vehicle(Vehicle_ID),
    FOREIGN KEY (Start_Location_ID) REFERENCES Location(Location_ID),
    FOREIGN KEY (End_Location_ID) REFERENCES Location(Location_ID), 
    FOREIGN KEY (Pickup_Location_ID) REFERENCES Location(Location_ID),
    FOREIGN KEY (Dropoff_Location_ID) REFERENCES Location(Location_ID)
);

CREATE TABLE Booking (
    Booking_ID INT PRIMARY KEY IDENTITY(1,1),
    Ride_ID INT,
    User_ID INT,
    Seat_Count INT CHECK (Seat_Count > 0),
    Booking_Status VARCHAR(20) CHECK (Booking_Status IN ('Pending', 'Confirmed', 'Cancelled')),
    FOREIGN KEY (Ride_ID) REFERENCES Ride_Offer(Ride_ID),
    FOREIGN KEY (User_ID) REFERENCES Student(User_ID)
);

CREATE TABLE Payment (
    Payment_ID INT PRIMARY KEY IDENTITY(1,1),
    Booking_ID INT,
    Amount DECIMAL(10,2) CHECK (Amount >= 0),
    Payment_Method VARCHAR(20) CHECK (Payment_Method IN ('Cash', 'Online')),
    Payment_Status VARCHAR(50) CHECK (Payment_Status IN ('Paid', 'Unpaid', 'Pending')),
    Timestamp DATETIME DEFAULT GETDATE(),
    FOREIGN KEY (Booking_ID) REFERENCES Booking(Booking_ID)
);

CREATE TABLE Review (
    Review_ID INT PRIMARY KEY IDENTITY(1,1),
    Reviewer_ID INT,
    Reviewee_ID INT,
    Ride_ID INT,
    Rating INT CHECK (Rating BETWEEN 1 AND 5),
    Comment VARCHAR (200),
    Timestamp DATETIME,
    FOREIGN KEY (Reviewer_ID) REFERENCES Student(User_ID),
    FOREIGN KEY (Reviewee_ID) REFERENCES Student(User_ID),
    FOREIGN KEY (Ride_ID) REFERENCES Ride_Offer(Ride_ID)
);
GO

--------------- INDEXES for filtering (yet to implement)----------------------
CREATE INDEX idx_user_email ON Users(Email);
CREATE INDEX idx_student_enrollment ON Student(Enrollment_No);
CREATE INDEX idx_admin_role ON Admin(Role);
CREATE INDEX idx_uni_name ON University(University_Name);
CREATE INDEX idx_vehicle_type ON Vehicle(VehicleType);
CREATE INDEX idx_location_address ON Location(Address);
CREATE INDEX idx_ride_date ON Ride_Offer(Ride_Date);
CREATE INDEX idx_booking_status ON Booking(Booking_Status);
CREATE INDEX idx_payment_status ON Payment(Payment_Status);
CREATE INDEX idx_review_rating ON Review(Rating);
CREATE NONCLUSTERED INDEX idx_Booking_Student_Status ON Booking(User_ID, Booking_Status);
CREATE NONCLUSTERED INDEX idx_Payment_Booking_PaymentStatus ON Payment(Booking_ID, Payment_Status);
CREATE NONCLUSTERED INDEX idx_Vehicle_Owner_Active ON Vehicle(User_ID, Is_Active);
CREATE NONCLUSTERED INDEX idx_Student_University_Department ON Student(University_ID, Department);
GO


------------------------ VIEWS (could be used later)-----------------------------------
--1) All ride offers with driver info and vehicle
CREATE VIEW vw_RideOffersWithDriver AS
SELECT r.Ride_ID, u.F_Name + ' ' + u.L_Name AS Driver_Name, v.VehicleType, v.Plate_No, r.Ride_Date, r.Departure_Time, r.Total_Fare, r.Status
FROM Ride_Offer r
JOIN Users u ON r.User_ID = u.User_ID
JOIN Vehicle v ON r.Vehicle_ID = v.Vehicle_ID;
GO

--2) Reviews with reviewer and ride info
CREATE VIEW vw_ReviewDetails AS
SELECT rv.Review_ID, reviewer.F_Name + ' ' + reviewer.L_Name AS Reviewer, reviewee.F_Name + ' ' + reviewee.L_Name AS Reviewee, r.Ride_Date, rv.Rating, rv.Comment
FROM Review rv
JOIN Users reviewer ON rv.Reviewer_ID = reviewer.User_ID
JOIN Users reviewee ON rv.Reviewee_ID = reviewee.User_ID
JOIN Ride_Offer r ON rv.Ride_ID = r.Ride_ID;
GO

--3) University and total registered students
CREATE VIEW vw_UniversityStudentCount AS
SELECT univ.University_Name, COUNT(s.User_ID) AS Total_Students
FROM University univ
JOIN Student s ON univ.University_ID = s.University_ID
GROUP BY univ.University_Name;
GO


------------------------- VIEWS USED IN ADMIN -------------------
--1) Basic User Info (Managed Students)
CREATE OR ALTER VIEW vw_BasicUserInfo AS  
SELECT 
    User_ID,
    F_Name + ' ' + L_Name AS Full_Name,
    Email,
    Phone,
    Gender,
    CNIC,
    Status
FROM Users;
GO

--2) Useful Details (View More Details of a Student)
CREATE OR ALTER VIEW vw_UserFullDetails AS  
SELECT 
    -- A) Student Info
	u.User_ID,
    s.Enrollment_No,
    univ.University_Name,
    s.Department,
    s.Emergency_Contact,
    s.Verified AS Is_Verified,

    -- B) Driver Info
    v.VehicleType,
    v.Plate_No,
    v.Model,
    v.Color,
    v.Capacity,
    v.Is_Active AS Vehicle_Active,

    -- C) Ride Offers
    r.Ride_ID AS Offered_Ride_ID,
    l1.Address AS Start_Location,
    l2.Address AS End_Location,
    r.Ride_Date,
    r.Departure_Time,
    r.Available_Seats,
    r.Status AS Ride_Status,

    -- D) Bookings Made
    b.Booking_ID,
    b.Seat_Count,
    b.Booking_Status,

    -- E) Reviews
    rv_given.Rating AS Given_Rating,
    rv_given.Comment AS Given_Comment,
    rv_given.Timestamp AS Given_Timestamp,

    rv_received.Rating AS Received_Rating,
    rv_received.Comment AS Received_Comment,
    rv_received.Timestamp AS Received_Timestamp

FROM Users u
LEFT JOIN Student s ON u.User_ID = s.User_ID
LEFT JOIN University univ ON s.University_ID = univ.University_ID

LEFT JOIN Vehicle v ON s.User_ID = v.User_ID

LEFT JOIN Ride_Offer r ON r.User_ID = u.User_ID
LEFT JOIN Location l1 ON r.Start_Location_ID = l1.Location_ID
LEFT JOIN Location l2 ON r.End_Location_ID = l2.Location_ID

LEFT JOIN Booking b ON b.User_ID = u.User_ID

LEFT JOIN Review rv_given ON rv_given.Reviewer_ID = u.User_ID
LEFT JOIN Review rv_received ON rv_received.Reviewee_ID = u.User_ID;
GO

--3) Vehicles Information (View vehicles)
CREATE OR ALTER VIEW vw_BasicVehicleInfo AS   
SELECT
    v.Vehicle_ID,
    v.User_ID,
    v.VehicleType,
    v.Plate_No,
    v.Model,
    v.Color,
    v.Capacity,
    v.Is_Active,
    u.F_Name + ' ' + u.L_Name AS Owner_Name
FROM Vehicle v
JOIN Users u ON v.User_ID = u.User_ID
GO

--4) Ride Information (View Rides)
CREATE OR ALTER VIEW vw_BasicRideInfo AS    
SELECT 
    r.Ride_ID,
    u.F_Name + ' ' + u.L_Name AS Driver_Name,
    v.Model + ' (' + v.Plate_No + ')' AS Vehicle,
    sl.Address AS Start_Location,
    el.Address AS End_Location,
    pl.Address AS Pickup_Location,
    dl.Address AS Dropoff_Location,
    r.Ride_Date,
    r.Departure_Time,
    r.Estimated_Arrival,
    r.Available_Seats,
    r.Total_Fare,
    r.Status,
    r.User_ID,
    r.Vehicle_ID
FROM Ride_Offer r
JOIN Users u ON r.User_ID = u.User_ID
JOIN Vehicle v ON r.Vehicle_ID = v.Vehicle_ID
JOIN Location sl ON r.Start_Location_ID = sl.Location_ID
JOIN Location el ON r.End_Location_ID = el.Location_ID
JOIN Location pl ON r.Pickup_Location_ID = pl.Location_ID
JOIN Location dl ON r.Dropoff_Location_ID = dl.Location_ID;
GO

--5) Bookings Information (View Bookings)
CREATE OR ALTER VIEW vw_BookingDetails AS   
SELECT 
    b.Booking_ID,
    
    -- Student who made the booking
    s.User_ID AS Student_ID,
    u1.F_Name + ' ' + u1.L_Name AS Student_Name,
    u1.Email AS Student_Email,
    
    -- Ride Info
    r.Ride_ID,
    r.Ride_Date,
    r.Departure_Time,
    r.Estimated_Arrival,
    
    loc_pickup.Address AS Pickup_Location,
    loc_dropoff.Address AS Dropoff_Location,
    
    -- Driver Info
    d.User_ID AS Driver_ID,
    u2.F_Name + ' ' + u2.L_Name AS Driver_Name,
    u2.Email AS Driver_Email,

    -- Booking details
    b.Seat_Count,
    b.Booking_Status

FROM Booking b
JOIN Ride_Offer r ON b.Ride_ID = r.Ride_ID

-- Student who booked
JOIN Student s ON b.User_ID = s.User_ID
JOIN Users u1 ON s.User_ID = u1.User_ID

-- Driver of the ride
JOIN Student d ON r.User_ID = d.User_ID
JOIN Users u2 ON d.User_ID = u2.User_ID

-- Pickup/Dropoff locations
JOIN Location loc_pickup ON r.Pickup_Location_ID = loc_pickup.Location_ID
JOIN Location loc_dropoff ON r.Dropoff_Location_ID = loc_dropoff.Location_ID;
GO

--------------------- VIEWS USED IN STUDENT (Most queries done within app.py) ------------
--6) My bookings (past)
CREATE VIEW View_Past_Bookings AS                
SELECT 
    b.Booking_ID, b.Seat_Count, b.Booking_Status,
    r.Ride_ID, r.Ride_Date, r.Departure_Time, r.Estimated_Arrival,
    pLoc.Address AS Pickup, dLoc.Address AS Dropoff,
    r.User_ID AS Driver_ID,
    u.F_Name + ' ' + u.L_Name AS Driver_Name,
    u.Phone AS Driver_Phone,
    r.Total_Fare
FROM Booking b
JOIN Ride_Offer r ON b.Ride_ID = r.Ride_ID
JOIN Users u ON r.User_ID = u.User_ID
JOIN Location pLoc ON r.Pickup_Location_ID = pLoc.Location_ID
JOIN Location dLoc ON r.Dropoff_Location_ID = dLoc.Location_ID
WHERE r.Ride_Date < CAST(GETDATE() AS DATE) AND b.Booking_Status = 'Confirmed';
GO

--7) My bookings (cancelled)
CREATE VIEW View_Cancelled_Bookings AS          
SELECT 
    b.Booking_ID, b.Seat_Count, b.Booking_Status,
    r.Ride_ID, r.Ride_Date, r.Departure_Time, r.Estimated_Arrival,
    pLoc.Address AS Pickup, dLoc.Address AS Dropoff,
    r.User_ID AS Driver_ID,
    u.F_Name + ' ' + u.L_Name AS Driver_Name,
    u.Phone AS Driver_Phone,
    r.Total_Fare
FROM Booking b
JOIN Ride_Offer r ON b.Ride_ID = r.Ride_ID
JOIN Users u ON r.User_ID = u.User_ID
JOIN Location pLoc ON r.Pickup_Location_ID = pLoc.Location_ID
JOIN Location dLoc ON r.Dropoff_Location_ID = dLoc.Location_ID
WHERE b.Booking_Status = 'Cancelled';
GO

--8) My bookings (All)
CREATE VIEW View_All_Bookings AS            
SELECT 
    b.Booking_ID, b.Seat_Count, b.Booking_Status,
    r.Ride_ID, r.Ride_Date, r.Departure_Time, r.Estimated_Arrival,
    pLoc.Address AS Pickup, dLoc.Address AS Dropoff,
    r.User_ID AS Driver_ID,
    u.F_Name + ' ' + u.L_Name AS Driver_Name,
    u.Phone AS Driver_Phone,
    r.Total_Fare
FROM Booking b
JOIN Ride_Offer r ON b.Ride_ID = r.Ride_ID
JOIN Users u ON r.User_ID = u.User_ID
JOIN Location pLoc ON r.Pickup_Location_ID = pLoc.Location_ID
JOIN Location dLoc ON r.Dropoff_Location_ID = dLoc.Location_ID;
GO

--------------------------- PROCEDURES -----------------------------
--1) Create/Add User
CREATE PROCEDURE AddUser      
    @FName VARCHAR(20),
    @LName VARCHAR(20),
    @Email VARCHAR(30),
    @Password VARCHAR(12),
    @Phone VARCHAR(11),
    @Gender VARCHAR(10),
    @CNIC VARCHAR(13),
    @Status VARCHAR(20)
AS
BEGIN
    INSERT INTO Users (F_Name, L_Name, Email, Password, Phone, Gender, CNIC, Status)
    VALUES (@FName, @LName, @Email, @Password, @Phone, @Gender, @CNIC, @Status);

END;
GO

EXEC AddUser            --Registering an Admin 
    @FName = 'Aneeza',
    @LName = 'Naheen',
    @Email = 'aneeza@campuslift.com',
    @Password = 'aneeza@123',
    @Phone = '03001234567',
    @Gender = 'Female',
    @CNIC = '3520198765432',
    @Status = 'Active';
GO

SELECT User_ID FROM Users WHERE Email = 'aneeza@campuslift.com';
GO

INSERT INTO Admin (User_ID, Role)
VALUES (1, 'Moderator');
GO

--2) Register Student 
CREATE PROCEDURE RegisterStudent
    @UserID INT,
    @Enrollment VARCHAR(20),
    @UniversityID INT,
    @Department VARCHAR(50),
    @EmergencyContact VARCHAR(11),
    @IsDriver BIT = 0,
    @LicenseNo VARCHAR(30),
    @Verified BIT = 1
AS
BEGIN
    INSERT INTO Student (User_ID, Enrollment_No, University_ID, Department, Emergency_Contact, Is_Driver, License_No, Verified)
    VALUES (@UserID, @Enrollment, @UniversityID, @Department, @EmergencyContact, @IsDriver, @LicenseNo, @Verified);
END;
GO

--3) Add Vehicle
CREATE PROCEDURE AddVehicle
    @UserID INT,
    @VehicleType VARCHAR(10),
    @PlateNo VARCHAR(20),
    @Model VARCHAR(20),
    @Color VARCHAR(15),
    @Capacity INT,
    @IsActive BIT = 1
AS
BEGIN
    INSERT INTO Vehicle (User_ID, VehicleType, Plate_No, Model, Color, Capacity, Is_Active)
    VALUES (@UserID, @VehicleType, @PlateNo, @Model, @Color, @Capacity, @IsActive);
END;
GO

--4) Add Ride Offer
CREATE PROCEDURE AddRideOffer
    @UserID INT,
    @VehicleID INT,
    @StartLoc INT,
    @EndLoc INT,
    @PickupLoc INT,
    @DropoffLoc INT,
    @Date DATE,
    @DepartTime TIME,
    @EstArr TIME,
    @Seats INT,
    @Fare DECIMAL(10,2),
    @Status VARCHAR(50)
AS
BEGIN
    INSERT INTO Ride_Offer (User_ID, Vehicle_ID, Start_Location_ID, End_Location_ID, Pickup_Location_ID, Dropoff_Location_ID, Ride_Date, Departure_Time, Estimated_Arrival, Available_Seats, Total_Fare, Status)
    VALUES (@UserID, @VehicleID, @StartLoc, @EndLoc, @PickupLoc, @DropoffLoc, @Date, @DepartTime, @EstArr, @Seats, @Fare, @Status);
END;
GO

--5) Book a ride
CREATE PROCEDURE BookRides
    @RideID INT,
    @StudentID INT,
    @SeatCount INT
AS
BEGIN
    DECLARE @AvailableSeats INT;
    DECLARE @TotalFare DECIMAL(10,2);
    DECLARE @FarePerSeat DECIMAL(10,2);
    DECLARE @PaymentAmount DECIMAL(10,2);
    DECLARE @BookingID INT;

    SELECT @AvailableSeats = Available_Seats,
           @TotalFare = Total_Fare
    FROM Ride_Offer
    WHERE Ride_ID = @RideID;

    IF @AvailableSeats >= @SeatCount
    BEGIN
        -- Calculate fare per seat
        SET @FarePerSeat = @TotalFare / NULLIF(@AvailableSeats + @SeatCount, 0);
        SET @PaymentAmount = @FarePerSeat * @SeatCount;

        -- Insert booking
        INSERT INTO Booking (Ride_ID, User_ID, Seat_Count, Booking_Status)
        VALUES (@RideID, @StudentID, @SeatCount, 'Confirmed');

        SET @BookingID = SCOPE_IDENTITY(); -- Get the inserted Booking_ID

        -- Insert payment
        EXEC AddPayment @BookingID, @PaymentAmount, 'Online', 'Paid';

        -- Update available seats
        UPDATE Ride_Offer
        SET Available_Seats = Available_Seats - @SeatCount
        WHERE Ride_ID = @RideID;
    END
    ELSE
    BEGIN
        RAISERROR('Not enough seats available.', 16, 1) WITH NOWAIT;
    END
END;
GO

--6) Cancel a Booking
CREATE PROCEDURE CancelBooking
    @BookingID INT
AS
BEGIN
    DECLARE @RideID INT, @SeatCount INT;

    SELECT @RideID = Ride_ID, @SeatCount = Seat_Count
    FROM Booking
    WHERE Booking_ID = @BookingID;

    -- Refund the seats
    UPDATE Ride_Offer
    SET Available_Seats = Available_Seats + @SeatCount
    WHERE Ride_ID = @RideID;

    -- Mark the booking as cancelled
    UPDATE Booking
    SET Booking_Status = 'Cancelled'
    WHERE Booking_ID = @BookingID;
END;
GO

--7) Add Location
CREATE PROCEDURE AddLocation
    @Address VARCHAR(100),
    @Lat FLOAT,
    @Lon FLOAT
AS
BEGIN
    INSERT INTO Location (Address, Lat, Lon)
    VALUES (@Address, @Lat, @Lon);
END;
GO

--8) Update Location
CREATE PROCEDURE UpdateLocation
    @LocationID INT,
    @NewAddress VARCHAR(100),
    @Lat FLOAT = NULL,
    @Lon FLOAT = NULL
AS
BEGIN
    UPDATE Location
    SET 
        Address = @NewAddress,
        Lat = ISNULL(@Lat, Lat),
        Lon = ISNULL(@Lon, Lon)
    WHERE Location_ID = @LocationID;
END;
GO

--9) Add University 
CREATE PROCEDURE AddUniversity
    @UniversityName VARCHAR(100),
    @City VARCHAR(20),
    @Email VARCHAR(30),
    @IsApproved BIT = 1
AS
BEGIN
    INSERT INTO University (University_Name, City, Contact_Email, Is_Approved)
    VALUES (@UniversityName, @City, @Email, @IsApproved);
END;
GO

--10) Upcoming Bookings in My bookings 
CREATE PROCEDURE GetUpcomingBooking
    @StudentID INT
AS
BEGIN
    SELECT 
        b.Booking_ID,
        r.Ride_ID,
        r.Ride_Date,
        r.Departure_Time,
        r.Estimated_Arrival,
        b.Seat_Count AS Seats_Booked,
        b.Booking_Status,
        pLoc.Address AS Pickup,
        dLoc.Address AS Dropoff,
        r.User_ID AS Driver_ID,
        u.F_Name + ' ' + u.L_Name AS Driver_Name,
        u.Phone AS Driver_Phone,
        r.Total_Fare,
        'Paid' AS Payment_Status -- or fetch from Payment table if dynamic status needed
    FROM Booking b
    JOIN Ride_Offer r ON b.Ride_ID = r.Ride_ID
    JOIN Users u ON r.User_ID = u.User_ID
    JOIN Location pLoc ON r.Pickup_Location_ID = pLoc.Location_ID
    JOIN Location dLoc ON r.Dropoff_Location_ID = dLoc.Location_ID
    WHERE 
        b.User_ID = @StudentID
        AND r.Ride_Date >= CAST(GETDATE() AS DATE)
        AND b.Booking_Status = 'Confirmed'
END
GO

-------------------Reviews and Payment Related Procedures------------------
-- Mark Payemnt as Paid
CREATE PROCEDURE MarkPaymentPaid
    @PaymentID INT
AS
BEGIN
    UPDATE Payment
    SET Payment_Status = 'Paid'
    WHERE Payment_ID = @PaymentID;
END;
GO

--Submit a Review
CREATE PROCEDURE SubmitReview
    @ReviewerID INT,
    @RevieweeID INT,
    @RideID INT,
    @Rating INT,
    @Comment VARCHAR(200)
AS
BEGIN
    INSERT INTO Review (Reviewer_ID, Reviewee_ID, Ride_ID, Rating, Comment, Timestamp)
    VALUES (@ReviewerID, @RevieweeID, @RideID, @Rating, @Comment, GETDATE());
END;
GO

--Add payment 
CREATE PROCEDURE AddPayment
    @BookingID INT,
    @Amount DECIMAL(10,2),
    @PaymentMethod VARCHAR(20),
    @PaymentStatus VARCHAR(50)
AS
BEGIN
    INSERT INTO Payment (Booking_ID, Amount, Payment_Method, Payment_Status)
    VALUES (@BookingID, @Amount, @PaymentMethod, @PaymentStatus);
END;
GO

----------------------------- TRIGGERS-----------------------------
--1) Automatically make user/student a driver when they register vehicle 
CREATE TRIGGER TRG_SetIsDriverOnVehicleInsert
ON Vehicle
AFTER INSERT
AS
BEGIN
    UPDATE Student
    SET Is_Driver = 1
    WHERE User_ID IN (
        SELECT User_ID FROM inserted
    );
END;
GO

--2) Prevent studnet from booking more then available seats, or booking more than once
CREATE TRIGGER TRG_LimitBookingSeatsPerUser
ON Booking
INSTEAD OF INSERT
AS
BEGIN
    IF EXISTS (
        SELECT 1
        FROM inserted i
        JOIN Booking b ON i.Ride_ID = b.Ride_ID AND i.User_ID = b.User_ID
    )
    BEGIN
        RAISERROR('You have already booked a seat for this ride.', 16, 1);
        ROLLBACK;
        RETURN;
    END

    IF EXISTS (
        SELECT 1
        FROM inserted i
        JOIN Ride_Offer r ON i.Ride_ID = r.Ride_ID
        WHERE i.Seat_Count > r.Available_Seats
    )
    BEGIN
        RAISERROR('Requested seat count exceeds ride capacity.', 16, 1);
        ROLLBACK;
        RETURN;
    END

    -- ✅ DO THE INSERT YOURSELF
    INSERT INTO Booking (Ride_ID, User_ID, Seat_Count, Booking_Status)
    SELECT Ride_ID, User_ID, Seat_Count, Booking_Status
    FROM inserted;
END
GO

--3) Prevent duplicate plate numbers 
CREATE TRIGGER trg_BlockDuplicateVehicle
ON Vehicle
AFTER INSERT
AS
BEGIN
    IF EXISTS (
        SELECT 1
        FROM inserted i
        JOIN Vehicle v ON i.Plate_No = v.Plate_No
        WHERE i.Vehicle_ID <> v.Vehicle_ID
    )
    BEGIN
        RAISERROR('A vehicle with this plate number already exists.', 16, 1);
        ROLLBACK;
    END
END;
GO

--4) Only verified users can offer a ride
CREATE TRIGGER TRG_EnforceVerifiedUserOnRideOffer
ON Ride_Offer
AFTER INSERT
AS
BEGIN
    IF EXISTS (
        SELECT 1
        FROM inserted i
        JOIN Student s ON i.User_ID = s.User_ID
        WHERE s.Verified = 0
    )
    BEGIN
        RAISERROR('Only verified drivers can create ride offers.', 16, 1);
        ROLLBACK;
    END
END;
GO

-------------------Reviews and Payment Related Triggers------------------
-- Review Rides only after ride is completed 
CREATE TRIGGER TRG_ReviewOnlyAfterRide
ON Review
INSTEAD OF INSERT
AS
BEGIN
    IF EXISTS (
        SELECT 1 FROM inserted i
        JOIN Ride_Offer r ON i.Ride_ID = r.Ride_ID
        WHERE r.Ride_Date > CAST(GETDATE() AS DATE)
    )
    BEGIN
        RAISERROR('You can only review after the ride is completed.', 16, 1);
        ROLLBACK;
    END
END;
GO

--Confrim a booking after payment 
CREATE TRIGGER trg_AutoConfirmBookingOnPayment
ON Payment
AFTER UPDATE
AS
BEGIN
    IF EXISTS (
        SELECT 1
        FROM inserted i
        JOIN deleted d ON i.Payment_ID = d.Payment_ID
        WHERE i.Payment_Status = 'Paid' AND d.Payment_Status <> 'Paid'
    )
    BEGIN
        UPDATE Booking
        SET Booking_Status = 'Confirmed'
        WHERE Booking_ID IN (
            SELECT Booking_ID FROM inserted
            WHERE Payment_Status = 'Paid'
        );
    END
END;
GO
