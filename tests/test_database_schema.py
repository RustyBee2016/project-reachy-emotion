"""
Test database schema and stored procedures.
Tests the Phase 1 database foundation including tables, constraints, and business logic.
"""
import pytest
import psycopg2
from psycopg2.extras import RealDictCursor
import os
from uuid import uuid4
from datetime import datetime


@pytest.fixture
def db_conn():
    """Create database connection for testing."""
    conn = psycopg2.connect(
        host=os.getenv('DB_HOST', 'localhost'),
        port=os.getenv('DB_PORT', '5432'),
        database=os.getenv('DB_NAME', 'reachy_emotion_test'),
        user=os.getenv('DB_USER', 'postgres'),
        password=os.getenv('DB_PASSWORD', 'postgres')
    )
    yield conn
    conn.rollback()
    conn.close()


@pytest.fixture
def db_cursor(db_conn):
    """Create cursor with dict results."""
    cursor = db_conn.cursor(cursor_factory=RealDictCursor)
    yield cursor
    cursor.close()


class TestVideoTable:
    """Test video table schema and constraints."""
    
    def test_video_insert_basic(self, db_cursor, db_conn):
        """Test basic video insertion."""
        video_id = uuid4()
        db_cursor.execute("""
            INSERT INTO video (video_id, file_path, split, label, sha256)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING video_id, split, label
        """, (video_id, 'videos/train/test.mp4', 'train', 'happy', 'a' * 64))
        
        result = db_cursor.fetchone()
        assert result['video_id'] == video_id
        assert result['split'] == 'train'
        assert result['label'] == 'happy'
        db_conn.commit()
    
    def test_video_sha256_unique_constraint(self, db_cursor, db_conn):
        """Test SHA256 uniqueness constraint."""
        sha = 'b' * 64
        
        # First insert should succeed
        db_cursor.execute("""
            INSERT INTO video (file_path, split, sha256)
            VALUES (%s, %s, %s)
        """, ('videos/temp/test1.mp4', 'temp', sha))
        db_conn.commit()
        
        # Second insert with same SHA should fail
        with pytest.raises(psycopg2.IntegrityError):
            db_cursor.execute("""
                INSERT INTO video (file_path, split, sha256)
                VALUES (%s, %s, %s)
            """, ('videos/temp/test2.mp4', 'temp', sha))
            db_conn.commit()
    
    def test_video_updated_at_trigger(self, db_cursor, db_conn):
        """Test automatic updated_at timestamp."""
        video_id = uuid4()
        
        # Insert video
        db_cursor.execute("""
            INSERT INTO video (video_id, file_path, split)
            VALUES (%s, %s, %s)
            RETURNING created_at, updated_at
        """, (video_id, 'videos/temp/test.mp4', 'temp'))
        
        initial = db_cursor.fetchone()
        db_conn.commit()
        
        # Update video
        import time
        time.sleep(0.1)  # Ensure time difference
        
        db_cursor.execute("""
            UPDATE video SET label = %s WHERE video_id = %s
            RETURNING updated_at
        """, ('happy', video_id))
        
        updated = db_cursor.fetchone()
        db_conn.commit()
        
        assert updated['updated_at'] > initial['updated_at']


class TestTrainingRun:
    """Test training_run table and constraints."""
    
    def test_training_run_creation(self, db_cursor, db_conn):
        """Test training run creation with valid fractions."""
        run_id = uuid4()
        db_cursor.execute("""
            INSERT INTO training_run (
                run_id, strategy, train_fraction, test_fraction, seed
            ) VALUES (%s, %s, %s, %s, %s)
            RETURNING run_id, status
        """, (run_id, 'balanced_random', 0.7, 0.3, 12345))
        
        result = db_cursor.fetchone()
        assert result['run_id'] == run_id
        assert result['status'] == 'pending'
        db_conn.commit()
    
    def test_training_run_invalid_fractions(self, db_cursor, db_conn):
        """Test fraction validation constraint."""
        # Sum > 1.0 should fail
        with pytest.raises(psycopg2.IntegrityError):
            db_cursor.execute("""
                INSERT INTO training_run (strategy, train_fraction, test_fraction)
                VALUES (%s, %s, %s)
            """, ('balanced_random', 0.7, 0.5))
            db_conn.commit()


