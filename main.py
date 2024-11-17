import streamlit as st
import firebase_admin
from firebase_admin import credentials, db, auth
from firebase_admin import firestore
import yagmail
import schedule
import time
import uuid
import random
from datetime import datetime, timedelta
import pandas as pd
import json
from threading import Thread
import streamlit as st
import datetime
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from sqlalchemy import create_engine, Column, String, Integer, DateTime, Float, Text, Boolean
from sqlalchemy.orm import sessionmaker, declarative_base
import numpy as np
from datetime import timedelta
from huggingface_hub import InferenceApi, InferenceClient
import json
import matplotlib.pyplot as plt
from wordcloud import WordCloud
import json
from datetime import time, datetime

class CustomJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (time, datetime)):
            return obj.isoformat()
        return super().default(obj)


# Firebase configuration
FIREBASE_CONFIG = {
    "apiKey": "AIzaSyAK6hPa-TrrGPPge3M33ed4eMtc4uz0G3g",
    "authDomain": "wellness-123.firebaseapp.com",
    "projectId": "wellness-123",
    "storageBucket": "wellness-123.firebasestorage.app",
    "messagingSenderId": "216178271990",
    "appId": "1:216178271990:web:8c462bf695fc4fc6256ed7"
}


# Email configuration
EMAIL_SENDER = "rishavgupta9191@gmail.com"
EMAIL_PASSWORD = "Arnav_6969@"

# Initialize Firebase
try:
    firebase_admin.get_app()
except ValueError:
    cred = credentials.Certificate("wellness-123-firebase-adminsdk-awt57-019ab1e6b2.json")
    firebase_admin.initialize_app(cred, {
        'databaseURL': 'https://wellness-123-default-rtdb.firebaseio.com'
    })


# Initialize Firestore
db = firebase_admin.db


# Initialize Firebase Database reference
ref = db.reference('/')

class FirebaseAuth:
    def __init__(self):
        self.auth = auth
        self.ref = db.reference('/users')  # Create reference at class level

    def get_user_data(self, user_id):
        try:
            # Get basic user info from Auth
            user = self.auth.get_user(user_id)
            # Get extended profile data from Realtime Database
            profile_data = self.ref.child(user_id).get() or {}
            
            return {
                'uid': user.uid,
                'email': user.email,
                'username': profile_data.get('username', user.display_name or 'Guest'),
                'bio': profile_data.get('bio', ''),
                'goals': profile_data.get('goals', []),
                'preferences': profile_data.get('preferences', {
                    'theme': 'Light',
                    'notifications': True,
                    'email_reports': True
                }),
                'stats': profile_data.get('stats', {
                    'streak': 0,
                    'total_checkins': 0,
                    'achievements': []
                })
            }
        except Exception as e:
            return {
                'username': 'Guest',
                'bio': '',
                'goals': [],
                'preferences': {},
                'stats': {}
            }


    def save_user_data(self, user_id, data):
        self.ref.child(user_id).set(data)

    def sign_up(self, email, password, username):
        try:
            # Add input validation
            if len(password) < 6:
                return False, "Password must be at least 6 characters"
                
            if not '@' in email or not '.' in email:
                return False, "Please enter a valid email address"
                
            if len(username) < 3:
                return False, "Username must be at least 3 characters"

            # Create user in Firebase
            user = auth.create_user(
                email=email,
                password=password,
                display_name=username
            )
            
            # Create user profile in database
            self.ref.child(user.uid).set({
                'username': username,
                'email': email,
                'created_at': {'.sv': 'timestamp'},
                'settings': {
                    'email_reports': True,
                    'report_frequency': 'weekly'
                }
            })
            
            return True, user.uid

        except auth.EmailAlreadyExistsError:
            return False, "This email is already registered"



    def sign_in(self, email, password):
        try:
            user = self.auth.get_user_by_email(email)
            # In a real implementation, you would verify the password
            # For demo purposes, we're just checking if the user exists
            return True, user.uid
        except Exception as e:
            return False, str(e)

# Update the get_user_data method:


class DataManager:
    def __init__(self):
        self.db = db

    def save_checkin(self, user_id, checkin_data):
        checkin_ref = (db.collection('users')
                    .document(user_id)
                    .collection('checkins')
                    .document())
        checkin_data['timestamp'] = firestore.SERVER_TIMESTAMP
        checkin_ref.set(checkin_data)

    def get_user_checkins(self, user_id, days=30):
        cutoff = datetime.now() - timedelta(days=days)
        checkins = (db.collection('users')
                   .document(user_id)
                   .collection('checkins')
                   .where('timestamp', '>=', cutoff)
                   .stream())
        return [doc.to_dict() for doc in checkins]

