Hi everyone, this project analyzes a database in MySQL, including its schema and transactions. 
There are three files in this project:

binlog_parser: This file parses the binlog file, which has the record of all the changes made in database.

schema_parser: This file processes database schema information and parses the schema file, generating a mapping between table names and columns

binlog_analyser: This file provides statistics and insight on the changes and transactions recorded in the binlog.