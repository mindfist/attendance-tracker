import os
import re

import cv2
import numpy as np
import psycopg2
from flask import Flask, request, jsonify
from flask_cors import CORS, cross_origin

app = Flask(__name__)
CORS(app, supports_credentials=True)

FILE_PATH = os.path.dirname(os.path.realpath(__file__))

DATABASE_USER = os.environ['DATABASE_USER']
DATABASE_PASSWORD = os.environ['DATABASE_PASSWORD']
DATABASE_HOST = os.environ['DATABASE_HOST']
DATABASE_PORT = os.environ['DATABASE_PORT']
DATABASE_NAME = os.environ['DATABASE_NAME']


def get_db_connection():
    return psycopg2.connect(user=DATABASE_USER,
                            password=DATABASE_PASSWORD,
                            host=DATABASE_HOST,
                            port=DATABASE_PORT,
                            database=DATABASE_NAME)


@app.route('/receive_data', methods=['POST'])
def get_receive_data():
    """
    get data from the face recognition
    :return:
    """
    if request.method == 'POST':
        json_data = request.get_json()
        date = json_data['date']
        name = json_data['name']

        # Check if the user is already in the DB
        try:
            # Connect to the DB
            connection = get_db_connection()
            cursor = connection.cursor()

            # Query to check if the user as been saw by the camera today
            user_saw_today_sql_query = f"select * from users where date = `{date}` and name=" \
                                       f"`{name}`"

            cursor.execute(user_saw_today_sql_query)
            result = cursor.fetchall()
            connection.commit()

            # If use is already in the DB for today
            if result:
                print('user in')
                image_path = f"{FILE_PATH}/assets/img/{date}/{name}/departure.jpg"

                # Save image
                os.makedirs(f"{FILE_PATH}/assets/img/{date}/{name}", exit_ok=True)
                cv2.imwrite(image_path, np.array['picture_array'])
                json_data['picture_path'] = image_path

                update_user_query = f"update users set departure_time = `{json_data['hour']}`, departure_picture= `" \
                                    f"{json_data['picture_path']}` where name=`{name}` and date=`{date}`"

            else:
                print('user out')
                # Save image
                image_path = f"{FILE_PATH}/assets/img/history/{date}/{name}/arrival.jpg"
                os.makedirs(f"{FILE_PATH}/assets/img/history/{date}/{name}", exist_ok=True)
                cv2.imwrite(image_path, np.array(json_data['picture_array']))
                json_data['picture_path'] = image_path

                # Create a new row for the user today:
                insert_user_query = f"insert into users (name, date, arrival_time, arrival_picture) values (`{name}`," \
                                    f"`{date}`, `{json_data['hour']}`, `{json_data['picture_path']}`)"
                cursor.execute(insert_user_query)

        except (Exception, psycopg2.DatabaseError) as error:
            print(f'Error DB :{error}')
        finally:
            connection.commit()

            if connection:
                cursor.close()
                connection.close()
                print("db connection is closed")
        return jsonify(json_data)


@app.route('/get_employee/<string:name>', methods=['GET'])
def get_employee(name):
    response = {}

    # check if user is already in db
    try:
        # get db connection
        connection = get_db_connection()
        cursor = connection.cursor()

        user_info_sql_query = f"select * from users where name=`{name}`"

        cursor.execute(user_info_sql_query)
        result = cursor.fetchall()
        connection.commit()

        if result:
            print('Result: ', result)
            for k, v in enumerate(result):
                response[k] = {}
                for ko, vo in enumerate(result[k]):
                    response[k][ko] = str(vo)
            print(f'GET employee response {response}')
        else:
            response = {'error': 'user not found'}
    except (Exception, psycopg2.DatabaseError) as Error:
        print(f'DB error: {Error}')
    finally:
        if connection:
            cursor.close
            connection.close
            print('db connection is close')
    return jsonify(response)


@app.route('/get_last_entries', methods=['GET'])
def get_last_entries():
    """
    Get last 5 users seen by the camera
    :return:
    """
    response = {}
    # check if the user is already in the db
    try:
        connection = get_db_connection()

        cursor = connection.cursor()
        last_enrires_sql_query = f"select * from users ORDER BY id DESC LIMIT 5;"

        cursor.execute(last_enrires_sql_query)
        result = cursor.fetchall()
        connection.commit()

        if result:
            # Structure the data and put the dates in string for the front
            for k, v in enumerate(result):
                response[k] = {}
                for ko, vo, in enumerate(result[k]):
                    response[k][ko] = str(vo)
            else:
                response = {'error': 'error in fetching data'}

    except (Exception, psycopg2.DatabaseError) as error:
        print(f"DB Error: {error}")
    finally:
        # close db connection
        if connection:
            cursor.close()
            connection.close()

    return jsonify(response)


@app.route('/add_employee', methods=['POST'])
@cross_origin(supports_credentials=True)
def add_employee():
    """
    add new employee
    :return:
    """
    try:
        # Get the picture from the request
        image_file = request.files['image']
        print(request.form['nameOfEmployee'])

        # Store it in the folder of the know faces
        file_path = os.path.join(f"assets/img/users/{request.form['nameOfEmployee']}.jpg")
        image_file.save(file_path)
        response = {'Success': 'New employee was successfully added'}
    except (Exception, os.error) as Error:
        response = {"Error": "Error while adding new employee" + str(Error)}
    return jsonify(response)


@app.route('/get_employee_list', methods=['GET'])
def get_employee_list():
    """
    get list of employee
    :return:
    """
    employee_list = {}

    # Walk in the user folder to get the user list
    walk_count = 0
    for file_name in os.listdir(f"{FILE_PATH}/assets/img/users/"):
        # Capture the employee's name with the file's name
        name = re.findall("(.*)\.jpg", file_name)
        if name:
            employee_list[walk_count] = name[0]
            walk_count += 1

    return jsonify(employee_list)


@app.route('/delete_employee/<string:name>', methods=['GET'])
def delete_employee(name):
    """
    Delete employee
    :param name: employee name to be deleted
    :return:
    """
    try:
        # Remove the picture of the employee from the user's folder
        print(f"Name: {name}")
        file_path = os.path.join(f'assets/img/users/{name}.jpg')
        os.remove(file_path)
        response = {"Success": "Employee successfully removed"}
    except (Exception, os.error) as Error:
        response = {"Error": "Error while deleting new employee. Please try again. Error : " + str(Error)}
    return jsonify(response)


if __name__ == '__main__':
    app.run()