class EmailReporter:
    def __init__(self):
        self.yag = yagmail.SMTP(EMAIL_SENDER, EMAIL_PASSWORD)

    def send_report(self, user_email, report_data):
        try:
            # Generate report content
            report_html = self._generate_report_html(report_data)
            
            # Send email
            subject = f"Your Wellness Report - {datetime.now().strftime('%Y-%m-%d')}"
            self.yag.send(
                to=user_email,
                subject=subject,
                contents=report_html
            )
            return True
        except Exception as e:
            print(f"Error sending email: {str(e)}")
            return False

    def _generate_report_html(self, data):
        # Convert data to pandas DataFrame for analysis
        df = pd.DataFrame(data)
        
        # Calculate key metrics
        avg_sleep = df['sleep_hours'].mean()
        avg_stress = df['stress_level'].mean()
        exercise_days = (df['exercise_minutes'] > 0).sum()
        
        # Generate HTML report
        html = f"""
        <h2>Your Wellness Report</h2>
        <p>Here's your wellness summary for the past period:</p>
        <ul>
            <li>Average Sleep: {avg_sleep:.1f} hours</li>
            <li>Average Stress Level: {avg_stress:.1f}/10</li>
            <li>Days with Exercise: {exercise_days}</li>
        </ul>
        """
        return html

class UserManager:
    def __init__(self):
        self.auth = auth
        self.ref = db.reference('/users')
        self.yag = yagmail.SMTP('rishavgupta9191@gmail.com', 'Arnav_6969@')
    def check_email_exists(self, email):
        try:
            auth.get_user_by_email(email)
            return True
        except:
            return False

    def send_verification_email(self, email, verification_code):
        subject = "Welcome to AI Wellness Pro - Verify Your Email"
        content = f"""
        <h2>Welcome to AI Wellness Pro!</h2>
        <p>Your verification code is: <strong>{verification_code}</strong></p>
        <p>Enter this code in the app to complete your registration.</p>
        """
        self.yag.send(email, subject, content)

    def edit_profile(self, user_id, data):
        json_data = json.loads(json.dumps(data, cls=CustomJSONEncoder))
        self.ref.child(user_id).update(json_data)
        return True, "Profile updated successfully"


    def delete_account(self, user_id):
        try:
            auth.delete_user(user_id)
            self.ref.child(user_id).delete()
            return True, "Account deleted successfully"
        except:
            return False, "Error deleting account"

# Enhanced UI components

def get_exercise_stats(user_id):
    # Get exercise data from database
    exercises = db.reference(f'/users/{user_id}/exercises').get() or {}
    
    # Convert to DataFrame
    if exercises:
        df = pd.DataFrame(exercises).T
        df['date'] = pd.to_datetime(df['date'])
        return {
            'total_days': len(df['date'].unique()),
            'total_exercises': len(df),
            'total_minutes': df['minutes'].sum(),
            'avg_duration': round(df['minutes'].mean(), 1),
            'current_streak': calculate_streak(df),
            'health_score': calculate_health_score(df)
        }
    return {
        'total_days': 0,
        'total_exercises': 0,
        'total_minutes': 0,
        'avg_duration': 0,
        'current_streak': 0,
        'health_score': 0
    }

def save_exercise(user_id, exercise_data):
    exercise_ref = db.reference(f'/users/{user_id}/exercises')
    exercise_id = str(uuid.uuid4())
    exercise_ref.child(exercise_id).set(exercise_data)

def calculate_streak(df):
    if df.empty:
        return 0
    dates = sorted(df['date'].unique())
    current_streak = 1
    for i in range(len(dates)-1):
        if (dates[i+1] - dates[i]).days == 1:
            current_streak += 1
        else:
            break
    return current_streak

def calculate_health_score(df):
    if df.empty:
        return 0
    recent_exercises = df[df['date'] > datetime.now() - timedelta(days=30)]
    frequency_score = min(len(recent_exercises) / 30 * 100, 100)
    intensity_score = len(recent_exercises[recent_exercises['intensity'] == 'High']) / len(recent_exercises) * 100
    return round((frequency_score + intensity_score) / 2)

