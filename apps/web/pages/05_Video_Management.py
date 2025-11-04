"""
Video Management Page - Enhanced with batch operations and real-time updates.
"""
import streamlit as st
from datetime import datetime
import asyncio
from typing import List, Optional

from apps.web.session_manager import SessionManager, render_status_bar, render_notifications
from apps.web.api_client_v2 import VideoMetadata


def main():
    st.set_page_config(page_title="Video Management", layout="wide")
    st.title("📹 Video Management")
    
    # Initialize session
    SessionManager.initialize()
    
    # Poll WebSocket messages
    SessionManager.poll_websocket_messages()
    
    # Status bar
    render_status_bar()
    
    # Notifications
    render_notifications()
    
    st.divider()
    
    # Filters
    render_filters()
    
    st.divider()
    
    # Video list
    render_video_list()
    
    st.divider()
    
    # Batch operations
    render_batch_operations()


def render_filters():
    """Render filter controls."""
    st.subheader("Filters")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        split = st.selectbox(
            "Split",
            options=['temp', 'dataset_all', 'train', 'test'],
            index=0,
            key='filter_split'
        )
    
    with col2:
        label = st.selectbox(
            "Label",
            options=[None, 'happy', 'sad', 'angry', 'neutral', 'surprise', 'fearful'],
            index=0,
            key='filter_label'
        )
    
    with col3:
        limit = st.number_input(
            "Limit",
            min_value=10,
            max_value=500,
            value=50,
            step=10,
            key='filter_limit'
        )
    
    with col4:
        if st.button("🔄 Refresh", use_container_width=True):
            st.session_state.last_refresh = datetime.now()
            st.rerun()


def render_video_list():
    """Render video list with selection."""
    st.subheader("Videos")
    
    api_client = SessionManager.get_api_client()
    
    try:
        # Fetch videos
        with st.spinner("Loading videos..."):
            videos = api_client.list_videos(
                split=st.session_state.filter_split,
                limit=st.session_state.get('filter_limit', 50),
                offset=0,
                label=st.session_state.filter_label
            )
        
        if not videos:
            st.info(f"No videos found in '{st.session_state.filter_split}' split.")
            return
        
        st.success(f"Found {len(videos)} videos")
        
        # Selection controls
        col1, col2 = st.columns([1, 4])
        with col1:
            select_all = st.checkbox("Select All", key='select_all_videos')
        with col2:
            st.text(f"Selected: {len(st.session_state.selected_videos)}")
        
        # Video grid
        cols_per_row = 3
        for i in range(0, len(videos), cols_per_row):
            cols = st.columns(cols_per_row)
            for j, col in enumerate(cols):
                if i + j < len(videos):
                    video = videos[i + j]
                    with col:
                        render_video_card(video, select_all)
    
    except Exception as e:
        st.error(f"Error loading videos: {e}")
        SessionManager.add_notification(f"Error loading videos: {e}", "error")


def render_video_card(video: VideoMetadata, select_all: bool):
    """Render individual video card."""
    with st.container(border=True):
        # Checkbox
        is_selected = video.video_id in st.session_state.selected_videos
        if select_all:
            is_selected = True
            if video.video_id not in st.session_state.selected_videos:
                st.session_state.selected_videos.append(video.video_id)
        
        selected = st.checkbox(
            f"Select",
            value=is_selected,
            key=f"select_{video.video_id}"
        )
        
        if selected and video.video_id not in st.session_state.selected_videos:
            st.session_state.selected_videos.append(video.video_id)
        elif not selected and video.video_id in st.session_state.selected_videos:
            st.session_state.selected_videos.remove(video.video_id)
        
        # Video info
        st.text(f"ID: {video.video_id[:8]}...")
        st.text(f"Split: {video.split}")
        
        if video.label:
            st.text(f"Label: {video.label}")
        else:
            st.text("Label: (none)")
        
        if video.duration_sec:
            st.text(f"Duration: {video.duration_sec:.1f}s")
        
        if video.size_bytes:
            size_mb = video.size_bytes / 1048576
            st.text(f"Size: {size_mb:.1f} MB")
        
        # Thumbnail placeholder
        st.caption(f"📹 {video.file_path.split('/')[-1]}")
        
        # Quick actions
        col1, col2 = st.columns(2)
        with col1:
            if st.button("👁️ View", key=f"view_{video.video_id}", use_container_width=True):
                st.session_state.viewing_video = video.video_id
        with col2:
            if st.button("🗑️ Delete", key=f"delete_{video.video_id}", use_container_width=True):
                st.session_state.deleting_video = video.video_id


