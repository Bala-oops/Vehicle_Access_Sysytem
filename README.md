# 🚗 Vehicle Access Management System

A web-based application to automate vehicle access requests with role-based approvals, PDF pass generation, and admin analytics dashboard.

---

## 📌 Overview

The **Vehicle Access Management System** is designed to replace manual vehicle entry processes with a digital solution.

It allows employees to request vehicle access online, which goes through a structured approval process (HOD → Security) before generating a final vehicle pass.

---

## 🎯 Features

- 🔐 Role-based authentication (Employee, HOD, Security, Admin)
- 📝 Vehicle access request form
- ✅ Two-level approval system
- 📄 PDF pass generation
- 📊 Admin dashboard with analytics (Power BI/Tableau)
- 🔍 Track request status in real-time
- 🛡️ Secure registration using Domain ID validation

---

## 👥 User Roles

### 👤 Employee
- Submit vehicle access requests  
- View request status  
- Download approved vehicle pass  

### 🧑‍💼 HOD (Head of Department)
- View pending requests  
- Approve or reject requests  

### 🛡️ Security
- View HOD-approved requests  
- Provide final approval  

### 🧑‍💻 Admin
- View system analytics  
- Manage users and requests  
- Access full system data  

---

## ⚙️ Workflow

```text
Employee → Submit Request
        ↓
HOD → Approve / Reject
        ↓
Security → Final Approval
        ↓
PDF Pass Generated



🛠️ Tech Stack
Frontend: HTML, CSS
Backend: Python (Flask)
Database: PostgreSQL (Supabase)
PDF Generation: ReportLab
Analytics: Power BI / Tableau



🔐 Security Features
Session-based authentication
Role-based access control
Server-side validation
Restricted registration (only valid employees)




📊 Highlights
Fully automated approval workflow
Real-time tracking of requests
Data visualization for decision making
Scalable and industry-relevant design



🚀 Conclusion

This project provides an efficient and secure solution for managing vehicle access in organizations by reducing manual work, improving transparency, and ensuring proper authorization at every stage.
