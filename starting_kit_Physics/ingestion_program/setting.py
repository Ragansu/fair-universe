# ------------------------------------------------------
# Class Setting
# created dict from params for data generation
# ------------------------------------------------------

class Setting:

    def __init__(self, case, params):
        self.case = case
        self.params = params

    def get_setting(self):
        return {
            "case": self.case,
            "problem_dimension": 2,
            "total_number_of_events": self.params.get_N(),
            "p_b": self.params.get_p_b(),
            "theta": 0,
            "L": 2,
            "generator": "normal",
            "background_distribution": {
                "name": "Gaussian",
                "mu": [0, 0],
                "sigma": [1, 1]
            },
            "signal_from_background": True,
            "signal_sigma_scale": 0.3,
            "systematics": [
                {
                    "name": "Translation",
                    "z_magnitude": self.params.get_z(),
                    "alpha": 90
                },
            ],
            "train_comment": "",
            "test_comment": "",
        }
