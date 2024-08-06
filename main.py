import streamlit as st
from dotenv import load_dotenv
import os
import imaplib
import email
from email.header import decode_header
from langchain.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_groq import ChatGroq
from datetime import datetime
from streamlit_option_menu import option_menu
import base64

# Load environment variables
load_dotenv()
api_key = os.getenv('groq_api_key')

# Initialize the Groq model
model = ChatGroq(api_key="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", model_name='llama3-8b-8192')
parser = StrOutputParser()

# IMAP email retrieval
def fetch_latest_emails(username, password, num_emails=5):
    mail = imaplib.IMAP4_SSL("imap.gmail.com")
    mail.login(username, password)
    mail.select("inbox")
    status, messages = mail.search(None, "ALL")
    email_ids = messages[0].split()[-num_emails:]

    emails = []
    for email_id in email_ids:
        status, msg_data = mail.fetch(email_id, "(RFC822)")
        msg = email.message_from_bytes(msg_data[0][1])
        subject, encoding = decode_header(msg["Subject"])[0]
        if isinstance(subject, bytes):
            subject = subject.decode(encoding if encoding else "utf-8")
        from_ = msg.get("From")
        date_ = msg.get("Date")
        body = ""
        attachments = []
        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                content_disposition = str(part.get("Content-Disposition"))
                try:
                    body = part.get_payload(decode=True).decode()
                except:
                    pass
                if content_type == "text/plain" and "attachment" not in content_disposition:
                    break
                elif "attachment" in content_disposition:
                    filename = part.get_filename()
                    if filename:
                        attachments.append(filename)
        else:
            content_type = msg.get_content_type()
            body = msg.get_payload(decode=True).decode()

        emails.append({
            "id": email_id.decode(),
            "subject": subject,
            "from": from_,
            "date": date_,
            "body": body,
            "attachments": attachments
        })
    mail.close()
    mail.logout()
    return emails

def classify_email(subject, from_, date_, body, attachments):
    template = """
    As an expert in email analysis, classify the following email based on its content. 
    Determine if it is spam or not and if it is a phishing attempt or not. Additionally, perform sentiment analysis.
    Also, provide a brief summary of what this email is about.

    Email details:
    Subject: {subject}
    From: {from_}
    Date: {date_}
    Body: {body}
    Attachments: {attachments}
    """
    prompt = PromptTemplate.from_template(template=template)
    chain = prompt | model | parser

    email_content = {
        "subject": subject,
        "from_": from_,
        "date_": date_,
        "body": body,
        "attachments": ", ".join(attachments) if attachments else "None"
    }

    result = chain.invoke(email_content)
    return result

# Streamlit
# Placeholder for session state
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "user_history" not in st.session_state:
    st.session_state.user_history = []
if "emails" not in st.session_state:
    st.session_state.emails = []

@st.cache_data
def get_img_as_base64(file):
    with open(file, "rb") as f:
        data = f.read()
    return base64.b64encode(data).decode()

img = get_img_as_base64("images\login.jpg")

page_bg_img = f"""
<style>
[data-testid="stAppViewContainer"] > .main {{
background-image: url("https://img.freepik.com/free-vector/gradient-connection-background_23-2150441893.jpg?t=st=1722228269~exp=1722231869~hmac=5631f59bf1b38d9e05f63b43d0c12d7aaddc276f0199e3aa1bce22ba6f05337e&w=996");
background-size: 100%;
background-repeat: no-repeat;
background-position: right;

}}

[data-testid="stSidebar"] > div:first-child {{
background-image: url("data:image/png;base64,{img}");
background-position: center; 
background-repeat: no-repeat;
background-attachment: fixed;
}}

[data-testid="stHeader"] {{
background: rgba(0,0,0,0);
}}

[data-testid="stToolbar"] {{
right: 2rem;
}}
</style>
"""

st.markdown(page_bg_img, unsafe_allow_html=True)

def login_page():
    st.title("Login")
    placeholder = st.empty()
    with placeholder.form(key="login_form"):
        st.markdown('<div class="login-container">', unsafe_allow_html=True)
        username = st.text_input("Email:")
        password = st.text_input("Email App Password:", type="password")
        st.markdown('<div class="center">', unsafe_allow_html=True)
        submit = st.form_submit_button("Submit")
        st.markdown('</div>', unsafe_allow_html=True)

    if submit:
        if username and password:
            st.session_state.authenticated = True
            st.session_state.username = username
            st.session_state.password = password
            st.success("Logged in successfully!")
        else:
            st.error("Invalid username or password")