def show_profile():
    st.header("👤 Profile Dashboard")
    
    # Profile Header
    col1, col2, col3 = st.columns([1, 2, 1])
    with col1:
        st.image("https://raw.githubusercontent.com/streamlit/streamlit/develop/examples/data/avatar.jpg", width=150)
        uploaded_file = st.file_uploader("Update Photo", type=['jpg', 'png'])
        if uploaded_file:
            st.success("Photo updated!")
    
    with col2:
        st.title(f"Welcome, {st.session_state.get('username', 'User')}!")
        st.caption("Building better habits, one day at a time")
    
    with col3:
        st.metric("Overall Score", "85", "↑ 5")
    
    # Main Tabs
    tabs = st.tabs(["Profile Info", "Health Stats", "Goals", "Settings", "Exercise Log"])
    
    with tabs[0]:  # Profile Info
        with st.form("profile_info"):
            col1, col2 = st.columns(2)
            with col1:
                name = st.text_input("Full Name")
                email = st.text_input("Email")
                dob = st.date_input("Date of Birth", min_value=datetime(1900, 1, 1), max_value=datetime.now())
            with col2:
                phone = st.text_input("Phone")
                location = st.text_input("Location")
                gender = st.selectbox("Gender", ["Select", "Male", "Female", "Other"])
            
            bio = st.text_area("Bio")
            interests = st.multiselect("Interests", 
                ["Fitness", "Meditation", "Nutrition", "Yoga", "Running", "Mental Health"])
            
            if st.form_submit_button("Save Profile"):
                st.success("Profile updated successfully!")
    
    with tabs[1]:  # Health Stats
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Active Days", "45")
            st.metric("Exercise Minutes", "2,340")
        with col2:
            st.metric("Current Streak", "7")
            st.metric("Avg. Daily Steps", "8,500")
        with col3:
            st.metric("Monthly Goal", "80%")
            st.metric("Sleep Score", "85%")
        
        # Health Trends
        st.subheader("Health Trends")
        chart_data = pd.DataFrame({
            'date': pd.date_range(start='2024-01-01', periods=30),
            'exercise': np.random.randint(0, 120, 30),
            'sleep': np.random.randint(5, 9, 30)
        })
        st.line_chart(chart_data.set_index('date'))
    
    with tabs[2]:  # Goals
        st.subheader("Set Your Goals")
        with st.form("goals_form"):
            col1, col2 = st.columns(2)
            with col1:
                daily_steps = st.number_input("Daily Steps Target", 1000, 20000, 10000)
                sleep_hours = st.number_input("Sleep Hours Target", 4, 12, 8)
                exercise_days = st.number_input("Exercise Days/Week", 1, 7, 4)
            with col2:
                water_glasses = st.number_input("Water Glasses/Day", 1, 15, 8)
                meditation_minutes = st.number_input("Meditation Minutes/Day", 5, 60, 15)
                weight_goal = st.number_input("Target Weight (kg)", 40, 150, 70)
            
            if st.form_submit_button("Update Goals"):
                st.success("Goals updated successfully!")
    
    with tabs[3]:  # Settings
        st.subheader("App Settings")
        col1, col2 = st.columns(2)
        with col1:
            st.selectbox("Theme", ["Light", "Dark", "System"])
            st.selectbox("Language", ["English", "Spanish", "French"])
            st.time_input("Daily Reminder Time")
        with col2:
            st.multiselect("Notifications", 
                ["Daily Reminders", "Goal Updates", "Weekly Reports"])
            st.selectbox("Data Privacy", ["Private", "Friends Only", "Public"])
            st.toggle("Enable Analytics")
    
    with tabs[4]:  # Exercise Log
        show_exercise_stats()
        
def show_exercise_stats():
    user_id = st.session_state['user_id']
    stats = get_exercise_stats(user_id)
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Days Active", f"{stats['total_days']} days")
        st.metric("Total Exercises", stats['total_exercises'])
    with col2:
        st.metric("Total Minutes", f"{stats['total_minutes']:,}")
        st.metric("Avg Duration", f"{stats['avg_duration']} min")
    with col3:
        st.metric("Current Streak", f"{stats['current_streak']} days")
    with col4:
        st.metric("Health Score", f"{stats['health_score']}%")

    # Add exercise
    with st.form("add_exercise"):
        st.subheader("Log Exercise")
        col1, col2 = st.columns(2)
        with col1:
            exercise_type = st.selectbox("Type", ["Running", "Yoga", "Strength", "Cycling"])
            duration = st.number_input("Duration (minutes)", 1, 300, 30)
        with col2:
            intensity = st.select_slider("Intensity", ["Low", "Medium", "High"])
            notes = st.text_input("Notes")
        
        if st.form_submit_button("Log Exercise"):
            save_exercise(user_id, {
                'type': exercise_type,
                'minutes': duration,
                'intensity': intensity,
                'notes': notes,
                'date': datetime.now().isoformat()
            })
            st.success("Exercise logged!")
            st.rerun()

    # Clear data option
    if st.button("Clear Exercise History"):
        if st.button("Confirm Clear"):
            db.reference(f'/users/{user_id}/exercises').delete()
            st.success("Exercise history cleared!")
            st.rerun()


