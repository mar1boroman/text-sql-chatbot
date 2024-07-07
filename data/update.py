import sqlite3

def update_car_price(db_path, car_id, new_price):
    # Connect to the SQLite database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Update the price of the car with the specified id
    update_query = 'UPDATE Cars_Price SET price = ? WHERE id = ?'
    cursor.execute(update_query, (new_price, car_id))
    
    # Commit the changes and close the connection
    conn.commit()
    conn.close()
    
    print(f"Price of car with id {car_id} updated to {new_price} successfully.")

# Example usage
db_path = 'cars_database.db'
car_id = 5
new_price = 300000.00

update_car_price(db_path, car_id, new_price)