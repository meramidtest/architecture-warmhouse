"""
Configuration settings for IoT Gateway API
"""
import os

class Config:
    """Base configuration class"""
    
    # Database configuration
    @staticmethod
    def get_database_uri():
        """Get database URI based on environment variables"""
        database_url = os.getenv('DATABASE_URL')
        
        if database_url:
            # Handle both postgres:// and postgresql:// schemes
            if database_url.startswith('postgres://'):
                database_url = database_url.replace('postgres://', 'postgresql://', 1)
            return database_url
        else:
            # Default to SQLite
            basedir = os.path.abspath(os.path.dirname(__file__))
            return f'sqlite:///{os.path.join(basedir, "sensors.db")}'
    
    SQLALCHEMY_DATABASE_URI = get_database_uri()
    SQLALCHEMY_TRACK_MODIFICATIONS = False

class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True

class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False

class TestingConfig(Config):
    """Testing configuration"""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'

config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
} 