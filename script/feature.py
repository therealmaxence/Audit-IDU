from features import FeatureTracability

if __name__ == "__main__":
    features = [
        FeatureTracability()
    ]
    for feature in features:
        print(feature.compute())