import os
import csv
import pywebio
import PyPDF2
import io
import re
from openai import OpenAI
from PyPDF2 import PdfReader
from pywebio.input import *
from pywebio.output import *
from google.cloud import storage

# Define GPT API keys and GCS bucket keys
os.environ["OPENAI_API_KEY"] = "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"
client = OpenAI(
  api_key=os.environ['OPENAI_API_KEY'],
)
BUCKET_NAME = 'venturer_associates'

# Scrub PDF and return a string
def read_pdf(pdf_file):
    reader = PdfReader(pdf_file)
    number_of_pages = len(reader.pages)
    count = 0
    text = ("")
    while count < (number_of_pages-3):
        page = reader.pages[count]
        current_page = page.extract_text()
        text += current_page
        count += 1
    return text

# Scrub bytes object of PDF and return a string
def convert_pdf_to_text(pdf_bytes):
    pdf_text = ""
    pdf_wrapped = io.BytesIO(pdf_bytes)
    pdf_reader = PyPDF2.PdfReader(pdf_wrapped)

    for page_num in range(len(pdf_reader.pages)):
        page = pdf_reader.pages[page_num]
        pdf_text += page.extract_text()

    return pdf_text

# Upload PDF to GCS
def upload_to_gcs(file_content, filename):
    """Uploads a file to Google Cloud Storage"""
    storage_client = storage.Client()
    bucket = storage_client.bucket(BUCKET_NAME)
    blob = bucket.blob(filename)
    blob.upload_from_string(file_content, content_type='application/pdf')
    return blob.public_url

# Download PDF from GCS
def read_file_from_gcs(filename):
    """Reads a file from Google Cloud Storage"""
    storage_client = storage.Client()
    bucket = storage_client.bucket(BUCKET_NAME)
    blob = bucket.blob(filename)
    file_content = blob.download_as_string()
    return file_content

# Wipe PDF off GCS
def delete_file_from_gcs(file_name):
    try:
        # Initialize a client to interact with Google Cloud Storage
        storage_client = storage.Client()
        # Get the bucket and file
        bucket = storage_client.bucket(BUCKET_NAME)
        blob = bucket.blob(file_name)
        # Delete the file
        blob.delete()
        return True
    except Exception as e:
        return False

# Extract HTML output from GPT chat completion string
def extract_html_table(input_string):
    # Regular expression pattern to find the HTML table between <html> and </html> tags
    pattern = r"```html(.*?)```"
    # Using regex to find the HTML table
    match = re.search(pattern, input_string, re.DOTALL)
    if match:
        html_table = match.group(1).strip()
        return html_table
    else:
        return None

