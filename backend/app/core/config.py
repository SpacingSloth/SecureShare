import os


class Settings:
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    MINIO_ENDPOINT: str = "minio:9000"
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = "minioadmin"
    MINIO_BUCKET: str = "secureshare"
    MAX_FILE_SIZE: int = 1024 * 1024 * 1024  
    PUBLIC_BASE_URL: str = "https://stylus-consistency-arise-sub.trycloudflare.com"
    ALLOWED_EXTENSIONS: set = {
            ".pdf", ".doc", ".docx", ".odt", ".rtf", ".txt", ".md",
            ".xls", ".xlsx", ".ods", ".csv",
            ".ppt", ".pptx", ".odp",
            
            ".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".svg", ".webp", ".heic",
            ".psd", ".ai", ".eps", ".indd",
            
            ".zip", ".rar", ".7z", ".tar", ".gz", ".bz2",
            
            ".mp3", ".wav", ".flac", ".aac", ".ogg", ".wma", ".m4a",
            
            ".mp4", ".mov", ".avi", ".mkv", ".flv", ".wmv", ".mpeg", ".webm",
            
            ".py", ".js", ".html", ".css", ".php", ".java", ".c", ".cpp", ".h", 
            ".cs", ".go", ".rb", ".swift", ".kt", ".ts", ".sh", ".bat", ".ps1",
            
            ".json", ".xml", ".yaml", ".yml", ".sql", ".db", ".sqlite", ".sqlite3",
            
            ".exe", ".msi", ".dmg", ".apk", ".iso", ".torrent"
    }

settings = Settings()