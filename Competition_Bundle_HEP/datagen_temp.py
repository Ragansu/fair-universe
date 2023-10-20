import pandas as pd
from sys import path
import numpy as np
from sklearn.model_selection import train_test_split
import os
module_dir = os.path.dirname(os.path.realpath(__file__))
ingestion_dir = os.path.join(module_dir,'ingestion_program')
path.append(ingestion_dir)

from systematics import Systematics


# Load the CSV file
def DataGenerator():
    
    # Get the directory of the current script (my_module.py)
    module_dir = os.path.dirname(os.path.realpath(__file__))
    
    # Construct the absolute path to something.csv
    csv_file_path = os.path.join(module_dir, 'reference_data.csv')
    df = pd.read_csv(csv_file_path)

    # Remove the "label" and "weights" columns from the data


    flag = df.pop('Process_flag')
    label = df.pop('Label')
    weights = df.pop('Weight')
    entry = df.pop('entry')
    eventid = df.pop('EventId')
    df.pop('PRI_lep_charge')
    df.pop('PRI_had_charge')    
    df.pop('PRI_jet_leading_charge')    
    df.pop('PRI_jet_subleading_charge')

    # Print the features of the data
    features = df.columns.tolist()
    for feature in features:
        print(feature)



    print (f"[*] --- sum of weights : {np.sum(weights)}")
    print (f"[*] --- sum of signal : {np.sum(weights[label==1])}")
    print (f"[*] --- sum of background : {np.sum(weights[label==0])}")
    
    # Calculate the sum of weights of signal and background for the whole data
    total_signal_weight = np.sum(weights[label==1])
    total_background_weight = np.sum(weights[label==0])

    # Split the data into training and testing sets
    train_df, test_df, train_label, test_label, train_weights, test_weights = train_test_split(df, label, weights, test_size=0.3)

    # Create directories to store the label and weight files
    train_label_path =  os.path.join(module_dir, 'input_data/train/labels')
    if not os.path.exists(train_label_path):
        os.makedirs(train_label_path)

    train_weights_path =  os.path.join(module_dir, 'input_data/train/weights')
    if not os.path.exists(train_weights_path):
        os.makedirs(train_weights_path)

    train_data_path =  os.path.join(module_dir, 'input_data/train/data')
    if not os.path.exists(train_data_path):
        os.makedirs(train_data_path)

    train_settings_path =  os.path.join(module_dir, 'input_data/train/settings')
    if not os.path.exists(train_settings_path):
        os.makedirs(train_settings_path)



    test_label_path =  os.path.join(module_dir, 'input_data/test/labels')
    if not os.path.exists(test_label_path):
        os.makedirs(test_label_path)

    test_weights_path =  os.path.join(module_dir, 'input_data/test/weights')
    if not os.path.exists(test_weights_path):
        os.makedirs(test_weights_path)

    test_data_path =  os.path.join(module_dir, 'input_data/test/data')
    if not os.path.exists(test_data_path):
        os.makedirs(test_data_path)

    


    subset_signal_weight = np.sum(train_weights[train_label==1])
    subset_background_weight = np.sum(train_weights[train_label==0])


    # Adjust the weights of the training set to match the weights of the whole data

    train_weights[train_label==1] *= total_signal_weight / subset_signal_weight
    train_weights[train_label==0] *= total_background_weight / subset_background_weight

    print ("sum of signal" , np.sum(train_weights[train_label==1]))
    print ("sum of background" , np.sum(train_weights[train_label==0]))

    import json

    train_settings = {"tes": 1.0, "ground_truth_mu": 1.0}

    # Specify the file path
    Settings_file_path = os.path.join(train_settings_path, 'data.json')

    # Save the settings to a JSON file
    with open(Settings_file_path, 'w') as json_file:
        json.dump(train_settings, json_file, indent=4)

    # Save the label and weight files for the training set
    train_label_path =  os.path.join(train_label_path, 'data.labels')
    train_label.to_csv(train_label_path, index=False, header=False)

    train_weights_path =  os.path.join(train_weights_path, 'data.weights')
    train_weights.to_csv(train_weights_path, index=False, header=False)

    # Divide the test set into 10 equal parts and save each part as a separate CSV file
    test_dfs = [test_df[i:i+len(test_df)//10] for i in range(0, len(test_df), len(test_df)//10)]
    test_weights_ = [test_weights[i:i+len(test_weights)//10] for i in range(0, len(test_weights), len(test_weights)//10)]
    test_label_ = [test_label[i:i+len(test_label)//10] for i in range(0, len(test_label), len(test_label)//10)]

    mu_calc_set = test_dfs.pop(0)
    mu_calc_weights = test_weights_.pop(0)
    mu_calc_label = test_label_.pop(0)
    signal_mu_calc = np.sum(mu_calc_weights[mu_calc_label==1])
    background_mu_calc = np.sum(mu_calc_weights[mu_calc_label==0])  
    mu_calc_weights[mu_calc_label==1] *= total_signal_weight / signal_mu_calc
    mu_calc_weights[mu_calc_label==0] *= total_background_weight / background_mu_calc

    weights_file_path = os.path.join(test_weights_path, 'data_mu_calc.weights')
    labels_file_path = os.path.join(test_label_path, 'data_mu_calc.labels')
    data_file_path = os.path.join(test_data_path, 'data_mu_calc.csv')

    # Writing data to files
    mu_calc_weights.to_csv(weights_file_path, index=False, header=False)
    mu_calc_label.to_csv(labels_file_path, index=False, header=False)
    mu_calc_set.to_csv(data_file_path, index=False)



    for i, (test_df, test_weights, test_label) in enumerate(zip(test_dfs, test_weights_, test_label_)):
        # Calculate the sum of weights of signal and background for the current subset

        subset_signal_weight = np.sum(test_weights[test_label==1])
        subset_background_weight = np.sum(test_weights[test_label==0])
        
        # Adjust the weights of the current subset to match the weights of the whole data
        
        test_weights[test_label==1] *= total_signal_weight / subset_signal_weight
        test_weights[test_label==0] *= total_background_weight / subset_background_weight

        #adding systematics to the test set
        
        setting_path =  os.path.join(module_dir, f'reference_data/settings/data_{i}.json')
        with open(setting_path) as f:
            data = json.load(f)

        # Extract the TES information from the JSON file
        # tes = data['tes']
        tes = 1.0
        test_syst = test_df.copy()

        data_syst = Systematics(
        data=test_syst,
        tes=tes
        ).data

        mu = data['ground_truth_mu']
        print("mu = ",mu)

        signal =  test_weights[test_label==1].sum()
        background = test_weights[test_label==0].sum()

        # modify the label and weight of the test set for new ground truth mu
        test_weights[test_label==1] *= mu


        test_df = data_syst.copy()
        del test_syst



        # Save the current subset as a CSV file
        data_file_path = os.path.join(test_data_path, f'data_{i}.csv')
        weights_file_path = os.path.join(test_weights_path, f'data_{i}.weights')
        labels_file_path = os.path.join(test_label_path, f'data_{i}.labels')

        # Writing data to files
        test_df.to_csv(data_file_path, index=False)
        test_weights.to_csv(weights_file_path, index=False, header=False)
        test_label.to_csv(labels_file_path, index=False, header=False)

        print ("Shape of test set : ",np.shape(test_df))

        print ("sum of signal" , np.sum(test_weights[test_label==1]))
        print ("sum of background" , np.sum(test_weights[test_label==0]))
        print ("sum of weights" , np.sum(test_weights))
        print ("mu = ",(np.sum(test_weights) - np.sum(train_weights[train_label==0]))/np.sum(train_weights[train_label==1]))

    # Save the training set as a CSV file
    train_data_path = os.path.join(train_data_path, 'data.csv')
    train_df.to_csv(train_data_path, index=False)

    print ("Shape of train set : ",np.shape(train_df)) 

if __name__ == "__main__":
    DataGenerator() 

