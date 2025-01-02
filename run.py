from app import app

import toml

# Load config
config = toml.load("config.toml")

if __name__ == "__main__":
    app.run(
        debug=config["flask"]["DEBUG"],
        host=config["flask"]["HOST"],
        port=config["flask"]["PORT"]
    )