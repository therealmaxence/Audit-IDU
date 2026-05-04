from features import FeatureTracability, FeatureConformite

if __name__ == "__main__":
    features = [
        FeatureTracability(),
        FeatureConformite()
    ]
    for feature in features:
        print(feature.compute())