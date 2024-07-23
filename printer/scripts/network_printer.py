import cups
import os
from dotenv import load_dotenv
from datetime import datetime

# Load environment variables
load_dotenv()

class NetworkPrinter:
    def __init__(self):
        self.printer_name = os.getenv('PRINTER_NAME')
        self.conn = cups.Connection()
        self.filename = "/tmp/print_job.txt"

    def clear_file(self):
        open(self.filename, 'w').close()

    def print_text(self, text):
        # Clear the file before writing new content
        self.clear_file()
        
        with open(self.filename, "w") as f:
            f.write(text)
        self.conn.printFile(self.printer_name, self.filename, "Poetry Camera Print", {})

    def print_poem(self, poem):
        self.print_text(poem)

    def get_header(self):
        # No longer returning date and time
        return ""

    def get_footer(self):
        current_date = datetime.now().strftime("%B %d, %Y")
        footer = f"\n\nWRITTEN BY THE GHOST IN THE MACHINE\n{current_date}\n"
        return footer
