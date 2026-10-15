DigiScientia Project
==============================
Day 2:
======
- Finetuning NCBI
- Created email template

Day 1:
====== 
- Attempt to download data
- Create NCBI

Day 0, 08th April:
==================
- Updated project template 
- Cloned gitlab repo
- Problem Understanding
- Preparing questions for meeting with Leal
- Meeting with Leal
- Attempt to download data

.... 

















Day 0, 29th of January  
====

## Create GitLab folder structure

## Data Exploration, 


### 1. Clone project repo to your desired destination

### 2. Navigate to a project repo and create a .gitignore file (see instructions below), push your changes to remote    


### 3. Make an environment with conda
 
`conda create --name myenv`

Change the environment\:

`conda env list`\
`conda activate myenv`\
`conda list`

### 4. Save an environment as .yml to be able to transfer it to the other person

Export your active environment to a new file (in the end of the project or once you need to share it with other person):

`conda env export > environment.yml`

Create the environment from the environment.yml file:

`conda env create -f environment.yml`

Remove environment if needed:

`conda remove --name myenv --all`


### 5. Folder structure

`pip install cookiecutter`\
`cookiecutter https://github.com/drivendata/cookiecutter-data-science`

Clean the folder structure (remove unnecessary files).   
Or create your own custom one. 

### 6. Git

#### 6.1 Gitignore 

Create `.gitignore` file for the following keywords: `python`, `jupyter`, `data` and whatever is required.    
`https://www.toptal.com/developers/gitignore`  

Add *.csv, *.json, etc. 

#### 6.2 push to the gitlab before you add any data to your folder.

`Git add .`\
`Git commit -m ”added folder structure”`\
`Git push `

#### 6.3 push info about data

Create separate txt file with the description where to get this data. Put the file into the `Data` folder.  
If the data are very light  ~5 mb or so, you can push it, Otherwise just description. 

#### 6.4 branching 

`Git branch vis`\
`Git checkout vis `

Work on `vis`, if you like the result => then merge \
Merging is happening on the target branch (master)\
Delete the branch after completing the task.

`git branch -d <branch-name>` \
`git push --delete <remote name> <branch name>` 

`<remote name>` == origin


**Do not work on the same file at the same time.**

If you work on the same branch - always pull first. 

Actually, always start with a PULL. \
This reduce a chance to get a conflict. Work ideally on different files. If working on the same file - always PULL first. 

#### 7. Example Student Projects  


- Brain MRI: https://github.com/SIT-Academy/brain-mri-classification/blob/master/README.md

- Super Resolution Satellite: 
https://github.com/SIT-Academy/satellite-image-super-resolution/tree/master/notebooks (SIT version)  
https://github.com/egronskaya/Super-Resolution-for-Satellite-Imagery (Students' version)

Both projects were done in Colab. 




