# Standard Library Imports
import csv
import datetime
import json
import re
import time
import urllib
from time import sleep

# Third-Party Imports
import numpy as np
import pandas as pd
import schedule
import torch
import torch.nn.functional as F
import nltk
from transformers import AutoModel, AutoTokenizer

# Local Application/Library Specific Imports
from common.database import Database
from common.email_manager import EmailManager
   
class DigiScientiaBot:
    def __init__(self):
        # Load configuration from JSON file
        config_path = '../common/config.json'
        with open(config_path) as config_file:
            config = json.load(config_file)
        self.db = Database(uri=config["MONGO_DB_URI"])
        self.email_manager = EmailManager(sender_email=config["EMAIL_SENDER"], sender_password=config["EMAIL_PASSWORD"])

    def check_new_submissions(self):     
        new_submissions = self.db.get_new_submissions()

        if new_submissions:
            print("Found new submissions:")
            for submission in new_submissions:
                self.submission = submission
                # Extract title and submission number for initial print (monitoring purposes)
                title = self.submission.get('title', 'No title provided')
                submission_number = self.submission.get('submission_number', 'No submission number')
                print(f"  - Title: {title}, Submission Number: {submission_number}")
                self.process_submission()
        else:
            print("No new submissions found.")
        
    def process_submission(self):
        submission = self.submission
        # Extract details from the submission
        self.title = submission.get('title', 'No title provided')
        self.abstract = submission.get('abstract', 'No abstract provided')
        self.keywords = submission.get('keywords', 'No keywords provided')
        self.author = submission.get('author', 'No author listed')
        self.author_email = submission.get('author_email', 'No email provided')
        self.author_orcid = submission.get('author_orcid', 'No ORCID provided')
        self.coauthors = submission.get('coauthors', 'No coauthors listed')
        self.link = submission.get('link', 'No link provided')

        # print the extracted details
        print(f"Processing Submission {submission.get('submission_number', 'N/A')}:")
        print(f"  Title: {self.title}")
        print(f"  Abstract: {self.abstract}")
        print(f"  Keywords: {self.keywords}")
        print(f"  Author: {self.author}")
        print(f"  Author Email: {self.author_email}")
        print(f"  Author ORCID: {self.author_orcid}")
        print(f"  Coauthors: {self.coauthors}")
        print(f"  Link: {self.link}")

        self.df_full = self.search_api()
        # print(' line  81, df')
        # print(self.df_full)
        self.ordered_df = self.find_reviewers()
        self.email_df = self.search_api_conflict()
        # print('\n')
        # print(self.email_df)
        
        # print('\n')
        # print('FINAL RESULT??')

        self.result_list = self.filter_seniors()
        print(self.result_list) 
        #create a mongo DB collection for the final list of peer reviewers to be shown in the STREAMLIT APP

        # Convert result_list DataFrame to a dictionary for MongoDB insertion
        result_list_dict = {
            "submission_number": submission.get("submission_number"),
            "results": self.result_list.to_dict('records')  # Ensure results are in a suitable format
        }

        # Insert the result list into MongoDB
        result_id = self.db.insert_result_list(result_list_dict)
        print(f"Result list inserted with ID: {result_id}")

         # Send requests for reviews, sending emails to reviewers or ...
        self.request_reviews(self.result_list)

        # Additional steps to process reviews and announce decisions
        self.process_reviews()
    
    def search_api(self):
        # This is where we input our keyword
        query = urllib.parse.quote(self.keywords)

        print('Searching API keywords:')
        print(self.keywords)
        print(query)

        # common settings between esearch and efetch
        base_url = 'http://eutils.ncbi.nlm.nih.gov/entrez/eutils/'
        db = 'db=pubmed'

        # esearch settings
        search_eutil = 'esearch.fcgi?'
        search_term = '&term=' + query
        search_usehistory = '&usehistory=y'
        search_rettype = '&rettype=json'
        sort = "&sort=relevance"
        datetype = "&datetype=pdat"
        reldate = "&reldate=" + str(3652)

        # call the esearch command for the query and read the web result
        search_url = base_url+search_eutil+db+search_term+search_usehistory+search_rettype+sort+datetype+reldate
        print(f"Making API call to: {search_url}")  # Debug: log the URL being called
        print(search_url) 

        f = urllib.request.urlopen(search_url)
        
        search_data = f.read().decode('utf-8')

        # efetch settings
        fetch_eutil = 'efetch.fcgi?'
        retmax = 20
        retstart = 0
        fetch_retmode = "&retmode=text"
        fetch_rettype = "&rettype=abstract"


        # obtain webenv and querykey settings from the esearch results
        fetch_webenv = "&WebEnv=" + re.findall (r"<WebEnv>(\S+)<\/WebEnv>", search_data)[0]
        fetch_querykey = "&query_key=" + re.findall(r"<QueryKey>(\d+?)</QueryKey>",search_data)[0]

        # call efetch commands using a loop until all abstracts are obtained
        run = True
        all_abstracts = list()
        loop_counter = 1

        while run:
            loop_counter += 1
            fetch_retstart = "&retstart=" + str(retstart)
            fetch_retmax = "&retmax=" + str(retmax)
            # create the efetch url
            fetch_url = base_url+fetch_eutil+db+fetch_querykey+fetch_webenv+fetch_retstart+fetch_retmax+fetch_retmode+fetch_rettype
            # open the efetch url

            print(f"Fetch call to: {fetch_url}")  # Debug: log the URL being called
            print(fetch_url) 

            f = urllib.request.urlopen (fetch_url)
            fetch_data = f.read().decode('utf-8')
            # split the data into individual abstracts
            abstracts = fetch_data.split("\n\n\n")
            
            # print('\n')
            # print(fetch_url)
            # print(abstracts)

            # append to the list all_abstracts
            all_abstracts = all_abstracts+abstracts
            # wait 2 seconds so we don't get blocked
            sleep(2)
            # update retstart to download the next chunk of abstracts
            retstart = retstart + retmax
            if retstart > 80 or retstart > len(all_abstracts):
                run = False
        
        full_abstracts = []
        # Define the columns for the DataFrame
        columns = ['Journal', 'Title', 'Authors', 'Author_Information', 'Abstract', 'DOI', 'Misc', 'Rest']

        # Loop through each abstract in all_abstracts
        for abstract in all_abstracts:
            # Split abstract into categories
            split_abstract = abstract.split("\n\n")
            if 6 <= len(split_abstract) <= 8:
                # Append the split_abstract to full_abstracts if it has the right number of sections
                full_abstracts.append(split_abstract)

        # Create a DataFrame for full abstracts
        self.df_full = pd.DataFrame(full_abstracts, columns=columns)

        print('SEACH API')
        print(self.df_full)

        return self.df_full

    def find_reviewers(self):
        # Select only interesting columns
        clean_df = self.df_full[['Title', 'Authors', 'Abstract', 'Author_Information']].copy()  # Add .copy() to avoid SettingWithCopyWarning

        # Split last author from the other authors. If there are no other authors --> NaN
        def split_authors(authors):
            split_authors = authors.rsplit(',', maxsplit=1)
            if len(split_authors) == 1:  # Only one author
                return (np.nan, split_authors[0].strip())
            else:
                return (split_authors[0].strip(), split_authors[1].strip())

        # print(' INSIDE FIND REVIEWES DF_CLEAN')
        # print(clean_df)

        clean_df.loc[:, ['Other_authors', 'Last_author']] = clean_df['Authors'].apply(split_authors).tolist()
        clean_df.loc[:, 'Other_authors'] = clean_df['Other_authors'].apply(lambda x: x if pd.notna(x) else np.nan)

        # Sort columns
        cleaned_df = clean_df[['Title', 'Abstract', 'Other_authors', 'Last_author', 'Author_Information']]

        # Define a function to extract the number including brackets from the Last_author column
        def extract_number(row):
            last_author = row['Last_author']
            match = re.search(r'\(\d+\)', last_author)
            if match:
                return match.group()
            else:
                return None

        # Apply the function to each row
        cleaned_df['Number_in_brackets'] = cleaned_df.apply(extract_number, axis=1)

        # Define a function to extract the desired information
        def extract_info(row):
            number_in_brackets = row['Number_in_brackets']
            author_info = row['Author_Information']
                
            if number_in_brackets is None:
                return ""

            # Find the position of the number in brackets in the author information
            index = author_info.find(number_in_brackets)
            if index != -1:
                # Extract everything after the number in brackets
                text_after_number = author_info[index + len(number_in_brackets):].strip()
                # Find the end position of the text to include
                end_position = re.search(r'(\(\d+\)|$)', text_after_number)
                if end_position:
                    return number_in_brackets + ' ' + text_after_number[:end_position.start()].strip()
            return ""

        # Apply the function to each row
        cleaned_df['Info_last_author'] = cleaned_df.apply(extract_info, axis=1)

        def extract_emails(text):
            emails = re.findall(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', text)
            if emails:
                return ', '.join(emails)
            else:
                return np.nan

        # Remove brackets, numbers, dots and \n from author columns
        def clean_names(text):
            names = re.sub(r'[\d()+.#\n]+', '', text)
            return names

        # Apply the 'extract_emails' function and assign the result to the 'Email' column
        cleaned_df.loc[:, 'Email'] = cleaned_df['Info_last_author'].apply(extract_emails)

        # Apply the 'clean_names' function to 'Last_author' and assign back to the same column
        cleaned_df.loc[:, 'Last_author'] = cleaned_df['Last_author'].apply(clean_names)

        # Change the type of 'Other_authors' to string safely
        cleaned_df.loc[:, 'Other_authors'] = cleaned_df.Other_authors.astype("str")

        # Apply the 'clean_names' function to 'Other_authors' after type conversion
        cleaned_df.loc[:, 'Other_authors'] = cleaned_df['Other_authors'].apply(clean_names)

        # Restructure DataFrame to include only specific columns
        cleaned_df = cleaned_df[["Title", "Abstract", "Other_authors", "Last_author", "Email"]]
        corpus = cleaned_df['Abstract'].tolist()

        def meanpooling(output, mask):
            embeddings = output[0] # First element of model_output contains all token embeddings
            mask = mask.unsqueeze(-1).expand(embeddings.size()).float()
            return torch.sum(embeddings * mask, 1) / torch.clamp(mask.sum(1), min=1e-9)

        # Sentences we want sentence embeddings for
        sentences = corpus

        # Load model from HuggingFace Hub
        tokenizer = AutoTokenizer.from_pretrained("neuml/pubmedbert-base-embeddings")
        model = AutoModel.from_pretrained("neuml/pubmedbert-base-embeddings")

        # Tokenize sentences
        inputs = tokenizer(sentences, padding=True, truncation=True, return_tensors='pt', max_length = 512)

        # Compute token embeddings
        with torch.no_grad():
            output = model(**inputs)

        # Perform pooling. In this case, mean pooling.
        embeddings = meanpooling(output, inputs['attention_mask'])

        new_sentence = self.abstract

        # Tokenize and encode the new sentence
        new_inputs = tokenizer(new_sentence, padding=True, truncation=True, return_tensors='pt', max_length = 512)

        # Compute token embeddings for the new sentence
        with torch.no_grad():
            new_output = model(**new_inputs)

        # Perform mean pooling for the new sentence
        new_embedding = meanpooling(new_output, new_inputs['attention_mask'])

        # Compute cosine similarity between the new sentence embedding and all other sentence embeddings
        similarities = F.cosine_similarity(embeddings, new_embedding, dim=1)

        # Combine cosine similarities with sentence indices
        similarity_scores = [(i, sim.item()) for i, sim in enumerate(similarities)]

        # Sort cosine similarities in descending order
        sorted_similarities = sorted(similarity_scores, key=lambda x: x[1], reverse=True)

        # Print sorted cosine similarities
        indices_to_print = [index for index, _ in sorted_similarities]

        # Create a new DataFrame containing selected rows
        selection_df = cleaned_df.iloc[indices_to_print]

        ##### Add cosine similarity to selection_df

        # Create a new column in the DataFrame to store cosine similarities
        selection_df['Cosine_similarity'] = None

        # Iterate over the list of tuples and assign cosine similarities to corresponding rows in DataFrame
        for index, similarity in sorted_similarities:
            selection_df.at[index, 'Cosine_similarity'] = similarity

        # Convert to percentage
        # selection_df["Cosine_similarity"] = (selection_df["Cosine_similarity"] * 100).map('{:.2f}%'.format)
        selection_df.loc[:, 'Cosine_similarity'] = (selection_df["Cosine_similarity"] * 100).map('{:.2f}%'.format)

        ##### Create dataframe with the inputs for the email, sorted with descending cosine similarity

        # Create deadline of two weeks
        now = datetime.datetime.now()
        two_weeks = datetime.timedelta(weeks=2)
        dl = now + two_weeks
        deadline = dl.strftime("%d.%m.%Y")

        # Add authors and emails
        self.ordered_df = selection_df[['Other_authors','Last_author','Email','Cosine_similarity']].reset_index(drop=True)

        # Add title and abstract of the to-be-reviewed manuscript
        self.ordered_df['To_review_title'] = self.title
        self.ordered_df['To_review_abstract'] = self.abstract
        self.ordered_df['Deadline'] = deadline

        # Drop rows where emails = NaN
        self.ordered_df = self.ordered_df[self.ordered_df['Email'].notna()].reset_index(drop=True)

        return self.ordered_df

    def search_api_conflict(self):
        columns = ['Journal', 'Title', 'Authors', 'Author_Information', 'Abstract', 'DOI', 'Misc', 'Rest']

        query = urllib.parse.quote(self.author)

        # common settings between esearch and efetch
        base_url = 'http://eutils.ncbi.nlm.nih.gov/entrez/eutils/'
        db = 'db=pubmed'

        # esearch settings
        search_eutil = 'esearch.fcgi?'
        search_term = '&term=' + query
        search_usehistory = '&usehistory=y'
        search_rettype = '&rettype=json'
        sort = "&sort=pub_date"
        datetype = "&datetype=pdat"
        reldate = "&reldate=" + str(1826)

        # call the esearch command for the query and read the web result
        search_url = base_url+search_eutil+db+search_term+search_usehistory+search_rettype+sort+datetype+reldate
        f = urllib.request.urlopen (search_url)
        search_data = f.read().decode('utf-8')

        # efetch settings
        fetch_eutil = 'efetch.fcgi?'
        retmax = 20
        retstart = 0
        fetch_retmode = "&retmode=text"
        fetch_rettype = "&rettype=abstract"

        # obtain webenv and querykey settings from the esearch results
        fetch_webenv = "&WebEnv=" + re.findall (r"<WebEnv>(\S+)<\/WebEnv>", search_data)[0]
        fetch_querykey = "&query_key=" + re.findall(r"<QueryKey>(\d+?)</QueryKey>",search_data)[0]

        # call efetch commands using a loop until all abstracts are obtained
        run = True
        all_abstracts_ci = list()
        loop_counter = 1

        while run:
            loop_counter += 1
            fetch_retstart = "&retstart=" + str(retstart)
            fetch_retmax = "&retmax=" + str(retmax)
            # create the efetch url
            fetch_url = base_url+fetch_eutil+db+fetch_querykey+fetch_webenv+fetch_retstart+fetch_retmax+fetch_retmode+fetch_rettype
            # open the efetch url
            f = urllib.request.urlopen (fetch_url)
            fetch_data = f.read().decode('utf-8')
            # split the data into individual abstracts
            abstracts = fetch_data.split("\n\n\n")
            # append to the list all_abstracts
            all_abstracts_ci = all_abstracts_ci+abstracts
            # wait 2 seconds so we don't get blocked
            sleep(2)
            # update retstart to download the next chunk of abstracts
            retstart = retstart + retmax
            if retstart > len(all_abstracts_ci):
                run = False

        full_abstracts_ci = []

        # For each abstract, split into categories and append it to the data list
        for abstract_ci in all_abstracts_ci:
            # To obtain categories, split every double newline.
            split_abstract_ci = abstract_ci.split("\n\n")
            if 6 <= len(split_abstract_ci) <= 8:
                full_abstracts_ci.append(split_abstract_ci)

        # Create a DataFrame from the data list
        data_ci_df = pd.DataFrame(full_abstracts_ci, columns=columns)

        # Remove brackets, numbers, dots, # and \n from author column
        def clean_names(text):
            names = re.sub(r'[\d()+.#\n]+', '', text)
            return names

        data_ci_df['Authors'] = data_ci_df['Authors'].apply(clean_names)

        # Select only authors
        clean_ci_df = data_ci_df[['Authors']]

        # Split each string in the 'Authors' column by comma and flatten the resulting list
        authors_list = [author.strip() for authors in clean_ci_df['Authors'] for author in authors.split(',')]

        # Convert the list to a set to remove duplicates
        authors_set = set(authors_list)

        # Remove the input author from the set
        authors_set.discard(self.author)

        # Create a new dataframe from the modified set
        conflict_df = pd.DataFrame({'Authors': list(authors_set)})

        # Function to check if any name in 'Authors' column of conflict_df is in 'Other_authors' or 'Last_author' columns of ordered_df
        def check_conflict(row):
            for author in conflict_df['Authors']:
                if author in row['Other_authors'] or author == row['Last_author']:
                    return False
            return True

        # Apply the function to each row in ordered_df and keep only rows where there is no conflict
        self.email_df = self.ordered_df[self.ordered_df.apply(check_conflict, axis=1)]

        ##### Remove other authors and select top then authors
        # Remove other authors
        self.email_df = self.email_df[["Last_author","Email","Cosine_similarity","To_review_title","To_review_abstract","Deadline"]]

        # Select top five authors
        self.email_df = self.email_df[:10].reset_index(drop=True)

        return self.email_df 

    def filter_seniors(self): # here we need to connect seniors_list file or DB

        seniors_list = pd.read_csv('../data/processed/seniors_list.csv')
        seniors_set = set(seniors_list['Name'])
        # Initialize an empty DataFrame with the same columns as self.email_df for result_list
        result_list = pd.DataFrame(columns=self.email_df.columns)

        # Iterate over rows in self.email_df to filter senior authors first
        for index, row in self.email_df.iterrows():
            if row['Last_author'] in seniors_set:
                # Use concat to add the row to result_list
                result_list = pd.concat([result_list, pd.DataFrame([row])], ignore_index=True)
                break  # Break after adding the first senior author

        # Add the remaining authors to the result list if less than 3 reviewers total
        for index, row in self.email_df.iterrows():
            if row['Last_author'] not in seniors_set and len(result_list) < 3:
                # Use concat to add the row to result_list
                result_list = pd.concat([result_list, pd.DataFrame([row])], ignore_index=True)

        return result_list

    def request_reviews(self, reviewers):
        # Ensure that reviewers is a DataFrame
        if not isinstance(reviewers, pd.DataFrame):
            raise ValueError("Reviewers data must be a DataFrame")
        
        # Template setup
        subject_template = "Invitation to Review a Paper: Dear {author}"
        body_template = """
        Dear {author},

        We are reaching out to invite you to review a paper that falls within your area of expertise. We believe your insights would be invaluable to ensure the quality and relevance of the research.

        Please let us know if you would be willing to contribute to the peer review process for this paper.

        Best regards,
        DigiScientia
        AI bot, Journal Editor
        """

        # Send emails to the constructed email address
        for index, row in reviewers.iterrows():
            author_name = row['Last_author'].split(',')[0]
            subject = subject_template.format(author=author_name)
            body = body_template.format(author=author_name)
            self.email_manager.send_email(subject, body, "constructordigi@gmail.com")

    def process_reviews(self):
        # Fetch all submissions
        submissions = self.db.get_all_submissions()
        if not submissions:
            print("No submissions to process or failed to fetch submissions.")
            return

        for submission in submissions:
            reviews = self.db.get_reviews(submission['submission_number'])
            if reviews and len(reviews) >= 3:
                avg_score = sum(review['score'] for review in reviews) / len(reviews)
                accept_count = sum(1 for review in reviews if review['recommendation'] == "Accept")

                # Check conditions for acceptance
                if avg_score >= 5 and accept_count > len(reviews) / 2:
                    subject = "Your submission has been accepted"
                    body = f"Dear {submission['author']},\n\nYour paper titled '{submission['title']}' has been accepted for publication.\n\nBest regards,\nDigiScientia Editorial Team"
                    self.email_manager.send_email(subject, body, submission['author_email'])
                    print(f"Accepted: {submission['title']}")
                else:
                    subject = "Your submission has been rejected"
                    body = f"Dear {submission['author']},\n\nWe regret to inform you that your paper titled '{submission['title']}' has not been accepted for publication.\n\nBest regards,\nDigiScientia Editorial Team"
                    self.email_manager.send_email(subject, body, submission['author_email'])
                    print(f"Rejected: {submission['title']}")

                # Optionally display review details
                print(f"#### Reviews for submission number {submission['submission_number']}:")
                for idx, review in enumerate(reviews, start=1):
                    print(f"Reviewer {idx}: {review['reviewer_name']}, Score: {review['score']}, Recommendation: {review['recommendation']}")

                print(f"Average Score: {avg_score}, Acceptance Count: {accept_count}")
            else:
                print(f"No sufficient reviews yet for submission number {submission['submission_number']}.")

def run_bot():

    bot = DigiScientiaBot()
    print(f"Starting ...")
    schedule.every(1).minutes.do(bot.check_new_submissions)
    print(f"Bot awake ...")

    # Run the schedule in a loop
    while True:
        schedule.run_pending()
        time.sleep(1)

if __name__ == "__main__":
    run_bot()