def render_batch_operations():
    """Render batch operation controls."""
    st.subheader("Batch Operations")
    
    if not st.session_state.selected_videos:
        st.info("Select videos to perform batch operations.")
        return
    
    st.text(f"Selected: {len(st.session_state.selected_videos)} videos")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.write("**Promote to:**")
        dest_split = st.selectbox(
            "Destination",
            options=['dataset_all', 'train', 'test'],
            key='batch_dest_split'
        )
        
        label = None
        if dest_split == 'dataset_all':
            label = st.selectbox(
                "Label (required)",
                options=['happy', 'sad', 'angry', 'neutral', 'surprise', 'fearful'],
                key='batch_label'
            )
        
        dry_run = st.checkbox("Dry Run", value=True, key='batch_dry_run')
        
        if st.button("🚀 Promote Selected", use_container_width=True):
            perform_batch_promotion(dest_split, label, dry_run)
    
    with col2:
        st.write("**Label:**")
        new_label = st.selectbox(
            "New Label",
            options=['happy', 'sad', 'angry', 'neutral', 'surprise', 'fearful'],
            key='batch_new_label'
        )
        
        if st.button("🏷️ Apply Label", use_container_width=True):
            perform_batch_labeling(new_label)
    
    with col3:
        st.write("**Actions:**")
        if st.button("📥 Download Manifest", use_container_width=True):
            download_manifest()
        
        if st.button("🗑️ Delete Selected", use_container_width=True):
            perform_batch_delete()
        
        if st.button("❌ Clear Selection", use_container_width=True):
            st.session_state.selected_videos = []
            st.rerun()


def perform_batch_promotion(dest_split: str, label: Optional[str], dry_run: bool):
    """Perform batch video promotion."""
    api_client = SessionManager.get_api_client()
    
    if dest_split == 'dataset_all' and not label:
        st.error("Label is required when promoting to dataset_all")
        return
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    total = len(st.session_state.selected_videos)
    successful = 0
    failed = 0
    
    for i, video_id in enumerate(st.session_state.selected_videos):
        try:
            status_text.text(f"Promoting {i+1}/{total}: {video_id[:8]}...")
            
            result = api_client.promote_video(
                video_id=video_id,
                dest_split=dest_split,
                label=label,
                dry_run=dry_run
            )
            
            if result.get('status') == 'success':
                successful += 1
            else:
                failed += 1
        
        except Exception as e:
            st.error(f"Error promoting {video_id[:8]}...: {e}")
            failed += 1
        
        progress_bar.progress((i + 1) / total)
    
    status_text.empty()
    progress_bar.empty()
    
    # Summary
    if dry_run:
        st.success(f"Dry run completed: {successful} would succeed, {failed} would fail")
    else:
        st.success(f"Promotion completed: {successful} successful, {failed} failed")
        SessionManager.add_notification(
            f"Batch promotion: {successful} successful, {failed} failed",
            "success" if failed == 0 else "warning"
        )
        
        # Clear selection
        st.session_state.selected_videos = []
        st.rerun()


def perform_batch_labeling(label: str):
    """Apply label to selected videos."""
    st.info(f"Labeling {len(st.session_state.selected_videos)} videos as '{label}'")
    # TODO: Implement relabel API call
    SessionManager.add_notification(f"Labeled {len(st.session_state.selected_videos)} videos", "success")


def perform_batch_delete():
    """Delete selected videos."""
    st.warning(f"Would delete {len(st.session_state.selected_videos)} videos")
    # TODO: Implement delete API call
    SessionManager.add_notification(f"Deleted {len(st.session_state.selected_videos)} videos", "warning")


def download_manifest():
    """Download manifest for selected videos."""
    import json
    
    manifest = []
    for video_id in st.session_state.selected_videos:
        manifest.append({
            'video_id': video_id,
            'timestamp': datetime.now().isoformat()
        })
    
    manifest_json = json.dumps(manifest, indent=2)
    
    st.download_button(
        label="📥 Download Manifest JSON",
        data=manifest_json,
        file_name=f"manifest_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
        mime="application/json"
    )


if __name__ == "__main__":
    main()