# App sequence deployed with pywebio
def main():
    """Undivided Ventures

    Internal AI Logic Engine
    """
    # Tutorial Video with three use cases
    put_markdown("# **Tutorial Video**")
    put_html("""
    <iframe width="560" height="315" src="https://www.youtube.com/embed/0-lfmnffsbI?si=lQcQUBD3wb_z0-9U" title="YouTube video player" frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share" allowfullscreen></iframe>
    """)

    # Landing page with use-case selection
    put_markdown("# **Logic Engine**")
    agenda = actions('Welcome to Undivided Ventures. How can I help you today?',[
                {'label':'Scrape a list of startups for investibles','value':'rankstartups','color':'primary'},
                {'label':'Analyse investible trends from PDF newsletter','value':'analysetrends','color':'danger'},
                {'label':'Scrape a list of startups and output data in a table','value':'scrapedata','color':'warning'}
                ], help_text='You can upload your PDF and required data in the next page')
    modelSelection = actions('Please select your AI model.',[
                {'label':'Base Model','value':'untrained','color':'primary'},
                {'label':'Preliminary Model (Beta Testing)','value':'trained','color':'warning'}
                ], help_text='You can upload your PDF and required data in the next page')

    # PDF upload Function
    pdf = file_upload("Please upload your PDF here", accept="pdf/*", placeholder='Maximum filesize of 3MB', multiple=False, max_size='10M')
    pdf_content = pdf['content']
    pdfname = pdf['filename']
    file_url = upload_to_gcs(pdf_content,pdfname)
    put_markdown("# **PDF Upload and Processing**")
    put_text('PDF rendered successfully! It has been stored in the cloud temporarily for processing. Please wait for the AI engine to respond.')
    stored_pdf = read_file_from_gcs (pdfname)

    # Model Selection
    if modelSelection == 'untrained':
        selectedModel="gpt-3.5-turbo-1106"
    if modelSelection == 'trained':
        selectedModel="ft:gpt-3.5-turbo-1106:venturer-associates::8yPSVf2O"

    # Use Case 1: Scraping startups and matching to investment thesis
    if agenda == 'rankstartups':
        thesis = input("What is your investment focus for the search?")
        startups = convert_pdf_to_text(stored_pdf)
        completion = client.chat.completions.create(
            model=selectedModel,
            messages=[
            {"role":"system","content":"You are an assistant"},
            {"role":"user", "content":"I am a climate focused venture capital firm. I invest in startups that relate to the built environment and touch on the themes of decarbonisation, circularity, social value, natural capital, or climate adaptation. From this pdf, please list all startup that fit this investment criteria and give me a one sentence description of each startup that fits the criteria. This is my investment thesis:"},
            {"role":"user","content":thesis},
            {"role":"user","content":"Please list all startups compatible with my investment thesis and briefly explain why each startup is suitable, selecting from this entrepreneurship newsletter containing potential startups and brief descriptions. "},
            {"role":"user","content":str(startups)}
            ]
            )
        put_markdown("# **Results**")
        put_text(completion.choices[0].message.content)
        put_html('<br><br>')
        put_markdown("# **Computational Resources**")
        cost = completion.usage.prompt_tokens/1000*0.1+completion.usage.completion_tokens/1000*0.2
        put_table([
        ['Estimated Cost, US cents', cost],
        ['Input Tokens', completion.usage.prompt_tokens],
        ['Output Tokens', completion.usage.completion_tokens],
        ['Total Tokens', completion.usage.total_tokens],
        ['Data Wiped From Cloud?', delete_file_from_gcs (pdfname)],
        ])

    # Use Case 2: Identifying investible megatrends
    if agenda == 'analysetrends':
        trends = convert_pdf_to_text(stored_pdf)
        completion = client.chat.completions.create(
            model=selectedModel,
            messages=[
            {"role":"system","content":"You are an assistant"},
            {"role":"user", "content":"I am a climate focused venture capital firm. This is a newsletter on recent trends in climate tech."},
            {"role":"user","content":str(trends)},
            {"role":"user","content":"What are the three promising sectors visible in this newsletter with sustainability impact which are receptive to investment? Please explain."},
            ]
            )
        put_markdown("# **Results**")
        put_text(completion.choices[0].message.content)
        put_html('<br><br>')
        put_markdown("# **Computational Resources**")
        cost = completion.usage.prompt_tokens/1000*0.1+completion.usage.completion_tokens/1000*0.2
        put_table([
        ['Estimated Cost, US cents', cost],
        ['Input Tokens', completion.usage.prompt_tokens],
        ['Output Tokens', completion.usage.completion_tokens],
        ['Total Tokens', completion.usage.total_tokens],
        ['Data Wiped From Cloud?', delete_file_from_gcs (pdfname)],
        ])

    # Use Case 3: Scrape startup data from input PDF and tabulate
    if agenda == 'scrapedata':
        database = convert_pdf_to_text(stored_pdf)
        completion = client.chat.completions.create(
            model=selectedModel,
            messages=[
            {"role":"system","content":"You are an assistant"},
            {"role":"user", "content":"This is a data string from a PDF containing a list of startups. "},
            {"role":"user","content": str(database)},
            {"role":"user","content":"I need a complete list of all the startups, please output the name, sector, year founded and other repeated data items of each and every startup in the form of a HTML table."}
            ]
            )
        extracted_startups = extract_html_table(completion.choices[0].message.content)
        put_markdown("# **Results**")
        put_html(extracted_startups)
        put_html('<br><br>')
        put_markdown("# **Computational Resources**")
        cost = completion.usage.prompt_tokens/1000*0.1+completion.usage.completion_tokens/1000*0.2
        put_table([
        ['Estimated Cost, US cents', cost],
        ['Input Tokens', completion.usage.prompt_tokens],
        ['Output Tokens', completion.usage.completion_tokens],
        ['Total Tokens', completion.usage.total_tokens],
        ['Data Wiped From Cloud?', delete_file_from_gcs (pdfname)],
        ])

# Deploy webapp on public address by calling main function
if __name__ == '__main__':
    import argparse
    from pywebio.platform.tornado_http import start_server as start_http_server
    from pywebio import start_server as start_ws_server

    parser = argparse.ArgumentParser()
    parser.add_argument("-p", "--port", type=int, default=8080)
    parser.add_argument("--http", action="store_true", default=False, help='Whether to enable http protocol for communicates')
    args = parser.parse_args()

    if args.http:
        start_http_server(main, port=args.port)
    else:
        # Since some cloud server may close idle connections (such as heroku),
        # use `websocket_ping_interval` to  keep the connection alive
        start_ws_server(main, port=args.port, websocket_ping_interval=30)