def homepage():
    st.title("Smart Email Classifier")
    
    if st.session_state.authenticated:
        num_emails_option = st.selectbox("Number of emails to fetch:", options=[5, 10, 50, 100, "All"])
        num_emails = None if num_emails_option == "All" else num_emails_option
        
        if st.button("Fetch Emails"):
            with st.spinner("Fetching the latest emails..."):
                try:
                    st.session_state.emails = fetch_latest_emails(st.session_state.username, st.session_state.password, num_emails)
                    st.success("Emails fetched successfully!")
                except Exception as e:
                    st.error(f"An error occurred: {e}")
        
        if st.session_state.emails:
            email_options = [f"{email['from']} ({email['id']})" for email in st.session_state.emails]
            selected_email_option = st.selectbox("Select an email to classify:", email_options)
            
            if selected_email_option:
                selected_email_id = selected_email_option.split(" (")[1][:-1]  # Extract the email ID from the option
                selected_email = next(email for email in st.session_state.emails if email["id"] == selected_email_id)
                
                subject = selected_email["subject"]
                from_ = selected_email["from"]
                date_ = selected_email["date"]
                body = selected_email["body"]
                attachments = selected_email["attachments"]
                
                classification_result = classify_email(subject, from_, date_, body, attachments)
                
                # Save to history
                st.session_state.user_history.append({
                    "datetime": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "subject": subject,
                    "from": from_,
                    "date": date_,
                    "body": body,
                    "result": classification_result
                })
                
                st.write(f"**Subject:** {subject}")
                st.write(f"**From:** {from_}")
                st.write(f"**Date:** {date_}")
                
                # Use expander to show email body
                with st.expander("More..."):
                    st.write(f"**Body:** {body}")
                st.write(f"**Attachments:** {', '.join(attachments) if attachments else 'None'}")
                st.write("**Classification Result**")
                st.write(classification_result)
    else:
        st.error("Please log in to fetch and classify emails.")

def user_profile_page():
    st.title("User Profile")
    if st.session_state.authenticated:
        st.write(f"Logged in as: {st.session_state.username}")
    else:
        st.error("Please log in to view your profile.")

def history_page():
    st.title("History")
    if st.session_state.authenticated:
        if st.session_state.user_history:
            for record in st.session_state.user_history:
                st.write(f"**Date and Time:** {record['datetime']}")
                st.write(f"**Subject:** {record['subject']}")
                st.write(f"**From:** {record['from']}")
                st.write(f"**Date:** {record['date']}")
                st.write(f"**Body:** {record['body']}")
                st.write(f"**Result:** {record['result']}")
                st.write("---")
        else:
            st.write("No history available.")
    else:
        st.error("Please log in to view your history.")

def about_us_page():
    st.title("About Us")
    st.write("This app was developed to help users classify and analyze their emails efficiently. This app classifies whether an email is spam or not, and whether it is a phishing attack. It also performs sentiment analysis and provides a summary of the email content")

def main():
    selected = option_menu(
        menu_title=None,  
        options=["Home", "Login", "Profile", "History", "About Us"],
        icons=['house', 'envelope', 'person', 'clock', 'info-circle'],
        menu_icon="cast", default_index=0,
        orientation="horizontal",
        styles={
         "container": {"padding": "0!important", "background-color": "black"},
        "icon": {"color": "white", "font-size": "16px"}, 
        "nav-link": {"font-size": "16px", "text-align": "left", "margin": "0px", "--hover-color": "red"},
        "nav-link-selected": {"background-color": "blue"},
        },
    )

    # Sidebar for navigation
    st.sidebar.title("Navigation")
    page = st.sidebar.radio("", ["Home", "Login", "Profile", "History", "About Us"])

    if selected == "Login":
        login_page()
    elif selected == "Profile":
        user_profile_page()
    elif selected == "History":
        history_page()
    elif selected == "About Us":
        about_us_page()
    else:
        homepage()

if __name__ == "__main__":
    main()
