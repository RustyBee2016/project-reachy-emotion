"""
Test suite for database migrations and stored procedures.
Run with: pytest tests/test_database_migrations.py -v
"""

import pytest
import psycopg2
from psycopg2.extras import RealDictCursor
import os
from datetime import datetime
from decimal import Decimal
import uuid


class TestDatabaseSchema:
    """Test database schema creation."""
    
    @pytest.fixture
    def db_connection(self):
        """Create test database connection."""
        # Use test database
        conn = psycopg2.connect(
            host=os.getenv('DB_HOST', 'localhost'),
            port=os.getenv('DB_PORT', '5432'),
            database=os.getenv('TEST_DB_NAME', 'reachy_test'),
            user=os.getenv('DB_USER', 'reachy'),
            password=os.getenv('DB_PASSWORD', 'testpass')
        )
        yield conn
        conn.rollback()
        conn.close()
    
    def test_video_table_exists(self, db_connection):
        """Test that video table exists with correct schema."""
        cur = db_connection.cursor()
        cur.execute("""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_name = 'video'
            ORDER BY ordinal_position
        """)
        
        columns = cur.fetchall()
        column_dict = {col[0]: (col[1], col[2]) for col in columns}
        
        # Verify essential columns
        assert 'video_id' in column_dict
        assert column_dict['video_id'][0] == 'uuid'
        assert column_dict['video_id'][1] == 'NO'
        
        assert 'file_path' in column_dict
        assert 'split' in column_dict
        assert 'label' in column_dict
        assert 'sha256' in column_dict
        assert 'created_at' in column_dict
    
    def test_training_run_table_exists(self, db_connection):
        """Test training_run table structure."""
        cur = db_connection.cursor()
        cur.execute("""
            SELECT column_name FROM information_schema.columns
            WHERE table_name = 'training_run'
        """)
        
        columns = {col[0] for col in cur.fetchall()}
        required_columns = {
            'run_id', 'status', 'strategy', 'train_fraction',
            'test_fraction', 'seed', 'dataset_hash', 'mlflow_run_id'
        }
        
        assert required_columns.issubset(columns)
    
    def test_training_selection_table_exists(self, db_connection):
        """Test training_selection junction table."""
        cur = db_connection.cursor()
        
        # Check table exists
        cur.execute("""
            SELECT EXISTS (
                SELECT 1 FROM information_schema.tables
                WHERE table_name = 'training_selection'
            )
        """)
        assert cur.fetchone()[0] is True
        
        # Check unique constraint
        cur.execute("""
            SELECT constraint_name FROM information_schema.table_constraints
            WHERE table_name = 'training_selection' AND constraint_type = 'UNIQUE'
        """)
        constraints = cur.fetchall()
        assert len(constraints) > 0
    
    def test_promotion_log_table_exists(self, db_connection):
        """Test promotion_log audit table."""
        cur = db_connection.cursor()
        cur.execute("""
            SELECT column_name FROM information_schema.columns
            WHERE table_name = 'promotion_log'
        """)
        
        columns = {col[0] for col in cur.fetchall()}
        required_columns = {
            'id', 'video_id', 'from_split', 'to_split', 'label',
            'idempotency_key', 'success', 'promoted_at'
        }
        
        assert required_columns.issubset(columns)


