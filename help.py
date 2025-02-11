import csv
import json
import requests
from datetime import datetime
api_url="https://patara.choicemarriage.com/backend-api/public/api-call-for-all-data"
def csv_to_json(csv_file_path, json_file_path):
    data = []

    # Open and read the CSV file
    with open(csv_file_path, mode='r', encoding='utf-8') as csv_file:
        csv_reader = csv.DictReader(csv_file)  # Reads CSV into a dictionary
        # print(csv_reader)
        for row in csv_reader:
            row['phone']=row['phone'].lstrip("-")
            # print(row['dob'])
            # Convert to datetime object
            # Example input (replace with actual data)
            date_str = row["dob"]  # Make sure this is not empty
            row['user_subcaste']="Patara"

            if date_str.strip():  # Check if the string is not empty
                try:
                    # Convert to datetime object
                    date_obj = datetime.strptime(date_str, "%d-%m-%Y")
                    
                    # Convert back to desired format
                    formatted_date = date_obj.strftime("%Y-%m-%d")
                    # print("Converted Date:", formatted_date)
                    row['dob']=formatted_date
                
                except ValueError as e:
                    print("Error: Invalid date format -", e)
            else:
                print("Error: Date string is empty")
           
            try:
                response = requests.post(api_url, json=row)
                if response.status_code in [200, 201]:
                    # print(f"Success: {response.json()}")
                    row['apiOperationStatus']=True
                    row['apiOperationresposce']=response.json()
                else:
                    row['apiOperationStatus']=False
                    row['apiOperationresposce']=response.json()
                    # print(f"Failed to send data: {response.status_code}, {response.text}")
            except requests.exceptions.RequestException as e:
                row['apiOperationStatus']=False
                row['apiOperationresposce']=str(e)
            
            # response=requests.get('https://patara.choicemarriage.com/backend-api/public/setting')

            # row['apiOperationresposce']="ok"
            data.append(row)

    # Write the JSON data into a file
    with open(json_file_path, mode='w', encoding='utf-8') as json_file:
        json.dump(data, json_file, indent=4)

    return data

# Example usageC:\Users\Surayanarayan\Downloads
csv_file = "C:Users/Surayanarayan/Downloads/registered_member_data.csv"
json_file = 'd.json'  # Change this to your JSON file path
json_data = csv_to_json(csv_file, json_file)

# print(json.dumps(json_data, indent=4))  # Print JSON array
# import requests


# response=requests.get('https://patara.choicemarriage.com/backend-api/public/setting')


# print(response.json())