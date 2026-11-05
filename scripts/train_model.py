"""Compatibility entry point: train a gated candidate, never auto-promote."""

from mlops.train import train_candidate

if __name__ == "__main__":
    result = train_candidate()
    print(f"Version {result.model_version}; gate passed: {result.decision.passed}")
