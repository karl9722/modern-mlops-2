"""Check the actual point-in-time training retrieval."""

from mlops.features import get_training_frame

if __name__ == "__main__":
    frame = get_training_frame()
    assert not frame.empty
    print(f"Retrieved {len(frame)} point-in-time training rows")
