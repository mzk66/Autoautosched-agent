from agent.llm.factory import load_env_file
from web.app import main


if __name__ == "__main__":
    load_env_file()
    main()
