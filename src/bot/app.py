# Standard Library Imports
import json
import re
import threading

# Third-Party Imports
import pandas as pd
import streamlit as st
from st_aggrid import AgGrid, GridOptionsBuilder

# Local Application/Library Specific Imports
from common.database import Database
from common.email_manager import EmailManager
from common.email_manager import EmailManager

from digiscientiabot import DigiScientiaBot
from logging_config import setup_logger, LogBuffer

logger = setup_logger()

# Initialize database and email details, load configuration from JSON file
config_path = '../common/config.json'
with open(config_path) as config_file:
    config = json.load(config_file)
db = Database(uri=config["MONGO_DB_URI"])
email_manager = EmailManager(sender_email=config["EMAIL_SENDER"], sender_password=config["EMAIL_PASSWORD"])

def submit_abstract_form():
    try:
        with st.form("abstract_submission"):
            st.write("#### Abstract Submission")
            title = st.text_input("Abstract Title: *", help="Required")
            abstract = st.text_area("Abstract:")
            keywords = st.text_input("Keywords:")
            author = st.text_input("Corresponding Author: *", help="Required")
            author_email = st.text_input("Author E-Mail: *", help="Required")
            author_orcid = st.text_input("Author ORCID: *", help="Required")
            coauthors = st.text_input("Co-authors:")
            link = st.text_input("BioRxiv Link: *", placeholder="https://", help="Required")

            submitted = st.form_submit_button("Submit Abstract")
            if submitted:
                if not title or not author or not author_email or not author_orcid or not link:
                    st.error("Please fill in all the required fields marked with an asterisk (*)")
                elif not re.match(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', author_email):
                    st.error("Invalid email format. Please correct the email and try again.")
                else:
                    submission_number = db.increment_abstract_count()
                    abstract_data = {
                        "submission_number": submission_number,
                        "title": title,
                        "abstract": abstract,
                        "keywords": keywords,
                        "author": author,
                        "author_email": author_email,
                        "author_orcid": author_orcid,
                        "coauthors": coauthors,
                        "link": link,
                        "submitted_date": db.current_datetime(),
                        "last_updated": db.current_datetime()
                    }
                    db.insert_abstract(abstract_data)
                    email_body = f"New submission received:\nSubmission Number: {submission_number}\nTitle: {title}\nAbstract: {abstract}"
                    email_manager.send_email("New Abstract Submission", email_body, author_email)
                    #email_manager.send_email("New Abstract Submission", email_body, jm_email)
                    st.success(f"Abstract submitted successfully!\nSubmission Number: {submission_number}")
    except Exception as e:
        st.error(f"An error occurred: {str(e)}")

def submit_review_form():
    try:
        with st.form("review_submission"):
            st.write("#### Review Submission")
            submission_number = st.text_input("Submission Number: *", help="Required")
            paper_title = st.text_input("Paper Title: *", help="Required")
            reviewer_name = st.text_input("Reviewer Name: *", help="Required")
            reviewer_email = st.text_input("Reviewer E-Mail: *", help="Required")
            review_text = st.text_area("Review Text: *", help="Required")
            score = st.number_input("Score (1-10): *", min_value=1, max_value=10, value=1, help="Required")
            recommendation = st.selectbox("Recommendation:* ", ["Accept", "Minor Revision", "Major Revision", "Reject"], help="Required")

            submitted = st.form_submit_button("Submit Review")
            if submitted:
                if not (submission_number and paper_title and reviewer_name and reviewer_email and review_text and score and recommendation):
                    st.error("Please fill in all the required fields marked with an asterisk (*)")
                elif not re.match(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', reviewer_email):
                    st.error("Invalid email format. Please correct the email and try again.")
                elif not db.abstract_exists(int(submission_number)):
                    st.error("No abstract found with the given submission number.")
                else:
                    review_data = {
                        "submission_number": int(submission_number),
                        "paper_title": paper_title,
                        "reviewer_name": reviewer_name,
                        "reviewer_email": reviewer_email,
                        "review_text": review_text,
                        "score": score,
                        "recommendation": recommendation
                    }
                    db.insert_review(review_data)
                    email_body = f"New review submitted:\nSubmission Number: {submission_number}\nReviewer: {reviewer_name}\nScore: {score}\nRecommendation: {recommendation}"
                    email_manager.send_email("New Review Submission Notification", email_body, reviewer_email)
                    st.success(f"Review submitted successfully!\nSubmission Number: {submission_number}")
    except Exception as e:
        st.error(f"An error occurred: {str(e)}")

def bot_dash():
    try:
        #st.divider()
        st.write("##### Reviewers selected for the latest submission:")
        results_data, submission_number = db.get_results()
        if results_data:
            # Convert the list of dictionaries to a DataFrame
            df = pd.DataFrame(results_data)
            # Only select the columns you want to display
            df = df[['Last_author', 'Email', 'Cosine_similarity']]
            # Rename columns as specified
            df.rename(columns={
                'Last_author': 'Reviewer',
                'Email': 'Email',
                'Cosine_similarity': 'Similarity Score (%)'
            }, inplace=True)
            st.write(f"The top three best matched reviewers for the abstract submission #{submission_number}:")
            # Display the DataFrame with styling
            st.dataframe(df.style.set_properties(**{
                'background-color': 'white', 
                'color': 'black', 
                'border-color': 'gray'
            }))
        else:
            st.write("No results found.")
        st.divider()
        st.write("###### Processed Submissions (Accepted Papers):")
        accepted_papers = db.get_accepted_papers()
        if accepted_papers:
            # Create DataFrame from accepted papers
            accepted_df = pd.DataFrame(accepted_papers)
            # Reorder the DataFrame columns as specified
            accepted_df = accepted_df[['Author', 'Title', 'Average Score', 'Acceptance Count']]
            # Display the table
            st.table(accepted_df)
        else:
            st.write("No accepted papers currently.")
    except Exception as e:
        st.error(f"An error occurred: {e}")
    
def journal_intro():
    # st.header(':blue[DigiScientia]:green[*]', divider='rainbow')

    st.markdown('#### DigiScientia:green[<sup>:star:</sup>]', unsafe_allow_html=True)
    #st.markdown('#### DigiScientia:green[*:star:] <sup>:star:</sup> Journal', unsafe_allow_html=True)
    #st.markdown('# :blue[DigiScientia]:green[*] Journal', unsafe_allow_html=True)

    st.markdown('''
                Embark on a journey towards a more equitable and transparent academic publishing process with DigiScientia.

                We understand the frustrations inherent in the traditional peer review process - the delays, the lack of transparency, unrewarded efforts and unrecognized contributions. That's why we are revolutionizing the system.

                At DigiScientia, we harness the power of AI to match manuscripts with suitable reviewers. Our technology ensures diversity, equity and inclusivity.

                Our commitment to quality remains unwavering; every review is meticulously conducted by experts in the field to uphold academic rigor. Our new interface allows straight-forward assessment and integrity checks.

                As researchers ourselves, we value your time and expertise. That's why, for the first time, we offer fair compensation to reviewers for their invaluable contributions to the peer-review process.

                We ensure transparency by publishing peer-review files alongside all articles.

                Knowledge should be free. We are open access forever.

                Join the movement towards a more rewarding publishing experience. Submit your abstract below.
            ''')  
    
    #st.markdown('<sup>:star:</sup>', unsafe_allow_html=True)

def bot_logs():

    #st.set_page_config(page_title="DigiScientia Bot Dashboard", layout="wide")
    st.write("#### DigiScientia Bot Dashboard")

    def bot_thread_function():
        bot_instance = DigiScientiaBot()
        bot_instance.run_bot()

    if st.button('Start Bot'):
        thread = threading.Thread(target=bot_thread_function, name='BotThread')
        thread.start()
        st.success("Bot started.")

    if st.button('Stop Bot'):
        if 'bot_instance' in globals() and bot_instance is not None:
            bot_instance.terminate()
            st.success("Bot stopped.")
        else:
            st.error("No running bot to stop.")

    # Create a placeholder for the log display area only once
    if 'log_area' not in st.session_state:
        st.session_state.log_area = st.empty()

    def refresh_logs():
        with LogBuffer.lock:
            logs_to_display = list(LogBuffer.buffer)
            LogBuffer.buffer.clear()
        if 'logs' not in st.session_state:
            st.session_state['logs'] = []
        st.session_state['logs'].extend(logs_to_display)
        # Correctly update the text area for logs
        st.session_state.log_area.text_area("Logs", value="\n".join(st.session_state['logs']), height=400, key="unique_log_key")

    st.button("Refresh Logs", on_click=refresh_logs)

    #Initialize the text area to display logs
    if 'logs' in st.session_state:
        st.session_state.log_area.text_area("Logs", value="\n".join(st.session_state['logs']), height=400, key="unique_log_key")
    else:
        st.session_state.log_area.text_area("Logs", value="", height=400, key="unique_log_key")

def main():
    db.initialize_submission_counter()

    st.header(':blue[DigiScientia]:green[*] Journal:', divider='rainbow')
    #st.markdown('# :blue_heart: DigiScientia <sup>:star:</sup> Journal', unsafe_allow_html=True)
    #st.markdown('# :blue[DigiScientia]:green[*] Journal', unsafe_allow_html=True)

    st.markdown('''
                _Revolutionizing academic publishing with a streamlined, fair, and transparent peer review process powered by AI, 
                recognizing and rewarding contributions, and committed to open access._
                ''')
    # st.markdown("---")
    #st.divider()

    tab1, tab2, tab3, tab4, tab5 = st.tabs(["Journal Intro", "Submit Abstract", "Submit Review", "Bot Dashboard", "Bot Logs"])
    # tab1, tab2, tab3, tab4, tab5 = st.tabs(["Journal Intro", "Submit Abstract", "Submit Review", "View Abstracts", "Bot Dashboard"])

    with tab1:
        # st.write("Tab 1 Active")
        journal_intro()
    with tab2:
        submit_abstract_form()
    with tab3:
        submit_review_form()
    # with tab4:
    #     view_abstracts()
    with tab4:
        bot_dash()
    with tab5:
        bot_logs()

if __name__ == "__main__":
    main()