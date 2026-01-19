import requests
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def check_internet_connection():
    logging.info("Checking internet connection upon startup")

    try:
        # Check for internet connectivity using requests
        response = requests.get("http://www.google.com", timeout=5)
        response.raise_for_status()  # will raise an exception if the request returned an unsuccessful status code
        internet_connected = True
        logging.info("i am ONLINE")
        
        # Prepare the print content
        print_content = (
            "\n"
            "hello, i am\n"
            "poetry camera\n"
            "and i am ONLINE!\n"
            "\n\n\n\n\n"
        )

    except (requests.ConnectionError, requests.Timeout, requests.HTTPError) as e:
        internet_connected = False
        logging.error(f"no internet! Error: {e}")
        
        # Prepare the print content for offline status
        print_content = (
            "\n"
            "hello, i am\n"
            "poetry camera\n"
            "but i'm OFFLINE!\n"
            "i need internet to work!\n"
            'connect to PoetryCameraSetup wifi network (pw: "password") on your phone or laptop to fix me!\n'
            "\n\n\n\n\n"
        )

    # Send the print request to the CatPrinter Flask server
    try:
        logging.info("Sending print request to CatPrinter Flask server")
        response = requests.post(
            "http://127.0.0.1:5002", 
            json={"text": print_content},
            timeout=5
        )
        if response.status_code == 200:
            logging.info("Print request sent successfully")
        else:
            logging.error(f"Failed to send print request: {response.status_code} {response.text}")
    except requests.RequestException as e:
        logging.error(f"Error sending print request: {e}")

if __name__ == "__main__":
    check_internet_connection()
