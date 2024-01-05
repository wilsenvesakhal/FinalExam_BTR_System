import os
import pickle
import pandas as pd
import networkx as nx
import numpy as np
from fuzzywuzzy import fuzz

import torch
import torch_geometric

import constants
import model
import utils
import data_loader

#Description :
#This function is used to processes a graph path, associates embeddings with nodes.
def path_to_data(path):
    x = path
    
    steps = [node[0] for node in x]
    id_to_embedding = {node[0]: node[1] for node in x}
    indices, x = pd.factorize(steps)
    
    senders, receivers = indices[:-1], indices[1:]
    
    # Associate embedding with tool instance in sequence
    full_x = []
    for item in x:
        seq = [item]
        seq.extend(id_to_embedding[item])
        full_x.append(seq)
    
    full_x = torch.tensor(full_x, dtype=torch.float)
    edge_index = torch.tensor([senders, receivers], dtype=torch.long)

    data = torch_geometric.data.Batch.from_data_list([torch_geometric.data.Data(x=full_x, edge_index=edge_index)])
    
    return data

#Description :
#This function is used to evaluate model on some input data
def predict(model, data):
    model.eval()
    with torch.no_grad():
        logits = model(data)
        return logits

#Description :
#check whether each element in the sequence entered by the user is recognized by the tool name list.
#If it is not recognized, it will recommend 10 other tools that are similar to that element.
def validate_sequence(input_sequence, all_tool_names):
    sequence = [tool.strip() for tool in input_sequence]
    
    if len(sequence) == 0:
        print("No sequence provided")
        return []
    
    true_sequence = []
    for tool in sequence:
        if tool in all_tool_names:
            true_sequence.append(tool)
        else:
            distances = {}
            for name in all_tool_names:
                distances[name] = fuzz.ratio(name, tool)
            
            sorted_candidates = sorted(distances.items(), key=lambda x: x[1], reverse=True)
            
            print(f"Tool {tool} not found in workflow, showing {constants.CANDIDATES_TO_SHOW} potential matches:")
            for i in range(constants.CANDIDATES_TO_SHOW):
                print(f"{i + 1}. {sorted_candidates[i][0]}")
            
            if (constants.MATCH_INTERACTIVELY):
                print("0 to exit")
                print("Please select a tool to use:")
                
                while True:
                    try:
                        selection = int(input())
                        if selection == 0:
                            return []
                        elif selection > 0 and selection <= constants.CANDIDATES_TO_SHOW:
                            true_sequence.append(sorted_candidates[selection - 1][0])
                            break
                    except:
                        print("Invalid input, please try again")
            else:
                return []

#Description:
#To convert sequence entered by the user
def convert_sequence(sequence, tool_name_to_id, toolbox):
    converted_sequence = []
    for tool in sequence:
        embedding = toolbox[tool]["embedding"]
        converted_sequence.append((tool_name_to_id[tool], embedding))
    
    return converted_sequence

def get_recommendation(base_config, model_base_loc, optimize_base_loc, input_sequence):
    info = utils.load_json(os.path.join(model_base_loc, "info.json"))
    tool_name_to_id = info["tool_name_to_id"]
    all_tool_names = list(tool_name_to_id.keys())
    sequence  = input_sequence
    sequence = validate_sequence(input_sequence, all_tool_names)
    
    if len(sequence) == 0:
        return []
    
    config = base_config.copy()
    best_params = utils.load_json(os.path.join(optimize_base_loc, "best_hyperparameters.json"))
    
    for key, value in best_params.items():
        config[key] = value
    
    config["hidden_channels"] = int(config["hidden_channels"])
    config["step_size"] = int(config["step_size"])
    config["batch_size"] = int(config["batch_size"])
    config["epochs"] = int(config["epochs"])
    config["model_path"] = model_base_loc
    config = data_loader.add_data_config(config)
    
    toolbox, _ = utils.load_toolbox()
    
    id_sequence = convert_sequence(sequence, tool_name_to_id, toolbox)
    data = path_to_data(id_sequence)
    loaded_model = model.load_model(config)
    
    logits = predict(loaded_model.to('cuda'), data.to('cuda'))
    recommendations = torch.topk(logits, constants.TOOLS_TO_RECOMMEND)[1].view(-1).cpu().detach().numpy()
    
    tool_id_to_name = { v: k for k, v in tool_name_to_id.items() }
    recommended_tools = [tool_id_to_name[tool_id] for tool_id in recommendations]
    
    return recommended_tools

model_base_loc = os.path.join(constants.OUT_LOC, constants.MODEL_NAME)
optimize_base_loc = os.path.join(constants.OUT_LOC, "{}_optimize".format(constants.MODEL_NAME))


base_config = {
    "device": "cuda",
    "model_type": constants.MODEL_TYPE,
    "hidden_channels": 32,
    "learning_rate": 0.001,
    "l2_penalty": 0.00001,
    "step_size": 30,
    "weight_decay": 0.1,
    "emb_dropout": 0.0,
    "dropout": 0.0,
    "epochs": 100,
    "batch_size": 100,
    "model_path": optimize_base_loc,
    "model_name": "model.pt",
    "top_k": constants.HITRATE_K,
    "mrr_k": constants.MRR_K,
}


recommended_tools=get_recommendation(base_config, model_base_loc, optimize_base_loc, ['umi_tools_extract','rna_star','bamFilter'])



