# 🏋️‍♂️🌙 GymNight - Desktop Edition

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

**GymNight Desktop** is a specialized data-driven workout management and analytics software engineered with **Python**, **PySide6**, and **SQLite**. Designed for bodybuilders and fitness enthusiasts, it focuses on hyper-precise progress tracking while eliminating the digital distractions common in modern fitness apps.

> 📱 **Looking for the mobile client?** Check out the [GymNight-Mobile](REPOSITORY_LINK_HERE) repository to track workouts directly from your smartphone.

---

## 📸 Preview
*Insert a dark/neon screenshot of your desktop application interface here!*

---

## 🎯 The Core Problem
Most fitness applications are bloated with social media features, ads, and over-complicated user interfaces that inadvertently encourage smartphone scrolling between sets. **GymNight** solves this by acting as an efficient, streamlined "background script" for your fitness routine: fast, optimal, and deeply data-oriented.

## ✨ Core Features

* **Custom Routine Templates:** Create, structure, and manage advanced workout splits (e.g., Push/Pull/Legs, Upper/Lower, Arnold Split).
* **High-Precision Volume Tracking:** Log sets, repetitions, and weight metrics with minimal interface friction.
* **Smart Performance Metrics:** Automated calculation of weekly training volume per muscle group to prevent overtraining.
* **Local Data Persistence:** Robust, zero-configuration data storage architecture using SQLite for historical progression tracking.
* **Health Dashboard Integration:** Instantly visualize critical biological metrics such as BMI (Body Mass Index) and BMR/TDEE caloric estimations.
* **Input Validation Engine:** Strict data validation layer to prevent anomalous or unrealistic entry logs.

---

## 🛠️ Technology Stack

* **Language:** Python 3.12+
* **GUI Framework:** PySide6 (Qt for Python)
* **Database Engine:** SQLite
* **Architecture:** Modular architecture with strict separation of business logic and UI layer.

---

## 📊 Scientific & Performance Algorithms

### 🏋️‍♂️ Training Volume Calculation
The application automatically computes the total **Training Volume Load (TVL)** for each muscle group to help you monitor progressive overload accurately, using the following formula:

$$TVL = \text{Sets} \times \text{Reps} \times \text{Weight}$$

### 🔥 Caloric Expenditure Model
Energy expenditure calculations during active sets are computed leveraging precise **MET (Metabolic Equivalent of Task)** values combined with temporal estimations based on execution rhythm (factoring an average of 4 seconds per repetition):

$$\text{Calories Burned} = \frac{\text{MET} \times \text{Weight (kg)} \times \text{Duration (mins)}}{60}$$

---

## 🔧 Set Classification Support
The logging engine supports distinct training set typologies to ensure high-fidelity data tracking:
* **Normal Set:** Standard working set targeting the prescribed repetition range.
* **Warm-up Set:** Sub-maximal intensity sets for neurological and joint preparation.
* **Drop Set:** Post-failure drop in load with zero rest to maximize metabolic stress.
* **Failure Set (RPE 10):** Set driven to absolute mechanical muscle failure.

---

## 📧 Contact & Contributions
This is a personal open-source project. For architectural inquiries, bug tracking, or feature requests, feel free to open an Issue or review the internal project documentation.

**GymNight** - Your data-driven training companion. Built with discipline. 📈💪
