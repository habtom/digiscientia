import json
import streamlit as st
import re
import pandas as pd
from st_aggrid import AgGrid, GridOptionsBuilder
from common.database import Database
from common.email_manager import EmailManager

with open('common/config.json') as f:
    config = json.load(f)
db = Database()
email_manager = EmailManager(config["EMAIL_SENDER"], config["EMAIL_PASSWORD"])

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

def view_abstracts():
    st.write("#### Submitted Abstracts")
    try:
        abstracts = db.get_abstracts()
        if abstracts:
            df = pd.DataFrame(abstracts)
            df['submitted_date'] = pd.to_datetime(df['submitted_date']).dt.strftime('%Y-%m-%d %H:%M:%S')
            df['last_updated'] = pd.to_datetime(df['last_updated']).dt.strftime('%Y-%m-%d %H:%M:%S')

            df.rename(columns={'submission_number': '#'}, inplace=True)
            display_columns = ['#', 'title', 'submitted_date']
            #df_display = df[display_columns]
            df_display = df.sort_values(by='submitted_date', ascending=False)[display_columns]

            if 'show_details' not in st.session_state:
                st.session_state['show_details'] = False

            for index, row in df_display.iterrows():
                cols = st.columns([5, 1])
                cols[0].write(row)
                if cols[1].button("View Details", key=f"button_{row['#']}"):
                    #st.session_state['detail_data'] = row.to_dict()
                    #st.session_state['show_details'] = True

                    # Retrieve all details from the DataFrame for the selected abstract
                    full_details = df.loc[df['#'] == row['#']].to_dict(orient='records')[0]
                    st.session_state['detail_data'] = full_details
                    st.session_state['show_details'] = True
                    break  # Break after button press to handle rerun

            if st.session_state['show_details']:
                st.write(f"Details for submission number {st.session_state['detail_data']['#']}:")
                st.json(st.session_state['detail_data'])  # Display in JSON format

                reviews = db.get_reviews(st.session_state['detail_data']['#'])
                if reviews:
                    st.write(f"#### Reviews for submission number {st.session_state['detail_data']['#']}:")
                    for idx, review in enumerate(reviews, start=1):
                        st.text(f"Reviewer {idx}: {review['reviewer_name']}, Score: {review['score']}, Recommendation: {review['recommendation']}")

                    avg_score = sum(review['score'] for review in reviews) / len(reviews)
                    accept_count = sum(1 for review in reviews if review['recommendation'] == "Accept")
                    if len(reviews) >= 3 and avg_score >= 5 and accept_count > len(reviews) / 2:
                        st.success("This paper can be approved for publication.")
                else:
                    st.error("No reviews yet.")

                if st.button("Back to list"):
                    st.session_state['show_details'] = False
                    st.session_state['detail_data'] = None
        else:
            st.error("No abstracts found in the database.")
    except Exception as e:
        st.error(f"Failed to fetch data from the database: {e}")

# def view_abstracts():
#     st.write("## Submitted Abstracts")
#     try:
#         abstracts = db.get_abstracts()
#         if abstracts:
#             df = pd.DataFrame(abstracts)
#             df['submitted_date'] = pd.to_datetime(df['submitted_date']).dt.strftime('%Y-%m-%d %H:%M:%S')
#             df['last_updated'] = pd.to_datetime(df['last_updated']).dt.strftime('%Y-%m-%d %H:%M:%S')

#             df.rename(columns={'submission_number': '#'}, inplace=True)
#             display_columns = ['#', 'title', 'author', 'submitted_date']

#             # Sort by 'submitted_date' in descending order
#             # df_display = df[display_columns]
#             df_display = df.sort_values(by='submitted_date', ascending=False)[display_columns]

#             if 'show_details' not in st.session_state:
#                 st.session_state['show_details'] = False

#             # Display the DataFrame only when not showing details
#             if not st.session_state['show_details']:

#                 # for index, row in df_display.iterrows():
#                 #     cols = st.columns([5, 1])
#                 #     with cols[0]:
#                 #         st.write(row)
#                 #     with cols[1]:
#                 #         if st.button("View Details", key=f"button_{row['#']}"):
#                 #             full_details = df.loc[df['#'] == row['#']].to_dict(orient='records')[0]
#                 #             st.session_state['detail_data'] = full_details
#                 #             st.session_state['show_details'] = True

#                 header_cols = st.columns([0.3, 8, 1])
#                 with header_cols[0]:
#                     st.markdown("**#**")  # Header for submission number
#                 with header_cols[1]:
#                     st.markdown("**Title**")  # Header for title
#                 with header_cols[2]:
#                     st.markdown("**View**")  # Header for the button

#                 for index, row in df_display.iterrows():
#                     cols = st.columns([0.3, 7, 1])  # Adjust the width ratios as needed
#                     with cols[0]:
#                         st.text(row['#'])
#                     with cols[1]:
#                         #st.text(row['title'])
#                         st.markdown(f"_{row['title']}_")
#                     with cols[2]:
#                         if st.button("Details", key=f"button_{row['#']}"):
#                             full_details = df.loc[df['#'] == row['#']].to_dict(orient='records')[0]
#                             st.session_state['detail_data'] = full_details
#                             st.session_state['show_details'] = True

