from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler


def make_model():
    """A fresh, untrained scaler + logistic regression pipeline."""
    return Pipeline([
        ("scale", StandardScaler()),
        ("clf", LogisticRegression()),
    ])