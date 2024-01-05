import requests
import os
import time
import tqdm

import constants
import utils


#def init_repositories():
    # First, we need to download the list of repositories from the Galaxy ToolShed
processed_repositories = {}

with open(constants.TOOL_SOURCES) as f:
    sources = f.read().splitlines()

# Concatenate sources and prepare for download
for source in sources:
    source_repositories_url = f"https://{source}/api/repositories"
    print("Downloading repository list from ", source_repositories_url)
    source_repositories = requests.get(source_repositories_url).json()
    
    for repository in tqdm.tqdm(source_repositories, desc=f"Preparing {source}"):
        id = f"{source} {repository['id']}"
        if id not in processed_repositories:
            processed_repositories[id] = {}
            processed_repositories[id]["processed"] = False
            
            processed_repositories[id]["name"] = repository["name"]
            if "description" in repository:
                processed_repositories[id]["description"] = repository["description"]
            processed_repositories[id]["downloads"] = repository["times_downloaded"]
    