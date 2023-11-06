# ================================
# External Imports
# ================================
import os
import json
import numpy as np
import scipy as sp
import pandas as pd
from sklearn.utils import shuffle
from sys import exit

# ================================
# Internal Imports
# ================================
from distributions import Gaussian, Gamma
from systematics import Translation, Scaling, Box, Rotation
from logger import Logger
from checker import Checker
from constants import (
    DISTRIBUTION_GAUSSIAN,
    DISTRIBUTION_GAMMA,
    SYSTEMATIC_TRANSLATION,
    SYSTEMATIC_SCALING,
    SYSTEMATIC_BOX,
    SYSTEMATIC_ROTATION,
    SIGNAL_LABEL,
    BACKGROUND_LABEL
)


# ================================
# Data Generation Class
# ================================
class DataGenerator:
    def __init__(self, settings_dict=None, logs=False):

        if logs:
            print("############################################")
            print("### Data Generation")
            print("############################################")

        # -----------------------------------------------
        # Initialize logger class
        # -----------------------------------------------
        self.logger = Logger(show_logs=logs)

        # -----------------------------------------------
        # Initialize checks class
        # -----------------------------------------------
        self.checker = Checker()

        # -----------------------------------------------
        # Initialize data members
        # -----------------------------------------------
        self.settings = None
        self.visualize_settings = None
        self.signal_distribution = None
        self.background_distribution = None
        self.systematic_translation = None
        self.systematic_scaling = None
        self.systematic_box = None
        self.systematic_rotation = None
        self.systematics_loaded = False

        self.generated_data = None
        self.generated_labels = None

        self.biased_data = None
        self.biased_labels = None

        self.problem_dimension = None
        self.ps, self.pb = None, None
        self.total_number_of_events = None
        self.number_of_background_events = None
        self.number_of_signal_events = None

        self.apply_copula = False
        # parameters of Gamma distribution
        self.alpha = None 
        self.beta = None

        self.settings = settings_dict
        self.logger.success("Settings Loaded!")

        # -----------------------------------------------
        # Load parameters from Settings
        # -----------------------------------------------
        self.problem_dimension = self.settings["problem_dimension"]
        self.total_number_of_events = self.settings["total_number_of_events"]

        self.pb = self.settings["p_b"]
        self.ps = round(1 - self.pb, 5)

        self.number_of_signal_events = int(self.total_number_of_events*self.ps)
        self.number_of_background_events = int(self.total_number_of_events * self.pb)

        # -----------------------------------------------
        # Load Background distribution
        # -----------------------------------------------
        background_dist = self.settings["background_distribution"]
        if background_dist["name"] == DISTRIBUTION_GAUSSIAN:
            self.background_distribution = Gaussian({
                "name": DISTRIBUTION_GAUSSIAN,
                "mu":  background_dist["mu"],
                "sigma": background_dist["sigma"],
                "generator": self.settings["generator"],
                "angle_rotation": self.settings.get('angle_rotation', 0)
            })

        if background_dist["name"] == DISTRIBUTION_GAMMA:
            self.background_distribution = Gamma({
                "name": DISTRIBUTION_GAMMA,
                "k":  background_dist["k"],
                "_theta_": background_dist["_theta_"]
            })

        # get copula
        self.apply_copula = self.settings.get("apply_copula", False)
        # set parameters of Gamma distribution
        self.alpha = self.settings.get("alpha", None)
        self.beta = self.settings.get("beta", None)

        if self.background_distribution is None:
            self.logger.error("Background distribution should be Gaussian or Gamma!")
            exit()
        else:
            self.logger.success("Background Distributions Loaded!")

        # -----------------------------------------------
        # Load Signal distribution
        # -----------------------------------------------
        box_center = [0, 0]
        if self.settings["signal_from_background"] and background_dist["name"] == DISTRIBUTION_GAUSSIAN:

            theta = self.settings["theta"]
            L = self.settings["L"]
            signal_sigma_scale = self.settings["signal_sigma_scale"]
            signal_sigma = np.multiply(background_dist["sigma"], signal_sigma_scale)
            signal_mu = background_dist["mu"] + np.array([L*np.cos(np.radians(theta)), L*np.sin(np.radians(theta))])
            box_center = signal_mu.tolist()
            self.signal_distribution = Gaussian({
                "name": DISTRIBUTION_GAUSSIAN,
                "mu":  signal_mu,
                "sigma": signal_sigma,
                "generator": self.settings["generator"],
                "angle_rotation": - self.settings.get('angle_rotation', 0)
            })
        else:
            signal_dist = self.settings["signal_distribution"]
            if signal_dist["name"] == DISTRIBUTION_GAUSSIAN:
                self.signal_distribution = Gaussian({
                    "name": DISTRIBUTION_GAUSSIAN,
                    "mu":  signal_dist["mu"],
                    "sigma": signal_dist["sigma"],
                    "generator": self.settings["generator"],
                    "angle_rotation": - self.settings.get('angle_rotation', 0)
                })
                box_center = signal_dist["mu"]

        if self.signal_distribution is None:
            self.logger.error("Signal Distributions should be Gaussian only!")
        else:
            self.logger.success("Signal Distributions Loaded!")

        self.settings["box_center"] = box_center

        # -----------------------------------------------
        # Load Systematics
        # -----------------------------------------------

        if "systematics" not in self.settings:
            self.logger.error("Systematics not found in settings")

        systematics = self.settings["systematics"]
        for systematic in systematics:

            # Translation
            if systematic["name"] == SYSTEMATIC_TRANSLATION:
                z_magnitude = systematic["z_magnitude"]
                alpha = systematic["alpha"]
                z = np.multiply([np.cos(np.radians(alpha)), np.sin(np.radians(alpha))], z_magnitude)
                self.systematic_translation = Translation({
                    "name": SYSTEMATIC_TRANSLATION,
                    "allowed_dimension": -1,
                    "translation_vector": z

                })

            # Scaling
            if systematic["name"] == SYSTEMATIC_SCALING:
                scaling_factor = systematic["scaling_factor"]
                if scaling_factor > 1:
                    self.systematic_scaling = Scaling({
                        "name": SYSTEMATIC_SCALING,
                        "allowed_dimension": -1,
                        "scaling_vector": [scaling_factor, scaling_factor]

                    })

            # Box
            if systematic["name"] == SYSTEMATIC_BOX:
                box_length = systematic["box_l"]
                if box_length > 1:
                    self.systematic_box = Box({
                        "name": SYSTEMATIC_BOX,
                        "box_center": box_center,
                        "box_length": box_length
                    })

            # Rotation
            if systematic["name"] == SYSTEMATIC_ROTATION:
                rotation_degree = systematic["rotation_degree"]
                if rotation_degree != 0:
                    self.systematic_rotation = Rotation({
                        "name": SYSTEMATIC_BOX,
                        "rotation_degree": rotation_degree
                    })

        self.systematics_loaded = True
        self.logger.success("Systematics Loaded!")

    def generate_data(self):

        # -----------------------------------------------
        # Check distributions loaded
        # -----------------------------------------------
        if self.checker.distribution_is_not_loaded(self.signal_distribution):
            self.logger.error("Signal distribution is not loaded!")
            exit()
        if self.checker.distribution_is_not_loaded(self.background_distribution):
            self.logger.error("Background distribution is not loaded!")
            exit()

        # -----------------------------------------------
        # Check systematics loaded
        # -----------------------------------------------
        if not self.systematics_loaded:
            self.logger.error("Systematics are not loaded!")
            exit()

        # column names
        columns = ["x{}".format(i+1) for i in range(0, self.settings["problem_dimension"])]
        columns.append("y")

        # -----------------------------------------------
        # Generate Data
        # -----------------------------------------------

        # get train signal datapoints
        signal_data = self.signal_distribution.generate_points(self.number_of_signal_events, self.problem_dimension)
        # get train background datapoints
        background_data = self.background_distribution.generate_points(self.number_of_background_events, self.problem_dimension)

        # get test signal datapoints
        biased_signal_data = self.signal_distribution.generate_points(self.number_of_signal_events, self.problem_dimension)
        # get test background datapoints
        biased_background_data = self.background_distribution.generate_points(self.number_of_background_events, self.problem_dimension)

        self.logger.success("Data Generated!")

        # -----------------------------------------------
        # Apply copula on Background Distribution
        # -----------------------------------------------
        if self.apply_copula:

            if self.alpha and self.beta:
                c_bg_data = sp.stats.norm.cdf(background_data)
                background_data = sp.stats.gamma.ppf(c_bg_data, self.alpha, self.beta)

                c_biased_bg_data = sp.stats.norm.cdf(biased_background_data)
                biased_background_data = sp.stats.gamma.ppf(c_biased_bg_data, self.alpha, self.beta)

            else:
                self.logger.warning("Parameters of Gamma Distribution (alpha, beta) are not valid")

        # -----------------------------------------------
        # Set Distribution centers
        # -----------------------------------------------
        # setting centers of both distributions before applying systematics for visualizations
        self.settings["signal_center"] = np.mean(signal_data, axis=0).tolist()
        self.settings["background_center"] = np.mean(background_data, axis=0).tolist()

        # -----------------------------------------------
        # Apply Rotation, Translation, Scaling and Box Systematics
        # -----------------------------------------------

        # Rotation
        if self.systematic_rotation is not None:
            biased_signal_data = self.systematic_rotation.apply_systematics(self.problem_dimension, biased_signal_data)
            biased_background_data = self.systematic_rotation.apply_systematics(self.problem_dimension, biased_background_data)
            self.logger.success("Rotation Systematics Applied!")

        # Translation
        if self.systematic_translation is not None:
            biased_signal_data = self.systematic_translation.apply_systematics(self.problem_dimension, biased_signal_data)
            biased_background_data = self.systematic_translation.apply_systematics(self.problem_dimension, biased_background_data)
            self.logger.success("Translation Systematics Applied!")

        # Scaling
        if self.systematic_scaling is not None:
            biased_signal_data = self.systematic_scaling.apply_systematics(self.problem_dimension, biased_signal_data)
            biased_background_data = self.systematic_scaling.apply_systematics(self.problem_dimension, biased_background_data)
            self.logger.success("Scaling Systematics Applied!")

        # setting centers of both distributions before applying systematics for visualizations
        self.settings["signal_center_biased"] = np.mean(biased_signal_data, axis=0).tolist()
        self.settings["background_center_biased"] = np.mean(biased_background_data, axis=0).tolist()
        # -----------------------------------------------
        # Generate labels
        # -----------------------------------------------

        # stack signal labels with data points
        signal_labels = np.repeat(SIGNAL_LABEL, signal_data.shape[0]).reshape((-1, 1))
        signal_original = np.hstack((signal_data, signal_labels))
        signal_biased = np.hstack((biased_signal_data, signal_labels))

        # stack background labels with data points
        background_labels = np.repeat(BACKGROUND_LABEL, background_data.shape[0]).reshape((-1, 1))
        background_original = np.hstack((background_data, background_labels))
        background_biased = np.hstack((biased_background_data, background_labels))

        # -----------------------------------------------
        # Create DataFrame from Data
        # -----------------------------------------------

        # create signal df
        signal_df = pd.DataFrame(signal_original, columns=columns)
        # create signal df biased
        signal_df_biased = pd.DataFrame(signal_biased, columns=columns)

        # create background df
        background_df = pd.DataFrame(background_original, columns=columns)
        # create background df biased
        background_df_biased = pd.DataFrame(background_biased, columns=columns)

        # -----------------------------------------------
        # Combine Signal and Background in a DataFrame
        # -----------------------------------------------

        # combine dataframe
        generated_dataframe = pd.concat([signal_df, background_df])
        biased_dataframe = pd.concat([signal_df_biased, background_df_biased])

        # -----------------------------------------------
        # Apply Box Systematics
        # -----------------------------------------------

        if self.systematic_box is not None:
            generated_dataframe, biased_dataframe = self.systematic_box.apply_systematics(generated_dataframe, biased_dataframe)
            self.logger.success("Box Systematics Applied!")
        # -----------------------------------------------
        # Separate original and biased data
        # -----------------------------------------------

        # generated data labels
        self.generated_data = generated_dataframe[generated_dataframe.columns[:-1]]
        self.generated_labels = generated_dataframe["y"].to_numpy()

        # biased data labels
        self.biased_data = biased_dataframe[biased_dataframe.columns[:-1]]
        self.biased_labels = biased_dataframe["y"].to_numpy()

        # shuffle data
        self.generated_data = shuffle(self.generated_data, random_state=33)
        self.generated_labels = shuffle(self.generated_labels, random_state=33)
        self.biased_data = shuffle(self.biased_data, random_state=33)
        self.biased_labels = shuffle(self.biased_labels, random_state=33)

    def get_data(self):

        # -----------------------------------------------
        # Check Data Generated
        # -----------------------------------------------
        if self.checker.data_is_not_generated(self.generated_data):
            self.logger.error("Data is not generated. First call `generate_data` function!")
            exit()

        original_set = {"data": self.generated_data, "labels": self.generated_labels}
        biased_set = {"data": self.biased_data, "labels": self.biased_labels}

        return self.settings, original_set, biased_set

    def save_data(self, directory, file_index=None):

        # -----------------------------------------------
        # Check Data Generated
        # -----------------------------------------------

        if self.checker.data_is_not_generated(self.generated_data):
            self.logger.error("Data is not generated. First call `generate_data` function!")
            exit()

        # -----------------------------------------------
        # Check Directory Exists
        # -----------------------------------------------
        if not os.path.exists(directory):
            self.logger.warning("Directory {} does not exist. Creating directory!".format(directory))
            os.mkdir(directory)
        train_data_dir = os.path.join(directory, "train", "data")
        train_labels_dir = os.path.join(directory, "train", "labels")
        test_data_dir = os.path.join(directory, "test", "data")
        test_labels_dir = os.path.join(directory, "test", "labels")
        settings_dir = os.path.join(directory, "settings")
        if not os.path.exists(train_data_dir):
            os.makedirs(train_data_dir)
        if not os.path.exists(train_labels_dir):
            os.makedirs(train_labels_dir)
        if not os.path.exists(test_data_dir):
            os.makedirs(test_data_dir)
        if not os.path.exists(test_labels_dir):
            os.makedirs(test_labels_dir)
        if not os.path.exists(settings_dir):
            os.makedirs(settings_dir)

        if file_index is None:
            train_data_name = "train.csv"
            train_labels_name = "train.labels"
            test_data_name = "test.csv"
            test_labels_name = "test.labels"
            settings_file_name = "settings.json"
        else:
            train_data_name = "train_"+str(file_index)+".csv"
            train_labels_name = "train_"+str(file_index)+".labels"
            test_data_name = "test_"+str(file_index)+".csv"
            test_labels_name = "test_"+str(file_index)+".labels"
            settings_file_name = "settings_"+str(file_index)+".json"

        train_data_file = os.path.join(train_data_dir, train_data_name)
        train_labels_file = os.path.join(train_labels_dir, train_labels_name)
        test_data_file = os.path.join(test_data_dir, test_data_name)
        test_labels_file = os.path.join(test_labels_dir, test_labels_name)
        settings_file = os.path.join(settings_dir, settings_file_name)

        self.generated_data.to_csv(train_data_file, index=False)
        self.biased_data.to_csv(test_data_file, index=False)

        with open(train_labels_file, 'w') as filehandle1:
            for ind, lbl in enumerate(self.generated_labels):
                str_label = str(int(lbl))
                if ind < len(self.generated_labels)-1:
                    filehandle1.write(str_label + "\n")
                else:
                    filehandle1.write(str_label)
        filehandle1.close()

        with open(test_labels_file, 'w') as filehandle2:
            for ind, lbl in enumerate(self.biased_labels):
                str_label = str(int(lbl))
                if ind < len(self.biased_labels)-1:
                    filehandle2.write(str_label + "\n")
                else:
                    filehandle2.write(str_label)
        filehandle2.close()

        with open(settings_file, 'w') as fp:
            json.dump(self.settings, fp)

        self.logger.success("Train and Test data saved!")
