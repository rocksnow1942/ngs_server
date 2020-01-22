# Steps TO SET UP Development Environment

### Before started
This for starting the development environment. No deployment tools such as nginx or gunicorn are installed.

Some of the packages are required for a more specific task. For example, elasticsearch require installation of 
elastic search package and its dependencies. The main application is still functional without it. But the 
related searching function will be missing.  

### Step 1. Get the ngs_server repository from git.
In the folder you want to save the application, pull repository from git using git, 
or download and unzip to that folder. Then change directory to that folder.

    $ cd /path/to/your/folder
    $ git clone https://github.com/rocksnow1942/ngs_server.git
    $ cd ngs_server 
    $ ls 

You should be able to see this:

    Aptitude_NGS.py		certs			server_mapping
    README.md		config.py		testNGSdbdata.py
    Ubuntu Deploy Configs	fastq_tools.py
    app			requirements.txt

### Step 2. Install virtual environment for running the applicaiton and install application dependencies. 
Create a folder venv and put python files in there and activate the virtual environment. 

    $ python -m venv venv 
    $ source venv/bin/activate 
   

After this you should see `(venv)` in front of your terminal prompt. 

Also, if you enter `which python` in terminal, you should see 
`/path/to/your/folder/ngs_server/venv/bin/python`. This means venv is activated. 

Then install all dependencies. All dependencies are installed to the venv 

    $ pip install -r requirements.txt

No errors should occur. If error "xcrun: error: invalid active developer path", run 
    
    $ xcode-select --install 

to install the xcode tools. Then run the above command again. 

### Step 3. Install mysql server and create Database for application use. 
The mysql server tested with is `5.7.27`. Any `5.7` mysql server version should work fine. 

Download and install from [MySQL Community Downloads](https://dev.mysql.com/downloads/mysql/).

After install, log in mysql with root and create user name and password. 
By default, after install root password is set to empty. 

Then create a database called 'ngs' and new user 'ngs_server_user' to use this database.

    $ sudo mysql -u root 
    > create database ngs character set utf8mb4 collate utf8mb4_unicode_ci;
    > create user 'ngs_server_user'@'localhost' identified by 'ngs_server_password';
    > grant all privileges on ngs.* to 'ngs_server_user'@'localhost';
    > flush privileges;
    > quit;

### Step 4. Create environment variables files. 

Create `.env` file under `ngs_server` folder. Put in the following content with proper changes. 

    SECRET_KEY=a_secret_key
    DATABASE_URL=mysql+pymysql://ngs_server_user:ngs_server_password@localhost:3306/ngs?charset=utf8mb4
    MAIL_SERVER=smtp.googlemail.com
    MAIL_PORT=587
    MAIL_USE_TLS=1
    MAIL_USERNAME=<your gmail address if you want to use email function>
    MAIL_PASSWORD=<your gmail password>
    UPLOAD_FOLDER=/path/to/your/folder/ngs_server/app/cache/file_upload
    ANALYSIS_FOLDER=/path/to/your/folder/ngs_server/app/cache/analysis_data
    ALLOWED_EXTENSIONS={'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif','csv','sql'}
    PAGE_LIMIT=10
    ELASTICSEARCH_URL=""
    FOLDOJO_FOLDER=/path/to/your/folder/ngs_server/app/APPS/foldojo/static/cache
    BOKEH_SECRET_KEY=<you need to generate bokeh key>
    BOKEH_SIGN_SESSIONS=1
    PPT_SOURCE_FOLDER=<PPT slides folder, this is for server indexing>
    PPT_TARGET_FOLDER=<PPT slides snapshot folder, this is for server reading snapshots>
    PPT_LOG_FILE=/path/to/your/folder/ngs_server/app/tasks/ppt_log.txt 
    APP_ERROR_LOG=/path/to/your/folder/ngs_server/logs/APP_ERROR_LOG.txt
    DATABASE_FOLDER=<path to mysql storage>
    ANIMAL_DATA_PATH=<path to animal data> 

Create `.flaskenv` file under `ngs_server` folder. Put in the following cotent.

    FLASK_APP=Aptitude_NGS.py

    
### Step 5. Initiate databse. 
Initiate the database in mysql server by run:
    
    $ flask db init 
    $ flask db migrate 
    $ flask db update

Some errors might occur: 

* `ImportError: cannot import name 'ViennaRNA' from 'app.utils.folding' (unknown location)`

This is caused by the ViennaRNA package is missing in the git repository. Solve this by commenting out 
the first line in `ngs_server/app/utils/folding/_structurepredict.py` to avoid importing `ViennaRNA` package.
This way, you won't see predicted structure on NGS sequence page. Other function should be intact.

* `Error: No such command "db".` 

This could be caused by a few reasons.
1. Make sure you are at the top-level of `ngs_server` folder. 
2. Run `which flask`. If you are not getting `/path/to/your/folder/ngs_server/venv/bin/flask`
This means your virtual environment is not active. Try restart the terminal, `cd` to the `ngs_server` folder, 
then run `source venv/bin/activate` again. 

### Step 6. Run the website on development server. 

After you successfully initialize the database using `flask db init`, you will be able to lauch the applicaiton by running: 

    $ flask run 

If everything goes right, you should see: 

    * Serving Flask app "Aptitude_NGS.py"
    * Environment: production
    WARNING: This is a development server. Do not use it in a production deployment.
    Use a production WSGI server instead.
    * Debug mode: off
    * Running on http://127.0.0.1:5000/ (Press CTRL+C to quit) 

Then you can access the applicaiton on `http://127.0.0.1:5000/` in your browser.

All error information or `print()` information will be displayed in the terminal window during using the website.

### Step 7. Create new user in shell. 
The website is up, but you still need a user name and password to login. 

Quit the applicaiton by `CTRL + C`. Then run: 

    $ flask shell 
This starts a python interactive session to talk with the backend. All database bindings are provided.
You can create new user here.

    > newuser = user(username = 'admin',privilege='admin') 
    > newuser.set_password('admin')
    > db.session.add(newuser)
    > db.session.commit()

Then you can login with 'admin' / 'admin'. 

### Final thoughts.

Search function using elasticsearch is missing.  

Apps rely on bokeh server is not able to load. 


