# DigiScientia

Prototype of an AI-assisted peer-review workflow, built as the capstone project of the
Constructor Academy Data Science Bootcamp (Munich, February to May 2024).

## What it does
- `src/portal/app.py`: Streamlit portal where authors submit abstracts and reviewers submit
  reviews (stored in MongoDB); shows the reviewers selected by the bot and the accepted papers.
- `src/bot/bot.py`: reviewer-matching bot. For each new submission it queries PubMed through
  the NCBI E-utilities, embeds the retrieved abstracts and the submitted abstract with
  PubMedBERT (Hugging Face Transformers, mean pooling), ranks last authors by cosine
  similarity, removes co-authors of the submitting author (conflict of interest), prefers
  reviewers from a curated senior list, stores the result and sends invitations by e-mail.
  Once three reviews are in, it aggregates scores and sends the decision.
- `src/common/`: MongoDB access layer and SMTP e-mail manager.

## Stack
Python 3.12, pandas, PyTorch, Hugging Face Transformers (neuml/pubmedbert-base-embeddings),
pymongo (MongoDB Atlas), Streamlit, schedule, NCBI E-utilities.

## Setup
Create `src/common/config.json` with `MONGO_DB_URI`, `EMAIL_SENDER` and `EMAIL_PASSWORD`
(not committed). `environment.yml` covers the notebook environment; the apps also need
`pip install streamlit streamlit-aggrid torch transformers pymongo schedule`.
Run `streamlit run src/portal/app.py` and `python src/bot/bot.py`.

## Status
Bootcamp prototype (May 2024), migrated from the bootcamp GitLab; not maintained.