def show_settings():
    st.header("⚙️ Advanced Settings")
    
    # Quick Settings
    with st.expander("Quick Settings", expanded=True):
        col1, col2, col3 = st.columns(3)
        with col1:
            st.toggle("Dark Mode")
        with col2:
            st.toggle("Notifications")
        with col3:
            st.toggle("Sound Effects")
    
    # Data Management
    st.subheader("Data Management")
    col1, col2 = st.columns(2)
    with col1:
        st.number_input("Data Retention Period (days)", 30, 365, 90)
    with col2:
        st.selectbox("Data Export Format", ["JSON", "CSV", "PDF"])
    
    if st.button("Export All Data"):
        st.success("Data export initiated!")
    
    # Integration Settings
    st.subheader("Integrations")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.toggle("Google Fit")
    with col2:
        st.toggle("Apple Health")
    with col3:
        st.toggle("Fitbit")
    
    # Privacy Settings
    with st.form("privacy_settings"):
        st.subheader("Privacy Settings")
        st.multiselect("Data Sharing", 
            ["Anonymous Usage Stats", "Wellness Insights", "Community Features"])
        st.selectbox("Profile Visibility", ["Public", "Friends Only", "Private"])
        
        col1, col2 = st.columns(2)
        with col1:
            st.toggle("Allow Research Use")
        with col2:
            st.toggle("Show Profile in Search")
            
        if st.form_submit_button("Save Privacy Settings"):
            st.success("Privacy settings updated!")
    
    # Advanced Features
    st.subheader("Advanced Features")
    with st.expander("AI Features"):
        st.slider("AI Recommendation Frequency", 0, 10, 5)
        st.multiselect("AI Analysis Focus", 
            ["Sleep Patterns", "Exercise Impact", "Mood Correlation", "Habit Formation"])
    
    with st.expander("Backup Settings"):
        st.selectbox("Backup Frequency", ["Daily", "Weekly", "Monthly"])
        st.text_input("Backup Email")
        if st.button("Configure Backup"):
            st.success("Backup settings saved!")



def schedule_reports():
    while True:
        # Get all users with email reports enabled
        users = db.collection('users').where('settings.email_reports', '==', True).stream()
        
        reporter = EmailReporter()
        data_manager = DataManager()
        
        for user in users:
            user_data = user.to_dict()
            checkins = data_manager.get_user_checkins(user.id)
            
            if checkins:
                reporter.send_report(user_data['email'], checkins)
        
        # Sleep for 24 hours
        time.sleep(86400)

def auth_page():
    st.title("🌟 AI Wellness Pro")
    
    tab1, tab2 = st.tabs(["Sign In", "Create Account"])
    
    with tab1:
        with st.form("signin_form"):
            email = st.text_input("Email")
            password = st.text_input("Password", type="password")
            remember = st.checkbox("Remember me")
            
            col1, col2 = st.columns([1, 1])
            with col1:
                if st.form_submit_button("Sign In"):
                    auth = FirebaseAuth()
                    success, result = auth.sign_in(email, password)
                    if success:
                        st.session_state['user_id'] = result
                        st.success("Welcome back!")
                        st.experimental_rerun()
            with col2:
                if st.form_submit_button("Forgot Password?"):
                    if email:
                        # Implement password reset
                        st.info("Password reset link sent to your email")
    
    with tab2:
        with st.form("signup_form"):
            st.write("Join AI Wellness Pro")
            
            email = st.text_input("Email")
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            confirm_password = st.text_input("Confirm Password", type="password")
            
            agree_terms = st.checkbox("I agree to the Terms and Privacy Policy")
            
            if st.form_submit_button("Create Account"):
                if not agree_terms:
                    st.error("Please agree to the terms")
                    return
                
                user_manager = UserManager()
                if user_manager.check_email_exists(email):
                    st.error("Email already registered")
                    return
                
                if password != confirm_password:
                    st.error("Passwords don't match")
                    return
                
                verification_code = ''.join(random.choices('0123456789', k=6))
                user_manager.send_verification_email(email, verification_code)
                
                st.session_state['pending_verification'] = {
                    'email': email,
                    'password': password,
                    'username': username,
                    'code': verification_code
                }
                st.info("Please check your email for verification code")



