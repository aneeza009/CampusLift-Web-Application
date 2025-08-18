#  CampusLift – Web Application  

CampusLift is a ride-sharing platform built for university campuses. It connects students and drivers in a secure, efficient, and eco-friendly way. The system ensures safe commuting, reduces transportation costs, and helps minimize traffic congestion inside campuses.  

---

##  Features  
-  **Student Registration** – Students can sign up and manage their profiles.  
-  **Ride Offering** – Drivers (students with vehicles) can offer rides with details like route, timing, and available seats.  
-  **Ride Booking** – Students can book available rides instantly.  
-  **Payment Integration** – Simple payment management for completed rides.  
-  **Review System** – Students can rate drivers and rides for trust and reliability.  
-  **Admin Panel** – University admins can manage students, drivers, vehicles, and ride history.  
-  **University Integration** – Supports multiple universities and their students.  

---

##  Tech Stack  
- **Backend:** [Flask](https://flask.palletsprojects.com/) (Python)  
- **Database:** Microsoft SQL Server (with stored procedures, views, and triggers)  
- **Frontend:** Flask Templates (HTML, Jinja2, Bootstrap)  
- **ORM / DB Connection:** pyodbc  
- **Environment Management:** python-dotenv  

---

##  Project Structure  


CampusLift/
│-- campus\_lift\_app/    # Main Flask app
│-- static/             # CSS, JS, Images
│-- templates/          # HTML templates
│-- venv/               # Virtual environment (not pushed to repo)
│-- .gitignore
│-- requirements.txt
│-- README.md



##  Installation & Setup  

### 1. Clone the repository  
bash
git clone https://github.com/aneeza009/CampusLift-Web-Application.git
cd CampusLift-Web-Application


### 2. Create & activate virtual environment

bash
python -m venv venv
venv\Scripts\activate   # On Windows
# OR
source venv/bin/activate   # On Mac/Linux


### 3. Install dependencies

bash
pip install -r requirements.txt


### 4. Configure Environment Variables

Create a `.env` file in the project root:


DB_SERVER=your_server_name
DB_DATABASE=your_database_name
DB_USERNAME=your_username
DB_PASSWORD=your_password
SECRET_KEY=your_secret_key


### 5. Run the application

bash
flask run


---

##  Future Enhancements

* Mobile App integration for Android/iOS
* Advanced search & route optimization
* Real-time ride tracking
* Wallet system for digital payments

---

##  Authors  

- **Aneeza Naheen**  
  📌 GitHub: [aneeza009](https://github.com/aneeza009)  

- **Muneefah Shahzad**  
  📌 GitHub: [mun33fa](https://github.com/mun33fa)  

- **Adan Zia**  
  📌 GitHub: [adnz1](https://github.com/adnz1)  

