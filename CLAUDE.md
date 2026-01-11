This is a demo app that monitors website uptime. 

Stack:

* Python
* uv
* FastAPI
* PostgreSQL
* Vanilla JS

You should be able to enter a website URL. The system should periodically check the website's uptime 
and store the results in a PostgreSQL database. We poll every 5 seconds. We should be able to view
a bar graph of the results that updates in real time with a simple red or green bar. The checks 
should happen in a background worker that saves the results to the database.