#             # Handle display of detailed JSON view
#             if st.session_state['show_details']:
#                 st.write(f"##### Details for submission number {st.session_state['detail_data']['#']}:")
#                 st.json(st.session_state['detail_data'])  # Display in JSON format

#                 reviews = db.get_reviews(st.session_state['detail_data']['#'])
#                 if reviews:
#                     st.write(f"##### Reviews for submission number {st.session_state['detail_data']['#']}:")
#                     for idx, review in enumerate(reviews, start=1):
#                         st.text(f"Reviewer {idx}: {review['reviewer_name']}, Score: {review['score']}, Recommendation: {review['recommendation']}")

#                     avg_score = sum(review['score'] for review in reviews) / len(reviews)
#                     accept_count = sum(1 for review in reviews if review['recommendation'] == "Accept")
#                     if len(reviews) >= 3 and avg_score >= 5 and accept_count > len(reviews) / 2:
#                         st.success("This paper can be approved for publication.")
#                 else:
#                     st.write("No reviews yet.")

#                 if st.button("Back to list"):
#                     st.session_state['show_details'] = False
#                     st.session_state['detail_data'] = None
#         else:
#             st.error("No abstracts found in the database.")
#     except Exception as e:
#         st.error(f"Failed to fetch data from the database: {e}")

# def view_authors():
#     try:
#         st.write("## List of Authors")
#         authors = db.get_authors()
#         if authors:
#             df = pd.DataFrame(authors)
#             # Setup pagination
#             page_size = 10  # Set page size to 10 or any other suitable number
#             total_pages = len(df) // page_size + (1 if len(df) % page_size else 0)
#             page_number = st.sidebar.number_input('Page number', min_value=1, max_value=total_pages, value=1)
            
#             start_idx = (page_number - 1) * page_size
#             end_idx = start_idx + page_size
#             df_page = df.iloc[start_idx:end_idx]
            
#             st.write(df_page)
#         else:
#             st.error("No authors found in the database.")
#     except Exception as e:
#         st.error(f"An error occurred: {str(e)}")

def bot_dash():
    # try:
    #     # st.write("#### Bot Dashboard")
    #     st.write("##### Reviewers seleceted ...")
    #     results_data, submission_number = db.get_results()
    #     if results_data:
    #         # Convert the list of dictionaries to a DataFrame
    #         df = pd.DataFrame(results_data)
    #         # Rename columns as specified
    #         df.rename(columns={
    #             'Last_author': 'Reviewer',
    #             'Email': 'Email',
    #             'Cosine_similarity': 'Similarity Score (%)'
    #         }, inplace=True)
    #         st.write(f"The top three best matched reviewers for the abstract submission #{submission_number}:")
    #         # Display the DataFrame with styling
    #         st.dataframe(df.style.set_properties(**{
    #             'background-color': 'white', 
    #             'color': 'black', 
    #             'border-color': 'gray'
    #         }))
    #     else:
    #         st.write("No results found.")

    #     st.divider()
    #     st.write("###### Procced submissions ...")
    #     st.divider()
    #     #st.write("##### Papers rejected ...")
    #     # st.write("###### Email sent [??]...")
    #     # st.divider()
        
    # except Exception as e:
    #     st.error(f"An error occurred: {e}")

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

def main():
    db.initialize_submission_counter()

    st.header(':blue[DigiScientia]:green[*] Journal:', divider='rainbow')
    #st.markdown('# :blue_heart: DigiScientia <sup>:star:</sup> Journal', unsafe_allow_html=True)
    #st.markdown('# :blue[DigiScientia]:green[*] Journal', unsafe_allow_html=True)

    #st.markdown(':blue[DigiScientia] :star:_Revolutionizing academic publishing with a streamlined, fair, and transparent peer review process powered by AI, recognizing and rewarding contributions, and committed to open access._')
    #st.markdown('_Revolutionizing academic publishing with a streamlined, fair, and transparent peer review process powered by AI bot, recognizing and rewarding contributions, and committed to open access._')
    
    st.markdown('''
                _Revolutionizing academic publishing with a streamlined, fair, and transparent peer review process powered by AI, 
                recognizing and rewarding contributions, and committed to open access._
                ''')
    # st.markdown("---")
    #st.divider()

    tab1, tab2, tab3, tab4 = st.tabs(["Journal Intro", "Submit Abstract", "Submit Review", "Bot Dashboard"])
    # tab1, tab2, tab3, tab4, tab5 = st.tabs(["Journal Intro", "Submit Abstract", "Submit Review", "View Abstracts", "Bot Dashboard"])

    # tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["Intro", "Submit Abstract", "Submit Review", "View Abstracts", "View Authors", "Bot Dashboard"])

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

    # if tab1:
    #     st.write("Tab 1 Active")
    # elif tab2:
    #     st.write("Tab 2 Active")
    # elif tab3:
    #     st.write("Tab 3 Active")
    # elif tab4:
    #     st.write("Tab 4 Active")

if __name__ == "__main__":
    main()