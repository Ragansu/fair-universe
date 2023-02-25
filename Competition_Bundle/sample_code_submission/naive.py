import pickle
from os.path import isfile
from sklearn.naive_bayes import GaussianNB


#------------------------------
# Naive Bayes Baseline Model
#------------------------------
class Model:
    def __init__(self):
        self.model_name = "Normal"
        self.clf = GaussianNB()
        self.is_trained=False

    def fit(self, X, y):
        self.clf.fit(X, y)
        self.is_trained=True

    def predict(self, X):
        return self.clf.predict(X)

    def save(self, path="./"):
        pickle.dump(self.clf, open(path + '_model.pickle', "wb"))

    
    def load(self, path="./"):
        modelfile = path + '_model.pickle'
        if isfile(modelfile):
            with open(modelfile, 'rb') as f:
                self = pickle.load(f)
            print("Model reloaded from: " + modelfile)
        return self