client = InferenceClient(
    model="tiiuae/falcon-7b-instruct",
    token="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"
)
# Database setup
engine = create_engine('sqlite:///wellness_pro_v3.db')
Base = declarative_base()

class CheckIn(Base):
    __tablename__ = 'checkins'
    id = Column(Integer, primary_key=True)
    date = Column(DateTime, default=datetime.utcnow)
    mood = Column(String(50))
    energy_level = Column(String(50))
    stress_level = Column(Integer)
    sleep_hours = Column(Float)
    exercise_minutes = Column(Integer)
    water_glasses = Column(Integer)
    nutrition_rating = Column(Integer)
    meditation_minutes = Column(Integer)
    productivity_rating = Column(Integer)
    social_interaction_hours = Column(Float)
    screen_time_hours = Column(Float)
    outdoor_time_minutes = Column(Integer)
    journal_entry = Column(Text)
    gratitude_notes = Column(Text)
    goals_completed = Column(Integer)
    habit_streaks = Column(Text)

Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)
session = Session()

def calculate_wellness_score(data):
    weights = {
        'sleep': 0.2,
        'exercise': 0.2,
        'stress': 0.15,
        'nutrition': 0.15,
        'mood': 0.1,
        'meditation': 0.1,
        'social': 0.1
    }
    
    scores = {
        'sleep': min(data['sleep_hours'] / 8 * 10, 10),
        'exercise': min(data['exercise_minutes'] / 60 * 10, 10),
        'stress': 10 - data['stress_level'],
        'nutrition': data['nutrition_rating'],
        'meditation': min(data['meditation_minutes'] / 20 * 10, 10),
        'social': min(data['social_interaction_hours'] / 2 * 10, 10)
    }
    
    mood_scores = {
        'Happy': 10, 'Energetic': 10, 'Content': 9,
        'Calm': 8, 'Tired': 6, 'Stressed': 5, 'Anxious': 4
    }
    scores['mood'] = mood_scores.get(data['mood'], 5)
    
    return sum(score * weights[metric] for metric, score in scores.items())

def get_ai_recommendations(data):
    categories = {
        "PHYSICAL WELLNESS": """
        Analyze physical metrics:
        - Sleep: {sleep_hours} hours
        - Exercise: {exercise_minutes} minutes
        - Energy: {energy_level}
        
        Provide 3 specific physical wellness recommendations.
        """,
        
        "MENTAL WELLBEING": """
        Analyze mental state:
        - Mood: {mood}
        - Stress: {stress_level}/10
        - Meditation: {meditation_minutes} minutes
        
        Provide 3 specific mental wellness recommendations.
        """,
        
        "LIFESTYLE BALANCE": """
        Analyze lifestyle:
        - Screen time: {screen_time_hours} hours
        - Social time: {social_interaction_hours} hours
        - Outdoor time: {outdoor_time_minutes} minutes
        
        Provide 3 specific lifestyle balance recommendations.
        """,
        
        "NUTRITION & HYDRATION": """
        Analyze nutrition:
        - Water: {water_glasses} glasses
        - Nutrition rating: {nutrition_rating}/10
        
        Provide 3 specific nutrition and hydration recommendations.
        """
    }
    
    recommendations = {}
    for category, prompt_template in categories.items():
        prompt = prompt_template.format(**data)
        try:
            response = client.text_generation(prompt)
            recommendations[category] = response
        except Exception as e:
            recommendations[category] = "Unable to generate recommendations."
    
    return recommendations


