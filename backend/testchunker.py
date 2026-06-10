
from chunker import chunk_all_files
files = {
    'test.sql': '''
CREATE TABLE users (id INT, name VARCHAR(50));
CREATE PROCEDURE login_user(IN email VARCHAR(100))
BEGIN
    SELECT * FROM users WHERE email = email;
END;
CREATE TRIGGER after_insert AFTER INSERT ON users
FOR EACH ROW BEGIN
    INSERT INTO logs VALUES(NEW.id);
END;
''',
    'readme.md': '''
# My Project
## Installation
Run npm install
## Features  
Has auth and database
## API
REST endpoints
''',
    'config.json': '{\"name\": \"myapp\", \"version\": \"1.0.0\"}'
}
chunks = chunk_all_files(files)
for c in chunks:
    print(c['metadata']['filepath'], '|', c['metadata']['func_name'])