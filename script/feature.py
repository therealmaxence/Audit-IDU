from features import (
    FeatureConformite,
    FeatureCountModuleOccurence,
    FeaturePersonUnicityADE,
    FeatureTracability,
)

if __name__ == "__main__":
    features = [
        FeatureCountModuleOccurence(),
        FeaturePersonUnicityADE(),
        FeatureTracability(),
        FeatureConformite(),
    ]
    for feature in features:
        feature.compute()