def show_checkin():
    st.header("📝 Daily Wellness Check-In")
    
    with st.form("checkin_form"):
        col1, col2, col3 = st.columns(3)
        
        with col1:
            mood = st.selectbox("Current Mood", 
                ["Happy", "Energetic", "Calm", "Stressed", "Tired", "Anxious", "Content"])
            energy_level = st.selectbox("Energy Level", ["Low", "Moderate", "High"])
            stress_level = st.slider("Stress Level", 1, 10, 5)
            sleep_hours = st.number_input("Sleep Hours", 0.0, 24.0, 7.0, 0.5)
        
        with col2:
            exercise_minutes = st.number_input("Exercise Minutes", 0, 300, 30)
            water_glasses = st.number_input("Water Glasses", 0, 20, 6)
            nutrition_rating = st.slider("Nutrition Rating", 1, 10, 7)
            meditation_minutes = st.number_input("Meditation Minutes", 0, 120, 10)
        
        with col3:
            productivity_rating = st.slider("Productivity", 1, 10, 7)
            social_interaction_hours = st.number_input("Social Time (hours)", 0.0, 24.0, 2.0)
            screen_time_hours = st.number_input("Screen Time (hours)", 0.0, 24.0, 8.0)
            outdoor_time_minutes = st.number_input("Outdoor Time (minutes)", 0, 480, 30)
        
        gratitude = st.text_area("What are you grateful for today?")
        journal = st.text_area("Journal Entry (Optional)")
        
        submitted = st.form_submit_button("Submit Check-in")
        
        if submitted:
            save_checkin(locals())
            show_recommendations(locals())

def save_checkin(data):
    try:
        new_checkin = CheckIn(
            mood=data['mood'],
            energy_level=data['energy_level'],
            stress_level=data['stress_level'],
            sleep_hours=data['sleep_hours'],
            exercise_minutes=data['exercise_minutes'],
            water_glasses=data['water_glasses'],
            nutrition_rating=data['nutrition_rating'],
            meditation_minutes=data['meditation_minutes'],
            productivity_rating=data['productivity_rating'],
            social_interaction_hours=data['social_interaction_hours'],
            screen_time_hours=data['screen_time_hours'],
            outdoor_time_minutes=data['outdoor_time_minutes'],
            gratitude_notes=data['gratitude'],
            journal_entry=data['journal']
        )
        session.add(new_checkin)
        session.commit()
        
        wellness_score = calculate_wellness_score(data)
        st.success(f"Check-in saved! Your Wellness Score: {wellness_score:.1f}/10")
        
    except Exception as e:
        st.error(f"Error saving check-in: {str(e)}")

def show_recommendations(data):
    st.header("🎯 Your Personalized Wellness Plan")
    
    recommendations = get_ai_recommendations(data)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("🏃‍♂️ Physical Wellness")
        st.write(recommendations["PHYSICAL WELLNESS"])
        
        st.subheader("🧘‍♂️ Mental Wellbeing")
        st.write(recommendations["MENTAL WELLBEING"])
    
    with col2:
        st.subheader("⚡ Lifestyle Balance")
        st.write(recommendations["LIFESTYLE BALANCE"])
        
        st.subheader("🥗 Nutrition & Hydration")
        st.write(recommendations["NUTRITION & HYDRATION"])

def show_dashboard():
    st.header("📊 Wellness Dashboard")
    
    checkins = session.query(CheckIn).all()
    if not checkins:
        st.info("Complete your first check-in to see your dashboard!")
        return
    
    # Convert to DataFrame
    df = pd.DataFrame([{
        'date': c.date,
        'mood': c.mood,
        'stress': c.stress_level,
        'sleep': c.sleep_hours,
        'exercise': c.exercise_minutes,
        'meditation': c.meditation_minutes,
        'productivity': c.productivity_rating,
        'social': c.social_interaction_hours,
        'screen': c.screen_time_hours,
        'outdoor': c.outdoor_time_minutes
    } for c in checkins])
    
    # Overview metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Average Sleep", f"{df['sleep'].mean():.1f} hrs")
    with col2:
        st.metric("Exercise Frequency", f"{(df['exercise'] > 0).mean()*100:.0f}%")
    with col3:
        st.metric("Avg Stress", f"{df['stress'].mean():.1f}/10")
    with col4:
        st.metric("Meditation", f"{df['meditation'].mean():.0f} min")
    
    # Visualizations
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Mood Distribution")
        fig = px.pie(df, names='mood', title='Mood Patterns')
        st.plotly_chart(fig)
        
        st.subheader("Sleep Pattern")
        fig = px.line(df, x='date', y='sleep', title='Sleep Hours')
        st.plotly_chart(fig)
    
    with col2:
        st.subheader("Stress vs Exercise")
        fig = px.scatter(df, x='exercise', y='stress', 
                        title='Exercise Impact on Stress',
                        trendline="ols")
        st.plotly_chart(fig)
        
        st.subheader("Activity Minutes")
        fig = go.Figure()
        fig.add_trace(go.Bar(name='Exercise', x=df['date'], y=df['exercise']))
        fig.add_trace(go.Bar(name='Outdoor', x=df['date'], y=df['outdoor']))
        fig.update_layout(barmode='group', title='Daily Activity Minutes')
        st.plotly_chart(fig)

