from ml_utils import DATA_PATH, ModelLoadError, train_model


def main() -> None:
    print("--- Training Energy Spike Prediction Model ---")
    try:
        artifacts, metrics = train_model()
    except ModelLoadError as err:
        print(f"[ERROR] {err}")
        return

    print("\nModel training complete. Artifacts saved to:")
    print(f"  - Model path: {DATA_PATH.parent / 'energy_spike_model.pkl'}")

    print("\n--- Evaluation Summary ---")
    print(f"Accuracy: {metrics['accuracy']:.4f}")
    print("\nClassification report:")
    print(metrics["classification_report"])


if __name__ == "__main__":
    main()