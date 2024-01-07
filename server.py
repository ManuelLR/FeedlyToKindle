# This is a simple http server that can be used to generate and serve the news to download it directly from your e-reader.
#

import os
import sys
import time
import logging
import subprocess
import aiohttp
import asyncio
from datetime import datetime, timedelta

from aiohttp import web
from aiohttp.web import Request, Response, json_response
from aiohttp.web_exceptions import HTTPNotFound, HTTPBadRequest

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

# Get the command from the environment variable
# FTK_SERVER_GENERATOR_COMMAND = os.getenv("FTK_SERVER_GENERATOR_COMMAND", "touch ${FTK_GENERATOR_OUTPUT_FILE}")
FTK_SERVER_GENERATOR_COMMAND = os.getenv("FTK_SERVER_GENERATOR_COMMAND", """ebook-convert /FeedlyToCalibre.recipe "${FTK_GENERATOR_OUTPUT_FILE}" --output-profile=kindle_pw3 --verbose""")
if FTK_SERVER_GENERATOR_COMMAND == None:
    raise Exception("FTK_SERVER_GENERATOR_COMMAND is not set")

FTK_SERVER_GENERATOR_OUTPUT_FORMAT = os.getenv("FTK_SERVER_GENERATOR_OUTPUT_FORMAT", "mobi")
if FTK_SERVER_GENERATOR_OUTPUT_FORMAT == None:
    raise Exception("FTK_SERVER_GENERATOR_OUTPUT_FORMAT is not set")

# Get the directory from the environment variable
FTK_SERVER_FILES_DIR = os.getenv("FTK_SERVER_FILES_DIR", "/output")
if FTK_SERVER_FILES_DIR == None:
    raise Exception("FTK_SERVER_FILES_DIR is not set")

# Get the port from the environment variable
FTK_SERVER_PORT = os.getenv("FTK_SERVER_PORT", "8080")
if FTK_SERVER_PORT == None:
    raise Exception("FTK_SERVER_PORT is not set")
FTK_SERVER_PORT = int(FTK_SERVER_PORT)

async def main_handler(request: Request) -> Response:
    """Render the main page."""
    logging.debug('Received a request to render the main page')
    # Get the list of files
    files = get_files()
    # Render the main page
    return web.Response(text=f"""
        <html>
            <head>
                <title>Feedly to your Kindle</title>
            </head>
            <body>
                <h1>Feedly to your Kindle</h1>
                <a href="/generate_news">Generate latest news & download it</a>
                <h2>Generated news</h2>
                (<a href="/">Refresh the list</a>)
                <ul>
                    {"".join([f"<li><a href='/file/{file}'>{file}</a></li>" for file in files])}
                </ul>
                <hr>
                <form action="/remove_old_files" method="get">
                    <p><input type="submit" value="Remove files"> older than <input type="number" name="days" min="1" max="365" value="7"> days</p>
                </form>
            </body>
        </html>
    """, content_type="text/html")

async def generate_news(request: Request) -> Response:
    """Generate the file."""
    logging.debug('Received a request to generate a file')
    try:
        file_path = f'{FTK_SERVER_FILES_DIR}/FeedlyToKindle_{datetime.now().strftime("%Y-%m-%dT%H-%M")}.{FTK_SERVER_GENERATOR_OUTPUT_FORMAT}'
        # Execute the command to generate the file injecting the variable FTK_GENERATOR_OUTPUT_FILE with the path to the file
        subprocess.run(FTK_SERVER_GENERATOR_COMMAND, shell=True, check=True, stderr=sys.stderr, stdout=sys.stdout,
            env=dict(
                os.environ,
                FTK_GENERATOR_OUTPUT_FILE=file_path
            ))

        logging.debug('Generated file: "%s"', file_path)
        # Return the file
        file_name = os.path.basename(file_path)
        return web.HTTPFound(f'/file/{file_name}')
    except subprocess.CalledProcessError as e:
        logging.error('Error generating file: "%s"', e)
        raise HTTPBadRequest(reason="Error generating file")

def get_files() -> list:
    """Get the list of files on a directory sorted by creation date (the newest should be the first one)."""
    files = []
    for file in os.listdir(FTK_SERVER_FILES_DIR):
        file_path = os.path.join(FTK_SERVER_FILES_DIR, file)
        if os.path.isfile(file_path):
            files.append(file_path)
    files.sort(key=os.path.getctime, reverse=True)
    # Remove the directory from the path
    files = [os.path.basename(file) for file in files]

    return files

async def get_file_handler(request: Request) -> Response:
    """Get the epub file."""
    logging.debug('Received a request to get a file')
    file_name = request.match_info['file_name']
    # Check avoid directory traversal attacks
    if file_name.find('/') != -1:
        raise HTTPBadRequest(reason="Invalid file name")
    file_path = os.path.join(FTK_SERVER_FILES_DIR, file_name)
    if os.path.isfile(file_path):
        return web.FileResponse(file_path)
    else:
        raise HTTPNotFound()

async def remove_old_files(request: Request) -> Response:
    """Remove old files."""
    logging.debug('Received a request to remove old files')
    try:
        days = int(request.query['days'])
        if days < 1:
            raise HTTPBadRequest(reason="Invalid number of days")
    except KeyError:
        raise HTTPBadRequest(reason="Invalid number of days")
    except ValueError:
        raise HTTPBadRequest(reason="Invalid number of days")

    files_to_remove = []
    for file in os.listdir(FTK_SERVER_FILES_DIR):
        file_path = os.path.join(FTK_SERVER_FILES_DIR, file)
        if os.path.isfile(file_path):
            file_creation_date = datetime.fromtimestamp(os.path.getctime(file_path))
            if datetime.now() - file_creation_date > timedelta(days=days):
                files_to_remove.append(file_path)

    logging.debug('Removing files: "%s"', files_to_remove)
    for file in files_to_remove:
        os.remove(file)

    logging.debug('Files deleted!')

    return web.HTTPFound('/')

def main():
    """Start the server."""
    # Create the web application
    app = web.Application()
    # Add the routes
    app.add_routes([web.get('/', main_handler),
                    web.get('/generate_news', generate_news),
                    web.get('/file/{file_name}', get_file_handler),
                    web.get('/remove_old_files', remove_old_files)])
    # Start the web application
    web.run_app(app, port=FTK_SERVER_PORT)

if __name__ == "__main__":
    main()