class TestStoredProcedures:
    """Test stored procedures for business logic."""
    
    def test_get_class_distribution(self, db_cursor, db_conn):
        """Test class distribution calculation."""
        # Insert test videos (3-class: happy, sad, neutral)
        labels = ['happy', 'happy', 'happy', 'sad', 'sad', 'sad', 'neutral', 'neutral', 'neutral']
        for i, label in enumerate(labels):
            db_cursor.execute("""
                INSERT INTO video (file_path, split, label, size_bytes, duration_sec)
                VALUES (%s, %s, %s, %s, %s)
            """, (f'videos/train/test{i}.mp4', 'train', label, 1000000, 5.0))
        db_conn.commit()
        
        # Call function
        db_cursor.execute("SELECT * FROM get_class_distribution('train')")
        results = db_cursor.fetchall()
        
        assert len(results) == 3
        happy_row = [r for r in results if r['label'] == 'happy'][0]
        sad_row = [r for r in results if r['label'] == 'sad'][0]
        neutral_row = [r for r in results if r['label'] == 'neutral'][0]
        
        assert happy_row['count'] == 3
        assert sad_row['count'] == 3
        assert neutral_row['count'] == 3
    
    def test_check_dataset_balance_empty(self, db_cursor):
        """Test balance check with empty dataset."""
        db_cursor.execute("SELECT * FROM check_dataset_balance(100, 1.5)")
        result = db_cursor.fetchone()
        
        assert result['balanced'] is False
        assert result['total_samples'] == 0
        assert 'empty' in result['recommendation'].lower()
    
    def test_check_dataset_balance_insufficient(self, db_cursor, db_conn):
        """Test balance check with insufficient samples."""
        # Insert 60 samples (below minimum of 100) - 3-class balanced
        labels = ['happy'] * 20 + ['sad'] * 20 + ['neutral'] * 20
        for i, label in enumerate(labels):
            db_cursor.execute("""
                INSERT INTO video (file_path, split, label)
                VALUES (%s, %s, %s)
            """, (f'videos/train/test{i}.mp4', 'train', label))
        db_conn.commit()
        
        db_cursor.execute("SELECT * FROM check_dataset_balance(100, 1.5)")
        result = db_cursor.fetchone()
        
        assert result['balanced'] is False
        assert result['total_samples'] == 50
        assert 'more samples' in result['recommendation'].lower()
    
    def test_check_dataset_balance_imbalanced(self, db_cursor, db_conn):
        """Test balance check with class imbalance."""
        # Insert 150 happy, 30 sad, 20 neutral (ratio = 7.5, exceeds max of 1.5)
        labels = ['happy'] * 150 + ['sad'] * 30 + ['neutral'] * 20
        for i, label in enumerate(labels):
            db_cursor.execute("""
                INSERT INTO video (file_path, split, label)
                VALUES (%s, %s, %s)
            """, (f'videos/train/test{i}.mp4', 'train', label))
        db_conn.commit()
        
        db_cursor.execute("SELECT * FROM check_dataset_balance(100, 1.5)")
        result = db_cursor.fetchone()
        
        assert result['balanced'] is False
        assert result['imbalance_ratio'] == 3.0
        assert 'imbalance' in result['recommendation'].lower()
    
    def test_check_dataset_balance_good(self, db_cursor, db_conn):
        """Test balance check with balanced dataset."""
        # Insert 80 happy, 75 sad, 75 neutral (ratio = 1.07, within 1.5)
        labels = ['happy'] * 80 + ['sad'] * 75 + ['neutral'] * 75
        for i, label in enumerate(labels):
            db_cursor.execute("""
                INSERT INTO video (file_path, split, label)
                VALUES (%s, %s, %s)
            """, (f'videos/train/test{i}.mp4', 'train', label))
        db_conn.commit()
        
        db_cursor.execute("SELECT * FROM check_dataset_balance(100, 1.5)")
        result = db_cursor.fetchone()
        
        assert result['balanced'] is True
        assert result['total_samples'] == 230
        assert 'ready' in result['recommendation'].lower()
    
    def test_promote_video_safe_basic(self, db_cursor, db_conn):
        """Test basic video promotion."""
        video_id = uuid4()
        
        # Insert video in temp
        db_cursor.execute("""
            INSERT INTO video (video_id, file_path, split)
            VALUES (%s, %s, %s)
        """, (video_id, 'videos/temp/test.mp4', 'temp'))
        db_conn.commit()
        
        # Promote directly to train with label
        db_cursor.execute("""
            SELECT * FROM promote_video_safe(%s, %s, %s, %s)
        """, (video_id, 'train', 'happy', 'test_user'))
        
        result = db_cursor.fetchone()
        db_conn.commit()
        
        assert result['success'] is True
        assert result['old_split'] == 'temp'
        assert result['new_split'] == 'train'
        
        # Verify video was updated
        db_cursor.execute("SELECT split, label FROM video WHERE video_id = %s", (video_id,))
        video = db_cursor.fetchone()
        assert video['split'] == 'train'
        assert video['label'] == 'happy'
    
    def test_promote_video_safe_idempotency(self, db_cursor, db_conn):
        """Test idempotency key prevents duplicate promotions."""
        video_id = uuid4()
        idem_key = 'test-key-123'
        
        # Insert video
        db_cursor.execute("""
            INSERT INTO video (video_id, file_path, split)
            VALUES (%s, %s, %s)
        """, (video_id, 'videos/temp/test.mp4', 'temp'))
        db_conn.commit()
        
        # First promotion
        db_cursor.execute("""
            SELECT * FROM promote_video_safe(%s, %s, %s, %s, %s)
        """, (video_id, 'train', 'happy', 'test_user', idem_key))
        result1 = db_cursor.fetchone()
        db_conn.commit()
        
        assert result1['success'] is True
        
        # Second promotion with same key should be idempotent
        db_cursor.execute("""
            SELECT * FROM promote_video_safe(%s, %s, %s, %s, %s)
        """, (video_id, 'train', 'happy', 'test_user', idem_key))
        result2 = db_cursor.fetchone()
        db_conn.commit()
        
        assert result2['success'] is True
        assert 'idempotent' in result2['message'].lower()
    
    def test_promote_video_safe_label_required(self, db_cursor, db_conn):
        """Test label requirement for train."""
        video_id = uuid4()
        
        db_cursor.execute("""
            INSERT INTO video (video_id, file_path, split)
            VALUES (%s, %s, %s)
        """, (video_id, 'videos/temp/test.mp4', 'temp'))
        db_conn.commit()
        
        # Promote without label should fail
        db_cursor.execute("""
            SELECT * FROM promote_video_safe(%s, %s, %s, %s)
        """, (video_id, 'train', None, 'test_user'))
        result = db_cursor.fetchone()
        db_conn.commit()
        
        assert result['success'] is False
        assert 'label required' in result['message'].lower()
    
    def test_promote_video_safe_dry_run(self, db_cursor, db_conn):
        """Test dry run mode."""
        video_id = uuid4()
        
        db_cursor.execute("""
            INSERT INTO video (video_id, file_path, split)
            VALUES (%s, %s, %s)
        """, (video_id, 'videos/temp/test.mp4', 'temp'))
        db_conn.commit()
        
        # Dry run promotion
        db_cursor.execute("""
            SELECT * FROM promote_video_safe(%s, %s, %s, %s, %s, %s)
        """, (video_id, 'train', 'happy', 'test_user', None, True))
        result = db_cursor.fetchone()
        db_conn.commit()
        
        assert result['success'] is True
        assert 'dry run' in result['message'].lower()
        
        # Verify video was NOT updated
        db_cursor.execute("SELECT split FROM video WHERE video_id = %s", (video_id,))
        video = db_cursor.fetchone()
        assert video['split'] == 'temp'
    
    def test_create_training_run_with_sampling(self, db_cursor, db_conn):
        """Test training run creation with automatic sampling."""
        # Insert balanced dataset (3-class: happy, sad, neutral)
        labels = ['happy'] * 70 + ['sad'] * 70 + ['neutral'] * 70
        for i, label in enumerate(labels):
            db_cursor.execute("""
                INSERT INTO video (file_path, split, label)
                VALUES (%s, %s, %s)
            """, (f'videos/train/test{i}.mp4', 'train', label))
        db_conn.commit()
        
        # Create training run
        db_cursor.execute("""
            SELECT create_training_run_with_sampling('balanced_random', 0.7, 42)
        """)
        run_id = db_cursor.fetchone()['create_training_run_with_sampling']
        db_conn.commit()
        
        assert run_id is not None
        
        # Verify run was created
        db_cursor.execute("""
            SELECT * FROM training_run WHERE run_id = %s
        """, (run_id,))
        run = db_cursor.fetchone()
        
        assert run['status'] == 'pending'
        assert run['seed'] == 42
        assert run['dataset_hash'] is not None
        
        # Verify selections were created
        db_cursor.execute("""
            SELECT target_split, COUNT(*) as cnt
            FROM training_selection
            WHERE run_id = %s
            GROUP BY target_split
        """, (run_id,))
        selections = {row['target_split']: row['cnt'] for row in db_cursor.fetchall()}
        
        # Should have roughly 70/30 split (allow some variance due to randomness)
        # Total is 210 samples (70 each class)
        assert 130 <= selections['train'] <= 160
        assert 50 <= selections['test'] <= 80
        assert selections['train'] + selections['test'] == 210
    
    def test_get_training_run_details(self, db_cursor, db_conn):
        """Test training run details retrieval."""
        # Create run with sampling (3-class: happy, sad, neutral)
        labels = ['happy'] * 34 + ['sad'] * 33 + ['neutral'] * 33
        for i, label in enumerate(labels):
            db_cursor.execute("""
                INSERT INTO video (file_path, split, label)
                VALUES (%s, %s, %s)
            """, (f'videos/train/test{i}.mp4', 'train', label))
        db_conn.commit()
        
        db_cursor.execute("""
            SELECT create_training_run_with_sampling('balanced_random', 0.8, 99)
        """)
        run_id = db_cursor.fetchone()['create_training_run_with_sampling']
        db_conn.commit()
        
        # Get details
        db_cursor.execute("""
            SELECT * FROM get_training_run_details(%s)
        """, (run_id,))
        details = db_cursor.fetchone()
        
        assert details['run_id'] == run_id
        assert details['status'] == 'pending'
        assert details['strategy'] == 'balanced_random'
        assert details['train_count'] + details['test_count'] == 100
        assert details['dataset_hash'] is not None


class TestPromotionLog:
    """Test promotion logging and audit trail."""
    
    def test_promotion_log_entry(self, db_cursor, db_conn):
        """Test promotion log captures all details."""
        video_id = uuid4()
        idem_key = 'test-log-key'
        
        db_cursor.execute("""
            INSERT INTO video (video_id, file_path, split)
            VALUES (%s, %s, %s)
        """, (video_id, 'videos/temp/test.mp4', 'temp'))
        db_conn.commit()
        
        # Promote video
        db_cursor.execute("""
            SELECT * FROM promote_video_safe(%s, %s, %s, %s, %s)
        """, (video_id, 'train', 'happy', 'test_user', idem_key))
        db_conn.commit()
        
        # Check log entry
        db_cursor.execute("""
            SELECT * FROM promotion_log WHERE idempotency_key = %s
        """, (idem_key,))
        log = db_cursor.fetchone()
        
        assert log['video_id'] == video_id
        assert log['from_split'] == 'temp'
        assert log['to_split'] == 'train'
        assert log['label'] == 'happy'
        assert log['success'] is True
        assert log['promoted_at'] is not None


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
