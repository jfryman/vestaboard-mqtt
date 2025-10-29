#!/usr/bin/env python3
"""Convert dict configs to MQTTConfig objects in test files."""

import re


def convert_mqtt_config_dicts(content):
    """Convert mqtt_config dict definitions to MQTTConfig constructor calls."""

    # Pattern to match mqtt_config = {...} with multiline support
    pattern = r"mqtt_config = \{([^}]+)\}"

    def replace_dict(match):
        dict_content = match.group(1)
        # Remove quotes from keys and convert to keyword arguments
        dict_content = re.sub(r'"(\w+)":', r"\1=", dict_content)
        return f"mqtt_config = MQTTConfig({dict_content})"

    content = re.sub(pattern, replace_dict, content, flags=re.DOTALL)

    return content


def main():
    files = ["test_mqtt_bridge.py", "test_mqtt_bridge_errors.py"]

    for filename in files:
        with open(filename, "r") as f:
            content = f.read()

        # Convert mqtt_config dicts
        content = convert_mqtt_config_dicts(content)

        with open(filename, "w") as f:
            f.write(content)

        print(f"Converted {filename}")


if __name__ == "__main__":
    main()
