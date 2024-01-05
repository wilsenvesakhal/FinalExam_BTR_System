import requests
import os
import time
import tqdm

import constants
import utils


#Description :
#This function is used to download the tool list from the toolshed.g2.bx.psu.edu site.
#This function will produce information for each tool consisting of information processed, 
#name, description, and downloads. The results will be saved in json form.
def init_repositories():
    # First, we need to download the list of repositories from the Galaxy ToolShed
    if os.path.exists(constants.PROCESSED_REPOSITORIES):
        processed_repositories = utils.load_json(constants.PROCESSED_REPOSITORIES)
    else:
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
    
    utils.dump_json(processed_repositories, constants.PROCESSED_REPOSITORIES)



#Description :
# This function adds information for each tool from the json results
# produced by the init_repositories function, by adding information for tools 
# consisting of id, name, profile, and other information.
def download_repositories():
    # Now we download all tool repositories and extract the tools from them
    # Respecting the API wait time specified in constants
    # See Toolshed API for structure of metadata
    i = 0
    prev_time = 0
    processed_repositories = utils.load_json(constants.PROCESSED_REPOSITORIES)
    for id, repository in processed_repositories.items():
        i += 1
        if repository["processed"]:
            continue
        
        print("Processing repository {}/{}: {}".format(i, len(processed_repositories), repository["name"]))
        
        source, actual_id = id.split(" ")
        metadata_url = f"https://{source}/api/repositories/{actual_id}/metadata"
        
        while (time.time() - prev_time < constants.GALAXY_API_WAIT):
            time.sleep(0.1)
        
        metadata = requests.get(metadata_url).json()
        prev_time = time.time()
        
        if len(metadata) == 0 or "err_msg" in metadata:
            print("No metadata found, skipping...")
            continue
        
        # Get description(s) from latest version of repository
        latest_revision = list(metadata.values())[-1]
        if "tools" in latest_revision:
            repository["tools"] = latest_revision["tools"]
            for i_tool in range(len(repository["tools"])):
                tool = repository["tools"][i_tool]
                if "tests" in tool:
                    del repository["tools"][i_tool]["tests"]
        repository["processed"] = True
        utils.dump_json(processed_repositories, constants.PROCESSED_REPOSITORIES)

def run():
    print("Downloading tool names and descriptions from Toolshed sources")
    init_repositories()
    download_repositories()
    print("Done downloading tool descriptions")