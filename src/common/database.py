# database.py
import json
from pymongo import MongoClient
from datetime import datetime

class Database:
    # MongoDB Atlas connection string
    def __init__(self):
        config_path = 'common/config.json'
        with open(config_path, 'r') as f:
            config = json.load(f)
        uri = config['MONGO_DB_URI']
        self.client = MongoClient(uri)
        self.db = self.client["digiscientia_database"]
        self.abstracts = self.db["abstracts"]
        self.reviews = self.db["reviews"]
        self.submission_counter = self.db["submission_counter"]
        self.authors = self.db["authors"]
        self.seniors_list = self.db["seniors_list"]
        self.last_checked = self.db["last_checked"]
        self.results = self.db["results"]

        # Initialize last_checked collection
        if self.last_checked.count_documents({}) == 0:
            self.last_checked.insert_one({"_id": "last_checked_time", "datetime": self.current_datetime()})
    
    def increment_abstract_count(self):
        # Check if the submission_counter collection has the abstract counter document
        if self.submission_counter.count_documents({'_id': 'abstract_counter'}) == 0:
            self.submission_counter.insert_one({'_id': 'abstract_counter', 'count': 0})

        # Increment and return the new count
        result = self.submission_counter.find_one_and_update(
            {'_id': 'abstract_counter'},
            {'$inc': {'count': 1}},
            return_document=True
        )
        return result['count']
    
    def current_datetime(self):
        return datetime.now()

    def abstract_exists(self, submission_number):
        """ Check if an abstract with the given submission number exists in the database. """
        count = self.abstracts.count_documents({"submission_number": submission_number})
        return count > 0
    
    def initialize_submission_counter(self):
        if self.submission_counter.count_documents({}) == 0:
            self.submission_counter.insert_one({"_id": "abstract_counter", "count": 0})

    def insert_abstract(self, data):
        return self.abstracts.insert_one(data).inserted_id

    def insert_review(self, data):
        return self.reviews.insert_one(data).inserted_id
    
    def insert_result_list(self, result_data):
        try:
            # Insert the data into the 'results' collection
            insert_result = self.db.results.insert_one(result_data)
            return insert_result.inserted_id  # Returns the ID of the inserted document
        except Exception as e:
            print(f"Error inserting result list into MongoDB: {e}")
            return None

    def get_abstracts(self):
        return list(self.abstracts.find({}, {'_id': 0}))

    def get_reviews(self, submission_number):
        return list(self.reviews.find({"submission_number": submission_number}))

    # def get_authors(self):
    #     return list(self.authors.find({}, {'_id': 0}))
    
    # def get_new_submissions(self):
    #     # Retrieve the last check time
    #     last_check = self.last_checked.find_one({"_id": "last_checked_time"})
    #     last_check_time = last_check["datetime"]

    #     # Query for new submissions since the last check
    #     new_submissions = list(self.abstracts.find({"submitted_at": {"$gt": last_check_time}}, {'_id': 0}))

    #     # Update the last checked time to current
    #     self.last_checked.update_one({"_id": "last_checked_time"}, {"$set": {"datetime": self.current_datetime()}})

    #     return new_submissions
    
    def get_new_submissions(self):
        # Retrieve the last check time
        last_check = self.last_checked.find_one({"_id": "last_checked_time"})
        last_check_time = last_check["datetime"]

        # Query for new submissions since the last check
        new_submissions = list(self.abstracts.find(
            {"submitted_date": {"$gt": last_check_time}},
            {'_id': 0, 'submission_number': 1, 'title': 1, 'abstract': 1, 'keywords': 1, 
             'author': 1, 'author_email': 1, 'author_orcid': 1, 'coauthors': 1, 'link': 1, 'submitted_date': 1}
        ))

        # Update the last checked time to current
        self.last_checked.update_one({"_id": "last_checked_time"}, {"$set": {"datetime": self.current_datetime()}})

        return new_submissions
    
    # def get_all_submissions(self):
    #     all_submissions = list(self.abstracts.find({}, {'_id': 0}))

    #     return all_submissions

    def get_all_submissions(self):
        try:
            # Specify only necessary fields to retrieve to optimize the query
            fields = {
                '_id': 0, 'submission_number': 1, 'title': 1, 'abstract': 1, 'keywords': 1, 
                'author': 1, 'author_email': 1, 'author_orcid': 1, 'coauthors': 1, 'link': 1,
                'submitted_date': 1  # Assuming 'submitted_date' might be used somewhere in processing
            }
            all_submissions = list(self.abstracts.find({}, fields))
            return all_submissions
        except Exception as e:
            print(f"An error occurred while fetching all submissions: {e}")
            return []

    # def get_results(self):
    #     try:
    #         cursor = self.results.find().sort('_id', -1).limit(1)
    #         latest_result = list(cursor)
    #         if latest_result:
    #             # Assume the results are stored under a 'results' key and return this part
    #             return latest_result[0]['results']
    #         else:
    #             return None
    #     except Exception as e:
    #         print(f"Failed to fetch the latest result: {e}")
    #         return None

    def get_results(self):
        try:
            # Fetch the most recent result
            cursor = self.results.find().sort('_id', -1).limit(1)
            latest_result = list(cursor)
            if latest_result:
                # Return both the results list and the submission number
                return latest_result[0]['results'], latest_result[0]['submission_number']
            else:
                return None, None
        except Exception as e:
            print(f"Failed to fetch the latest result: {e}")
            return None, None
        
    def get_accepted_papers(self):
        submissions = self.get_all_submissions()
        accepted_papers = []
        for submission in submissions:
            reviews = self.get_reviews(submission['submission_number'])
            if reviews and len(reviews) >= 3:
                avg_score = sum(review['score'] for review in reviews) / len(reviews)
                accept_count = sum(1 for review in reviews if review['recommendation'] == "Accept")
                if avg_score >= 5 and accept_count > len(reviews) / 2:
                    accepted_papers.append({
                        'Author': submission['author'],
                        'Title': submission['title'],
                        'Average Score': avg_score,
                        'Acceptance Count': accept_count
                    })
        return accepted_papers
        
    # def get_latest_result():
    #     latest_result = db.results.find().sort('_id', -1).limit(1)  # Fetch the most recent result
    #     return latest_result