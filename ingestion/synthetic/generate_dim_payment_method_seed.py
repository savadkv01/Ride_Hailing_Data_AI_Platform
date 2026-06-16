import json


def generate() -> dict:
    return {
        "method_code": "card",
        "method_type": "credit_card",
        "provider": "visa",
        "source_system": "synthetic_generator",
    }


if __name__ == "__main__":
    print(json.dumps(generate()))
