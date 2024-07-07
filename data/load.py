import csv
import sqlite3

# File paths
cars_country_path = 'data/Cars_Country.csv'
cars_multi_path = 'data/Cars_Multi.csv'
cars_price_path = 'data/Cars_Price.csv'

# Create a SQLite database connection
conn = sqlite3.connect('cars_database.db')
cursor = conn.cursor()

# Create the tables
cursor.execute('''
CREATE TABLE IF NOT EXISTS Cars_Country (
    origin TEXT PRIMARY KEY,
    country_name TEXT
)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS Cars_Multi (
    id INTEGER PRIMARY KEY,
    name TEXT,
    mpg REAL,
    cylinders INTEGER,
    displacement REAL,
    horsepower REAL,
    weight REAL,
    acceleration REAL,
    model_year INTEGER,
    origin TEXT,
    FOREIGN KEY (origin) REFERENCES Cars_Country(origin)
    
)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS Cars_Price (
    id INTEGER PRIMARY KEY,
    price REAL
)
''')

# Function to insert data into a table from a CSV file
def insert_data_from_csv(file_path, table_name, columns):
    with open(file_path, 'r') as file:
        reader = csv.reader(file)
        next(reader)  # Skip header row
        rows = [tuple(row) for row in reader]
        placeholders = ', '.join(['?'] * len(columns))
        cursor.executemany(f'INSERT INTO {table_name} ({", ".join(columns)}) VALUES ({placeholders})', rows)

# Insert data into the tables
insert_data_from_csv(cars_country_path, 'Cars_Country', ['origin', 'country_name'])
insert_data_from_csv(cars_multi_path, 'Cars_Multi', ['id', 'mpg', 'cylinders', 'displacement', 'horsepower', 'weight', 'acceleration', 'model_year', 'origin', 'name'])
insert_data_from_csv(cars_price_path, 'Cars_Price', ['id', 'price'])

# Commit changes and close the connection
conn.commit()
conn.close()

print("Data successfully loaded into the SQLite database.")