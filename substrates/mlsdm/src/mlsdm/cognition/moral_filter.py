class MoralFilter:
    def __init__(
        self,
        threshold: float = 0.5,
        adapt_rate: float = 0.05,
        min_threshold: float = 0.3,
        max_threshold: float = 0.9,
    ) -> None:
        if not (0.0 <= threshold <= 1.0 and 0.0 <= adapt_rate <= 1.0):
            raise ValueError("Threshold and adapt_rate must be between 0.0 and 1.0.")
        self.threshold = float(threshold)
        self.adapt_rate = float(adapt_rate)
        self.min_threshold = float(min_threshold)
        self.max_threshold = float(max_threshold)

    def evaluate(self, moral_value: float) -> bool:
        if not (0.0 <= moral_value <= 1.0):
            raise ValueError("Moral value must be between 0.0 and 1.0.")
        return moral_value >= self.threshold

    def adapt(self, accept_rate: float) -> None:
        if not (0.0 <= accept_rate <= 1.0):
            raise ValueError("Accept rate must be between 0.0 and 1.0.")
        if accept_rate < 0.5:
            self.threshold = max(self.min_threshold, self.threshold - self.adapt_rate)
        else:
            self.threshold = min(self.max_threshold, self.threshold + self.adapt_rate)

    def to_dict(self) -> dict[str, float]:
        return {
            "threshold": self.threshold,
            "adapt_rate": self.adapt_rate,
            "min_threshold": self.min_threshold,
            "max_threshold": self.max_threshold,
        }
