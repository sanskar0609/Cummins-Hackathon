from neo4j import GraphDatabase
from app.core.config import settings
from app.core.logging import log

class Neo4jSessionManager:
    """Singleton Graph Driver for Neo4j Operations."""
    def __init__(self):
        self.uri = settings.NEO4J_URI
        self.user = settings.NEO4J_USER
        self.password = settings.NEO4J_PASSWORD
        self.driver = None
        
    def connect(self):
        if not self.driver:
            log.info("connecting_to_neo4j", uri=self.uri)
            try:
                self.driver = GraphDatabase.driver(
                    self.uri, 
                    auth=(self.user, self.password),
                    max_connection_lifetime=3600,
                    max_connection_pool_size=50
                )
                self.driver.verify_connectivity()
            except Exception as e:
                log.error("neo4j_connection_failed", error=str(e))
                # For local isolated runtime, we don't block the API startup entirely 
                # but flag it explicitly in logs.

    def close(self):
        if self.driver:
            self.driver.close()

    def get_session(self):
        if not self.driver:
            self.connect()
        # Returns a new session. Caller MUST close it.
        if self.driver:
            return self.driver.session()
        return None

# Global graph driver
neo4j_db = Neo4jSessionManager()
neo4j_db.connect()
