import os
import logging
from typing import Dict, Any, Optional
from supabase import create_client, Client

# Configure logging for the "Pulse"
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("MemoryAgent")

class MemoryAgent:
    """
    THE COURIER:
    Singular Responsibility: Move pre-packaged logic from the Rewriter 
    into the specific Supabase table defined by the 'path'.
    """

    def __init__(self):
        # 1. Access the "Keys to the Vault" from Environment Variables
        self.url: Optional[str] = os.getenv("SUPABASE_URL")
        self.key: Optional[str] = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        self.db: Optional[Client] = None

        if not self.url or not self.key:
            logger.error("Memory Error: Environment variables missing. Courier is offline.")
        else:
            try:
                # 2. Establish the connection bridge
                self.db = create_client(self.url, self.key)
                logger.info("Memory Connection: Armed and ready.")
            except Exception as e:
                logger.error(f"Memory Connection: Failed to initialize: {e}")

    async def store(self, package: Dict[str, Any]) -> int:
        """
        The Direct Deposit:
        - The Rewriter specifies the table via 'path'.
        - Calculated word count is returned for the UI Pulse.
        - 0% content modification (Preserves the Iceberg).
        """
        if not self.db:
            logger.error("Memory: Database client not initialized.")
            return 0

        # 3. Routing Logic: The 'path' IS the table name
        target_table = package.get('path')
        content = package.get('content', '')

        if not target_table:
            logger.warning("Memory Rejection: No destination path specified by Rewriter.")
            return 0

        # 4. Calculate the Pulse (Word Count for UI feedback)
        word_count = len(content.split())

        try:
            # 5. The Direct Move to Supabase
            # Content lands exactly as the Rewriter labeled it.
            self.db.table(target_table).insert(package).execute()
            
            logger.info(f"Memory Success: Moved {word_count} words into '{target_table}'")
            
            # Return word count to trigger the UI update
            return word_count

        except Exception as e:
            logger.error(f"Memory Failure: Could not move info to {target_table}. Error: {e}")
            return 0