def show_achievements():
    st.header("🏆 Achievements & Streaks")
    
    achievements = [
        {"name": "Early Bird", "desc": "7-day streak of 7+ hours sleep", "icon": "💫"},
        {"name": "Fitness Warrior", "desc": "Exercise 30+ minutes for 5 days", "icon": "💪"},
        {"name": "Zen Master", "desc": "10-day meditation streak", "icon": "🧘‍♂️"},
        {"name": "Hydration Hero", "desc": "8 glasses water daily for a week", "icon": "💧"},
        {"name": "Outdoor Explorer", "desc": "60+ minutes outside for 5 days", "icon": "🌳"},
        {"name": "Gratitude Guru", "desc": "Daily gratitude notes for 7 days", "icon": "🙏"}
    ]
    
    for achievement in achievements:
        col1, col2 = st.columns([1, 4])
        with col1:
            st.write(achievement["icon"])
        with col2:
            st.write(f"**{achievement['name']}**")
            st.write(achievement["desc"])

def show_habits():
    st.header("📈 Habit Tracker")
    
    habits = [
        "Morning Meditation",
        "Exercise",
        "8h Sleep",
        "Healthy Meals",
        "Water Intake",
        "Reading",
        "Journaling",
        "Outdoor Time"
    ]
    
    days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    
    st.subheader("This Week's Habits")
    
    # Create habit tracking grid
    for habit in habits:
        cols = st.columns([3] + [1]*7)
        
        cols[0].write(habit)
        for i, day in enumerate(days, 1):
            cols[i].checkbox("", key=f"{habit}_{day}")

def show_journal():
    st.header("📔 Wellness Journal")
    
    # Journal entry
    st.subheader("New Entry")
    with st.form("journal_form"):
        date = st.date_input("Date")
        mood = st.selectbox("Mood", ["Happy", "Calm", "Anxious", "Stressed", "Sad"])
        entry = st.text_area("Write your thoughts...")
        tags = st.multiselect("Tags", ["Gratitude", "Achievement", "Challenge", "Learning"])
        submit = st.form_submit_button("Save Entry")
        
        if submit:
            st.success("Journal entry saved!")

def show_goals():
    st.header("🎯 Goals & Progress")
    
    # Set new goals
    st.subheader("Set New Goal")
    with st.form("goal_form"):
        goal_type = st.selectbox("Category", 
            ["Exercise", "Sleep", "Nutrition", "Mental Wellness", "Social", "Custom"])
        description = st.text_input("Goal Description")
        target_date = st.date_input("Target Date")
        metrics = st.text_input("Success Metrics")
        submit_goal = st.form_submit_button("Set Goal")
        
        if submit_goal:
            st.success("Goal set successfully!")
    
    # Show active goals
    st.subheader("Active Goals")
    goals = [
        {"type": "Exercise", "desc": "Run 5k", "progress": 60},
        {"type": "Sleep", "desc": "8 hours daily", "progress": 80},
        {"type": "Meditation", "desc": "Daily practice", "progress": 40}
    ]
    
    for goal in goals:
        col1, col2 = st.columns([3, 1])
        with col1:
            st.write(f"**{goal['type']}**: {goal['desc']}")
            st.progress(goal['progress'] / 100)
        with col2:
            st.write(f"{goal['progress']}%")

def show_analysis():
    st.header("🔍 Advanced Wellness Analysis")
    
    checkins = session.query(CheckIn).all()
    if not checkins:
        st.info("Start tracking to see your analysis!")
        return
    
    df = pd.DataFrame([{
        'date': c.date,
        'mood': c.mood,
        'stress': c.stress_level,
        'sleep': c.sleep_hours,
        'exercise': c.exercise_minutes,
        'meditation': c.meditation_minutes,
        'social': c.social_interaction_hours
    } for c in checkins])
    
    # Correlation analysis
    st.subheader("Factor Correlations")
    corr = df[['stress', 'sleep', 'exercise', 'meditation', 'social']].corr()
    fig = px.imshow(corr, title='Wellness Factor Correlations')
    st.plotly_chart(fig)
    
    # Mood analysis
    st.subheader("Mood Patterns")
    mood_counts = df['mood'].value_counts()
    fig = px.bar(x=mood_counts.index, y=mood_counts.values, title='Mood Distribution')
    st.plotly_chart(fig)
    
    # Time series analysis
    st.subheader("Trends Over Time")
    metrics = ['sleep', 'exercise', 'stress']
    fig = go.Figure()
    for metric in metrics:
        fig.add_trace(go.Scatter(x=df['date'], y=df[metric], name=metric.capitalize()))
    fig.update_layout(title='Wellness Metrics Over Time')
    st.plotly_chart(fig)

