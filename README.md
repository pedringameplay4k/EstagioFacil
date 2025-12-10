# 🎓 EstágioFácil - Internship Connection Platform

> Connecting promising talents to the best internship opportunities in the market.

**EstágioFácil** is a web application developed in Python (Flask) that serves as a job portal, facilitating interaction between students, companies, and administrators. The system features advanced job search, user profiles with photo uploads, and an administrative dashboard for metrics management.

---

## 🚀 Features

- **🏠 Home / Job Showcase:** View available internship positions with dynamic filters (Area, Salary, Work Model).
- **👥 Multiple Profiles:**
  - **Student:** Can view jobs, upload resumes, apply for positions, and edit their profile.
  - **Company:** Can register, manage their profile, and post vacancies.
  - **Admin:** Access to an exclusive dashboard with system statistics and user management.
- **🔐 Secure Authentication:** Login and Registration with encrypted passwords (Hash).
- **👤 User Profile:** Edit personal data, "About Me" section, and **Profile Picture Upload**.
- **📊 Admin Dashboard:** Overview of registered students, companies, and sign-up metrics.
- **🎨 UI/UX:** Responsive, modern interface with visual feedback (Loaders and Alerts).

---

## 🛠️ Tech Stack

- **Back-end:** Python 3, Flask.
- **Database:** SQLite (via SQLAlchemy ORM).
- **Front-end:** HTML5, CSS3, JavaScript (Vanilla).
- **Security:** Werkzeug Security (Password Hashing).

---

## ⚙️ How to Run Locally

Follow the steps below to run the project on your machine:

### 1. Prerequisites
Make sure you have **Python** installed.

### 2. Clone the repository
```bash
git clone [https://github.com/YOUR-USERNAME/ESTAGIOFACIL.git](https://github.com/YOUR-USERNAME/ESTAGIOFACIL.git)
cd ESTAGIOFACIL


ESTAGIOFACIL/
│
├── instance/           # SQLite Database
├── static/             # CSS, Images, and JS files
├── uploads/            # Profile pictures and resumes
├── templates/          # HTML files (Jinja2)
│   ├── index.html      # Home and Job Listings
│   ├── login.html
│   ├── cadastro.html
│   ├── perfil.html
│   ├── admin_dashboard.html
│   ├── empresa_dashboard.html
│   └── aluno_dashboard.html
│
├── app.py              # Main application code (Routes and Config)
└── README.md           # Documentation

Email: admin@portal.com
Password: admin123
