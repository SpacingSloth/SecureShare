import os

class Settings:
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    MINIO_ENDPOINT: str = "minio:9000"
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = "minioadmin"
    MINIO_BUCKET: str = "secureshare"
    MAX_FILE_SIZE: int = 1024 * 1024 * 1024  # 1024MB
    ALLOWED_EXTENSIONS: set = {
            # Документы
            ".pdf", ".doc", ".docx", ".odt", ".rtf", ".txt", ".md",
            ".xls", ".xlsx", ".ods", ".csv",
            ".ppt", ".pptx", ".odp",
            
            # Изображения
            ".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".svg", ".webp", ".heic",
            ".psd", ".ai", ".eps", ".indd",
            
            # Архивы
            ".zip", ".rar", ".7z", ".tar", ".gz", ".bz2",
            
            # Аудио
            ".mp3", ".wav", ".flac", ".aac", ".ogg", ".wma", ".m4a",
            
            # Видео
            ".mp4", ".mov", ".avi", ".mkv", ".flv", ".wmv", ".mpeg", ".webm",
            
            # Код
            ".py", ".js", ".html", ".css", ".php", ".java", ".c", ".cpp", ".h", 
            ".cs", ".go", ".rb", ".swift", ".kt", ".ts", ".sh", ".bat", ".ps1",
            
            # Данные
            ".json", ".xml", ".yaml", ".yml", ".sql", ".db", ".sqlite", ".sqlite3",
            
            # Прочее
            ".exe", ".msi", ".dmg", ".apk", ".iso", ".torrent"
    }

settings = Settings()