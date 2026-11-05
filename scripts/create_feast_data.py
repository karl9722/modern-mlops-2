"""Build the validated Ames feature source, without synthetic replacement data."""

from mlops.features import apply_definitions, build_feature_source

if __name__ == "__main__":
    print(f"Feature rows: {build_feature_source()}")
    apply_definitions()
