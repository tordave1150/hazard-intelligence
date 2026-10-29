"""Explicit budgets for the chunked national retrospective three-day product."""
PRODUCT = 'flood_3days_thailand'
WINDOW = '3days'
ENDPOINT = 'https://api-gateway.gistda.or.th/api/2.0/resources/features/flood/3days'
COLLECTION = 'satellite_flood_3days_latest'
PAGE_SIZE = 100
MAX_FEATURES = 20_000
MAX_PAGES = 200
MAX_SOURCE_BYTES = 64 * 1024 * 1024
MAX_FEED_BYTES = 32 * 1024 * 1024
MAX_POSITIONS = 2_000_000
MAX_SECONDS = 600
CHUNK_FEATURES = 100
CHUNK_BYTES = 1024 * 1024
MAX_CHUNKS = 512
