from core.db import Database
from core.router import ProviderRouter
from learning.learning_nightly_job import run_nightly_learning

PERSONA_ID = "dale"   # or whatever persona id you use

def main():
    db = Database()
    router = ProviderRouter(db)
    run_nightly_learning(db, router, PERSONA_ID)

if __name__ == "__main__":
    main()
