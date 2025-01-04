from app import create_app

import toml

# Load config
config = toml.load("config.toml")

app = create_app()

if __name__ == "__main__":
    app.run(
        debug=config["flask"]["DEBUG"],
        host=config["flask"]["HOST"],
        port=config["flask"]["PORT"]
    )