class TestStoredProcedures:
    """Test stored procedures and functions."""
    
    @pytest.fixture
    def db_connection(self):
        """Create test database connection with sample data."""
        conn = psycopg2.connect(
            host=os.getenv('DB_HOST', 'localhost'),
            database=os.getenv('TEST_DB_NAME', 'reachy_test'),
            user=os.getenv('DB_USER', 'reachy'),
            password=os.getenv('DB_PASSWORD', 'testpass')
        )
        
        # Insert test data
        cur = conn.cursor()
        try:
            # Clear existing test data
            cur.execute("DELETE FROM video WHERE file_path LIKE 'test_%'")
            
            # Insert balanced test videos
            for emotion in ['happy', 'sad', 'neutral']:
                for i in range(10):
                    cur.execute("""
                        INSERT INTO video (video_id, file_path, split, label, sha256, duration_sec)
                        VALUES (%s, %s, %s, %s, %s, %s)
                    """, (
                        uuid.uuid4(),
                        f'test_{emotion}_{i}.mp4',
                        'dataset_all',
                        emotion,
                        f'hash_{emotion}_{i}',
                        5.0
                    ))
            
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        
        yield conn
        
        # Cleanup
        cur.execute("DELETE FROM video WHERE file_path LIKE 'test_%'")
        conn.commit()
        conn.close()
    
    def test_get_class_distribution(self, db_connection):
        """Test class distribution function."""
        cur = db_connection.cursor(cursor_factory=RealDictCursor)
        
        cur.execute("SELECT * FROM get_class_distribution('dataset_all')")
        results = cur.fetchall()
        
        # Should have 3 emotion classes
        assert len(results) == 3
        
        # Each class should have 10 samples
        for row in results:
            assert row['count'] == 10
            assert row['percentage'] == Decimal('33.33') or row['percentage'] == Decimal('33.34')
    
    def test_check_dataset_balance(self, db_connection):
        """Test dataset balance checking function."""
        cur = db_connection.cursor(cursor_factory=RealDictCursor)
        
        cur.execute("SELECT * FROM check_dataset_balance(5, 1.5)")
        result = cur.fetchone()
        
        assert result['balanced'] is True
        assert result['total_samples'] == 30
        assert result['min_count'] == 10
        assert result['max_count'] == 10
        assert result['imbalance_ratio'] == Decimal('1.00')
        assert 'ready for training' in result['recommendation'].lower()
    
    def test_promote_video_safe(self, db_connection):
        """Test safe video promotion with idempotency."""
        cur = db_connection.cursor(cursor_factory=RealDictCursor)
        
        # Get a test video
        cur.execute("SELECT video_id FROM video WHERE split = 'dataset_all' LIMIT 1")
        video_id = cur.fetchone()['video_id']
        
        # First promotion - should succeed
        cur.execute("""
            SELECT * FROM promote_video_safe(%s, 'train', NULL, 'test_user', 'test_key_1', FALSE)
        """, (video_id,))
        result1 = cur.fetchone()
        
        assert result1['success'] is True
        assert result1['old_split'] == 'dataset_all'
        assert result1['new_split'] == 'train'
        
        # Second promotion with same idempotency key - should be idempotent
        cur.execute("""
            SELECT * FROM promote_video_safe(%s, 'train', NULL, 'test_user', 'test_key_1', FALSE)
        """, (video_id,))
        result2 = cur.fetchone()
        
        assert result2['success'] is True
        assert 'idempotent' in result2['message'].lower()
        
        db_connection.commit()
    
    def test_promote_video_dry_run(self, db_connection):
        """Test dry run promotion doesn't modify data."""
        cur = db_connection.cursor(cursor_factory=RealDictCursor)
        
        # Get a test video
        cur.execute("SELECT video_id, split FROM video WHERE split = 'dataset_all' LIMIT 1")
        video = cur.fetchone()
        video_id = video['video_id']
        original_split = video['split']
        
        # Dry run promotion
        cur.execute("""
            SELECT * FROM promote_video_safe(%s, 'test', NULL, 'test_user', NULL, TRUE)
        """, (video_id,))
        result = cur.fetchone()
        
        assert result['success'] is True
        assert 'dry run' in result['message'].lower()
        
        # Verify video wasn't actually moved
        cur.execute("SELECT split FROM video WHERE video_id = %s", (video_id,))
        current_split = cur.fetchone()['split']
        assert current_split == original_split
    
    def test_create_training_run_with_sampling(self, db_connection):
        """Test training run creation with automatic sampling."""
        cur = db_connection.cursor(cursor_factory=RealDictCursor)
        
        # Create training run
        cur.execute("""
            SELECT create_training_run_with_sampling('balanced_random', 0.7, 12345)
        """)
        run_id = cur.fetchone()['create_training_run_with_sampling']
        
        # Verify run was created
        cur.execute("SELECT * FROM training_run WHERE run_id = %s", (run_id,))
        run = cur.fetchone()
        
        assert run['status'] == 'pending'
        assert run['strategy'] == 'balanced_random'
        assert run['train_fraction'] == Decimal('0.70')
        assert run['seed'] == 12345
        
        # Verify samples were selected
        cur.execute("""
            SELECT target_split, COUNT(*) as count
            FROM training_selection
            WHERE run_id = %s
            GROUP BY target_split
        """, (run_id,))
        
        splits = {row['target_split']: row['count'] for row in cur.fetchall()}
        
        # Should have roughly 70% train, 30% test (±1 for rounding)
        total = splits.get('train', 0) + splits.get('test', 0)
        assert total == 30  # All test videos
        assert 19 <= splits.get('train', 0) <= 23  # ~70% of 30
        assert 7 <= splits.get('test', 0) <= 11    # ~30% of 30
        
        db_connection.commit()


class TestTriggers:
    """Test database triggers."""
    
    @pytest.fixture
    def db_connection(self):
        conn = psycopg2.connect(
            host=os.getenv('DB_HOST', 'localhost'),
            database=os.getenv('TEST_DB_NAME', 'reachy_test'),
            user=os.getenv('DB_USER', 'reachy'),
            password=os.getenv('DB_PASSWORD', 'testpass')
        )
        yield conn
        conn.rollback()
        conn.close()
    
    def test_updated_at_trigger(self, db_connection):
        """Test that updated_at is automatically updated."""
        cur = db_connection.cursor(cursor_factory=RealDictCursor)
        
        # Insert a video
        video_id = uuid.uuid4()
        cur.execute("""
            INSERT INTO video (video_id, file_path, split)
            VALUES (%s, 'test_trigger.mp4', 'temp')
            RETURNING created_at, updated_at
        """, (video_id,))
        
        initial = cur.fetchone()
        assert initial['created_at'] == initial['updated_at']
        
        # Wait a moment
        import time
        time.sleep(0.1)
        
        # Update the video
        cur.execute("""
            UPDATE video SET label = 'happy'
            WHERE video_id = %s
            RETURNING updated_at
        """, (video_id,))
        
        updated = cur.fetchone()
        assert updated['updated_at'] > initial['updated_at']
        
        db_connection.commit()


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--color=yes'])
