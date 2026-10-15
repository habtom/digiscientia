# digiscientiabot.py
import time
import schedule
from database import Database
import logging
from logging_config import setup_logger

logger = setup_logger()


class DigiScientiaBot:
    def __init__(self):
        self.db = Database()
        self.running = False  # Flag to control the loop, starts as False
        logger.info("DigiScientiaBot initialized and database connection established.")

    def check_new_submissions(self):
        logger.info("Starting to check for new submissions...")
        try:
            new_submissions = self.db.get_new_submissions()
            if new_submissions:
                logger.info(f"Found {len(new_submissions)} new submissions.")
                for submission in new_submissions:
                    self.process_submission(submission)
            else:
                logger.info("No new submissions found.")
        except Exception as e:
            logger.error("Failed to fetch new submissions", exc_info=True)
        
    def process_submission(self, submission):
        try:
            logger.info(f"Processing Submission {submission.get('submission_number', 'N/A')}:")
            # Process details
            self.log_submission_details(submission)
            # Further processing
            self.find_reviewers(submission)
            self.request_reviews(submission)
        except Exception as e:
            logger.error(f"Error processing submission {submission.get('submission_number')}", exc_info=True)

    def log_submission_details(self, submission):
        # Log all details of the submission
        details = {
            'Title': submission.get('title', 'No title provided'),
            'Abstract': submission.get('abstract', 'No abstract provided'),
            'Keywords': submission.get('keywords', 'No keywords provided'),
            'Author': submission.get('author', 'No author listed'),
            'Email': submission.get('author_email', 'No email provided'),
            'ORCID': submission.get('author_orcid', 'No ORCID provided'),
            'Coauthors': submission.get('coauthors', 'No coauthors listed'),
            'Link': submission.get('link', 'No link provided')
        }
        for key, value in details.items():
            logger.info(f"  {key}: {value}")

    def find_reviewers(self, submission):
        # Placeholder for reviewer finding logic
        pass

    def request_reviews(self, submission):
        # Placeholder for review request logic
        pass

    def run_bot(self):
        self.running = True
        logger.info("Bot starting...")
        schedule.every(1).minutes.do(self.check_new_submissions)
        logger.info("Bot is now active.")
        
        try:
            while self.running:
                schedule.run_pending()
                time.sleep(1)
        finally:
            logger.info("Bot shutting down...")

    def terminate(self):
        self.running = False  # Set this flag to False to stop the loop in `run_bot`

if __name__ == "__main__":
    bot = DigiScientiaBot()
    bot.run_bot()
