# test_python_utils.py - Utility functions for data processing

def clean_text(text: str) -> str:
    """Remove extra whitespace and normalize text."""
    return ' '.join(text.strip().split())

def calculate_average(numbers: list[float]) -> float:
    """Calculate the average of a list of numbers."""
    if not numbers:
        return 0.0
    return sum(numbers) / len(numbers)

class DataProcessor:
    def __init__(self, data: list):
        self.data = data

    def filter_positive(self) -> list[float]:
        """Return only positive values."""
        return [x for x in self.data if x > 0]

if __name__ == "__main__":
    print(clean_text("  hello   world  "))
    print(calculate_average([1, 2, 3, 4, 5]))