def show_reports():
    st.header("📊 Wellness Reports")
    
    report_type = st.selectbox("Report Type", 
        ["Weekly Summary", "Monthly Analysis", "Custom Period", "Trends Report"])
    
    date_range = st.date_input("Date Range", 
        [datetime.datetime.now() - timedelta(days=30), datetime.datetime.now()])
    
    if st.button("Generate Report"):
        checkins = session.query(CheckIn).all()
        if not checkins:
            st.info("No data available for report generation.")
            return
        
        df = pd.DataFrame([{
            'date': c.date,
            'mood': c.mood,
            'sleep': c.sleep_hours,
            'exercise': c.exercise_minutes,
            'stress': c.stress_level
        } for c in checkins])
        
        st.subheader("Report Summary")
        col1, col2 = st.columns(2)
        
        with col1:
            st.metric("Average Sleep", f"{df['sleep'].mean():.1f} hours")
            st.metric("Exercise Sessions", f"{(df['exercise'] > 0).sum()}")
        
        with col2:
            st.metric("Average Stress", f"{df['stress'].mean():.1f}/10")
            st.metric("Most Common Mood", df['mood'].mode()[0])
        
        # Download report
        report_csv = df.to_csv(index=False)
        st.download_button(
            label="Download Report",
            data=report_csv,
            file_name="wellness_report.csv",
            mime="text/csv"
        )

def main():
    if 'user_id' not in st.session_state:
        st.session_state['user_id'] = None

    # Show auth page if user is not logged in
    if not st.session_state['user_id']:
        auth_page()
        return

    # Modified main navigation to include user profile
    st.sidebar.title("🌟 AI Wellness Pro")
    
    pages = {
        "Daily Check-In": show_checkin,
        "Dashboard": show_dashboard,
        "Achievements": show_achievements,
        "Habit Tracker": show_habits,
        "Journal": show_journal,
        "Goals": show_goals,
        "Analysis": show_analysis,
        "Reports": show_reports,
        "Profile": show_profile,
        "Exercise Stats": show_exercise_stats,
        "Settings": show_settings
    }
    # User profile section with safe data access
    auth = FirebaseAuth()
    user_data = auth.get_user_data(st.session_state['user_id']) or {}
    
    with st.sidebar:
        st.write(f"Welcome, {user_data.get('username', 'Guest')}!")
        if st.button("Sign Out"):
            st.session_state['user_id'] = None
            st.experimental_rerun()
    
    # Rest of your navigation and pages
    
    page = st.sidebar.selectbox("Navigate", list(pages.keys()))
    pages[page]()

    # Rest of your existing navigation and pages...


# Modified save_checkin function to use Firebase
def save_checkin(data):
    try:
        ref = db.reference('/checkins')
        new_checkin = {
            'mood': data['mood'],
            'energy_level': data['energy_level'],
            'stress_level': data['stress_level'],
            'sleep_hours': data['sleep_hours'],
            'exercise_minutes': data['exercise_minutes'],
            'water_glasses': data['water_glasses'],
            'nutrition_rating': data['nutrition_rating'],
            'meditation_minutes': data['meditation_minutes'],
            'productivity_rating': data['productivity_rating'],
            'social_interaction_hours': data['social_interaction_hours'],
            'screen_time_hours': data['screen_time_hours'],
            'outdoor_time_minutes': data['outdoor_time_minutes'],
            'gratitude_notes': data['gratitude'],
            'journal_entry': data['journal'],
            'timestamp': datetime.now().isoformat()
        }
        
        # Push new checkin to database
        ref.push(new_checkin)
        
        wellness_score = calculate_wellness_score(data)
        st.success(f"Check-in saved! Your Wellness Score: {wellness_score:.1f}/10")
        
    except Exception as e:
        st.error(f"Error saving check-in: {str(e)}")


if __name__ == "__main__":
    main()