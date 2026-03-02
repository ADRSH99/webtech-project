"""
Test Model Generator
Creates sample ML models for testing the deployment platform.
"""

import os
import joblib
import json
import numpy as np


def create_sklearn_classifier():
    """Create a sample sklearn classification model."""
    from sklearn.ensemble import RandomForestClassifier
    
    # Create sample data (4 features, binary classification)
    X = np.array([
        [5.1, 3.5, 1.4, 0.2],
        [4.9, 3.0, 1.4, 0.2],
        [6.2, 3.4, 5.4, 2.3],
        [5.9, 3.0, 5.1, 1.8],
        [4.7, 3.2, 1.3, 0.2],
        [6.0, 2.2, 5.0, 1.5],
    ])
    y = [0, 0, 1, 1, 0, 1]  # Binary labels
    
    # Train model
    model = RandomForestClassifier(n_estimators=10, random_state=42)
    model.fit(X, y)
    
    # Save model
    model_path = "test_classifier.pkl"
    joblib.dump(model, model_path)
    print(f"✓ Created sklearn classifier: {model_path}")
    
    # Create matching config
    config = {
        "framework": "sklearn",
        "task": "classification",
        "input": {
            "type": "numeric",
            "features": 4
        },
        "output": {
            "type": "label"
        }
    }
    
    config_path = "test_classifier_config.json"
    with open(config_path, 'w') as f:
        json.dump(config, f, indent=2)
    print(f"✓ Created config: {config_path}")
    
    return model_path, config_path


def create_sklearn_regressor():
    """Create a sample sklearn regression model."""
    from sklearn.linear_model import LinearRegression
    
    # Create sample data (3 features, continuous output)
    X = np.array([
        [1.0, 2.0, 3.0],
        [2.0, 3.0, 4.0],
        [3.0, 4.0, 5.0],
        [4.0, 5.0, 6.0],
        [5.0, 6.0, 7.0],
    ])
    y = [10.0, 15.0, 20.0, 25.0, 30.0]  # Continuous targets
    
    # Train model
    model = LinearRegression()
    model.fit(X, y)
    
    # Save model
    model_path = "test_regressor.pkl"
    joblib.dump(model, model_path)
    print(f"✓ Created sklearn regressor: {model_path}")
    
    # Create matching config
    config = {
        "framework": "sklearn",
        "task": "regression",
        "input": {
            "type": "numeric",
            "features": 3
        },
        "output": {
            "type": "number"
        }
    }
    
    config_path = "test_regressor_config.json"
    with open(config_path, 'w') as f:
        json.dump(config, f, indent=2)
    print(f"✓ Created config: {config_path}")
    
    return model_path, config_path


def test_prediction(model_path, sample_input):
    """Test that a saved model can be loaded and used for prediction."""
    model = joblib.load(model_path)
    prediction = model.predict([sample_input])
    print(f"  Sample prediction for {sample_input}: {prediction[0]}")
    return prediction[0]


if __name__ == "__main__":
    print("=" * 60)
    print("ML Model Deployment Platform - Test Model Generator")
    print("=" * 60)
    print()
    
    # Create classifier
    print("Creating Classification Model...")
    clf_model, clf_config = create_sklearn_classifier()
    test_prediction(clf_model, [5.0, 3.4, 1.5, 0.2])
    print()
    
    # Create regressor
    print("Creating Regression Model...")
    reg_model, reg_config = create_sklearn_regressor()
    test_prediction(reg_model, [2.5, 3.5, 4.5])
    print()
    
    print("=" * 60)
    print("Test models created successfully!")
    print()
    print("To deploy the classifier, run:")
    print(f'curl -X POST http://localhost:8000/deploy-model \\')
    print(f'  -F "model_file=@{clf_model}" \\')
    print(f'  -F "config_file=@{clf_config}"')
    print()
    print("To deploy the regressor, run:")
    print(f'curl -X POST http://localhost:8000/deploy-model \\')
    print(f'  -F "model_file=@{reg_model}" \\')
    print(f'  -F "config_file=@{reg_config}"')
    print()
    print("=" * 60)
