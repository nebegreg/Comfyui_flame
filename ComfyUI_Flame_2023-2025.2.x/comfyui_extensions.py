#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
ComfyUI-Flame Extensions v3.0
Advanced features: Queue Management, WebSocket Monitor, Preset System

This module provides enhanced functionality for the ComfyUI-Flame integration
including queue management, real-time progress monitoring, and workflow presets.
"""

import os
import json
import time
import threading
import queue
import uuid
from datetime import datetime
from enum import Enum
import websocket
import requests
from typing import Dict, List, Optional, Callable, Any

# =============================================================================
# QUEUE MANAGEMENT SYSTEM
# =============================================================================

class JobStatus(Enum):
    """Job status enumeration"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class ComfyUIJob:
    """Represents a single ComfyUI processing job"""

    def __init__(self, job_id: str, clip, workflow_path: str, parameters: Dict = None):
        self.job_id = job_id
        self.clip = clip
        self.clip_name = clip.name if hasattr(clip, 'name') else str(clip)
        self.workflow_path = workflow_path
        self.workflow_name = os.path.basename(workflow_path)
        self.parameters = parameters or {}
        self.status = JobStatus.PENDING
        self.progress = 0.0
        self.current_frame = 0
        self.total_frames = 0
        self.start_time = None
        self.end_time = None
        self.error_message = None
        self.result_path = None
        self.prompt_id = None

    def start(self):
        """Mark job as started"""
        self.status = JobStatus.PROCESSING
        self.start_time = time.time()

    def complete(self, result_path: str):
        """Mark job as completed"""
        self.status = JobStatus.COMPLETED
        self.end_time = time.time()
        self.result_path = result_path
        self.progress = 100.0

    def fail(self, error_message: str):
        """Mark job as failed"""
        self.status = JobStatus.FAILED
        self.end_time = time.time()
        self.error_message = error_message

    def cancel(self):
        """Cancel the job"""
        self.status = JobStatus.CANCELLED
        self.end_time = time.time()

    def update_progress(self, progress: float, current_frame: int = None):
        """Update job progress"""
        self.progress = min(100.0, max(0.0, progress))
        if current_frame is not None:
            self.current_frame = current_frame

    def get_elapsed_time(self) -> float:
        """Get elapsed time in seconds"""
        if self.start_time is None:
            return 0.0
        end = self.end_time if self.end_time else time.time()
        return end - self.start_time

    def get_eta(self) -> float:
        """Get estimated time remaining in seconds"""
        if self.progress <= 0 or self.start_time is None:
            return 0.0
        elapsed = self.get_elapsed_time()
        total_estimated = elapsed / (self.progress / 100.0)
        return max(0.0, total_estimated - elapsed)

    def to_dict(self) -> Dict:
        """Convert job to dictionary"""
        return {
            'job_id': self.job_id,
            'clip_name': self.clip_name,
            'workflow_name': self.workflow_name,
            'status': self.status.value,
            'progress': self.progress,
            'current_frame': self.current_frame,
            'total_frames': self.total_frames,
            'elapsed_time': self.get_elapsed_time(),
            'eta': self.get_eta(),
            'error_message': self.error_message
        }

class QueueMode(Enum):
    """Queue processing mode"""
    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"

class ComfyUIQueueManager:
    """
    Manages multiple ComfyUI processing jobs with support for
    sequential and parallel processing modes.
    """

    def __init__(self, max_parallel_jobs: int = 2, mode: QueueMode = QueueMode.SEQUENTIAL):
        self.max_parallel_jobs = max_parallel_jobs
        self.mode = mode
        self.jobs: List[ComfyUIJob] = []
        self.processing_jobs: List[ComfyUIJob] = []
        self.completed_jobs: List[ComfyUIJob] = []
        self.failed_jobs: List[ComfyUIJob] = []
        self.is_processing = False
        self.stop_requested = False
        self.pause_requested = False
        self.lock = threading.Lock()
        self.callbacks: Dict[str, List[Callable]] = {
            'on_job_start': [],
            'on_job_progress': [],
            'on_job_complete': [],
            'on_job_failed': [],
            'on_queue_complete': []
        }

    def add_job(self, clip, workflow_path: str, parameters: Dict = None) -> str:
        """Add a job to the queue"""
        job_id = str(uuid.uuid4())
        job = ComfyUIJob(job_id, clip, workflow_path, parameters)

        with self.lock:
            self.jobs.append(job)

        return job_id

    def add_jobs_batch(self, clips: List, workflow_path: str, parameters: Dict = None) -> List[str]:
        """Add multiple jobs at once"""
        job_ids = []
        for clip in clips:
            job_id = self.add_job(clip, workflow_path, parameters)
            job_ids.append(job_id)
        return job_ids

    def get_job(self, job_id: str) -> Optional[ComfyUIJob]:
        """Get job by ID"""
        with self.lock:
            for job in self.jobs + self.processing_jobs + self.completed_jobs + self.failed_jobs:
                if job.job_id == job_id:
                    return job
        return None

    def remove_job(self, job_id: str) -> bool:
        """Remove a pending job from queue"""
        with self.lock:
            for i, job in enumerate(self.jobs):
                if job.job_id == job_id:
                    self.jobs.pop(i)
                    return True
        return False

    def clear_queue(self):
        """Clear all pending jobs"""
        with self.lock:
            self.jobs.clear()

    def clear_completed(self):
        """Clear completed jobs history"""
        with self.lock:
            self.completed_jobs.clear()
            self.failed_jobs.clear()

    def get_status(self) -> Dict:
        """Get queue status"""
        with self.lock:
            return {
                'mode': self.mode.value,
                'is_processing': self.is_processing,
                'pending_count': len(self.jobs),
                'processing_count': len(self.processing_jobs),
                'completed_count': len(self.completed_jobs),
                'failed_count': len(self.failed_jobs),
                'pending_jobs': [job.to_dict() for job in self.jobs],
                'processing_jobs': [job.to_dict() for job in self.processing_jobs],
                'completed_jobs': [job.to_dict() for job in self.completed_jobs[-10:]],  # Last 10
                'failed_jobs': [job.to_dict() for job in self.failed_jobs[-10:]]  # Last 10
            }

    def register_callback(self, event: str, callback: Callable):
        """Register a callback for events"""
        if event in self.callbacks:
            self.callbacks[event].append(callback)

    def _trigger_callback(self, event: str, *args, **kwargs):
        """Trigger callbacks for an event"""
        if event in self.callbacks:
            for callback in self.callbacks[event]:
                try:
                    callback(*args, **kwargs)
                except Exception as e:
                    print(f"Callback error: {e}")

    def process_queue(self, process_function: Callable):
        """
        Start processing the queue

        Args:
            process_function: Function to process a single job
                             Should accept (job, progress_callback) and return result_path or None
        """
        if self.is_processing:
            print("Queue is already processing")
            return

        self.is_processing = True
        self.stop_requested = False
        self.pause_requested = False

        def worker():
            while not self.stop_requested:
                # Check for pause
                while self.pause_requested and not self.stop_requested:
                    time.sleep(0.5)

                if self.stop_requested:
                    break

                # Get next job
                job = None
                with self.lock:
                    # Check if we can process more jobs
                    if self.mode == QueueMode.SEQUENTIAL:
                        can_process = len(self.processing_jobs) == 0
                    else:  # PARALLEL
                        can_process = len(self.processing_jobs) < self.max_parallel_jobs

                    if can_process and len(self.jobs) > 0:
                        job = self.jobs.pop(0)
                        self.processing_jobs.append(job)

                if job is None:
                    # No jobs available, check if we're done
                    with self.lock:
                        if len(self.processing_jobs) == 0 and len(self.jobs) == 0:
                            break
                    time.sleep(0.5)
                    continue

                # Process the job
                try:
                    job.start()
                    self._trigger_callback('on_job_start', job)

                    # Progress callback for the job
                    def progress_callback(progress: float, current_frame: int = None):
                        job.update_progress(progress, current_frame)
                        self._trigger_callback('on_job_progress', job)

                    # Process
                    result_path = process_function(job, progress_callback)

                    if result_path:
                        job.complete(result_path)
                        with self.lock:
                            self.processing_jobs.remove(job)
                            self.completed_jobs.append(job)
                        self._trigger_callback('on_job_complete', job)
                    else:
                        raise Exception("Processing returned no result")

                except Exception as e:
                    error_msg = str(e)
                    job.fail(error_msg)
                    with self.lock:
                        self.processing_jobs.remove(job)
                        self.failed_jobs.append(job)
                    self._trigger_callback('on_job_failed', job)

            # Processing complete
            self.is_processing = False
            self._trigger_callback('on_queue_complete')

        # Start worker thread
        thread = threading.Thread(target=worker, daemon=True)
        thread.start()

    def pause(self):
        """Pause queue processing"""
        self.pause_requested = True

    def resume(self):
        """Resume queue processing"""
        self.pause_requested = False

    def stop(self):
        """Stop queue processing"""
        self.stop_requested = True

# =============================================================================
# WEBSOCKET PROGRESS MONITOR
# =============================================================================

class ComfyUIProgressMonitor:
    """
    Real-time progress tracking via WebSocket connection to ComfyUI
    """

    def __init__(self, comfyui_url: str = "http://127.0.0.1:8188"):
        self.comfyui_url = comfyui_url
        self.ws_url = comfyui_url.replace('http://', 'ws://').replace('https://', 'wss://') + '/ws'
        self.ws = None
        self.is_connected = False
        self.callbacks: Dict[str, List[Callable]] = {
            'on_progress': [],
            'on_preview': [],
            'on_complete': [],
            'on_error': []
        }
        self.monitored_prompts: Dict[str, Dict] = {}  # prompt_id -> info
        self.lock = threading.Lock()

    def connect(self) -> bool:
        """Establish WebSocket connection"""
        try:
            self.ws = websocket.WebSocketApp(
                self.ws_url,
                on_message=self._on_message,
                on_error=self._on_error,
                on_close=self._on_close,
                on_open=self._on_open
            )

            # Start WebSocket in background thread
            wst = threading.Thread(target=self.ws.run_forever, daemon=True)
            wst.start()

            # Wait for connection
            for _ in range(50):  # 5 seconds timeout
                if self.is_connected:
                    return True
                time.sleep(0.1)

            return False

        except Exception as e:
            print(f"WebSocket connection error: {e}")
            return False

    def disconnect(self):
        """Close WebSocket connection"""
        if self.ws:
            self.ws.close()
        self.is_connected = False

    def monitor_prompt(self, prompt_id: str, total_steps: int = 20):
        """Start monitoring a prompt"""
        with self.lock:
            self.monitored_prompts[prompt_id] = {
                'total_steps': total_steps,
                'current_step': 0,
                'current_node': None,
                'progress': 0.0
            }

    def unmonitor_prompt(self, prompt_id: str):
        """Stop monitoring a prompt"""
        with self.lock:
            if prompt_id in self.monitored_prompts:
                del self.monitored_prompts[prompt_id]

    def get_progress(self, prompt_id: str) -> Optional[Dict]:
        """Get current progress for a prompt"""
        with self.lock:
            return self.monitored_prompts.get(prompt_id)

    def register_callback(self, event: str, callback: Callable):
        """Register callback for events"""
        if event in self.callbacks:
            self.callbacks[event].append(callback)

    def _trigger_callback(self, event: str, *args, **kwargs):
        """Trigger callbacks"""
        if event in self.callbacks:
            for callback in self.callbacks[event]:
                try:
                    callback(*args, **kwargs)
                except Exception as e:
                    print(f"Callback error: {e}")

    def _on_open(self, ws):
        """WebSocket opened"""
        self.is_connected = True
        print("WebSocket connected to ComfyUI")

    def _on_close(self, ws, close_status_code, close_msg):
        """WebSocket closed"""
        self.is_connected = False
        print(f"WebSocket disconnected: {close_msg}")

    def _on_error(self, ws, error):
        """WebSocket error"""
        print(f"WebSocket error: {error}")
        self._trigger_callback('on_error', error)

    def _on_message(self, ws, message):
        """Handle incoming WebSocket message"""
        try:
            data = json.loads(message)
            msg_type = data.get('type')

            if msg_type == 'progress':
                # Progress update
                node = data.get('data', {}).get('node')
                value = data.get('data', {}).get('value', 0)
                max_value = data.get('data', {}).get('max', 100)

                # Update monitored prompts
                with self.lock:
                    for prompt_id, info in self.monitored_prompts.items():
                        info['current_node'] = node
                        info['current_step'] = value
                        info['progress'] = (value / max_value * 100.0) if max_value > 0 else 0

                self._trigger_callback('on_progress', node, value, max_value)

            elif msg_type == 'executing':
                # Node execution
                node = data.get('data', {}).get('node')
                prompt_id = data.get('data', {}).get('prompt_id')

                with self.lock:
                    if prompt_id in self.monitored_prompts:
                        self.monitored_prompts[prompt_id]['current_node'] = node

            elif msg_type == 'executed':
                # Node completed
                prompt_id = data.get('data', {}).get('prompt_id')
                output = data.get('data', {}).get('output', {})

                # Check for preview images
                if 'images' in output:
                    images = output['images']
                    self._trigger_callback('on_preview', prompt_id, images)

            elif msg_type == 'execution_complete':
                # Execution complete
                prompt_id = data.get('data', {}).get('prompt_id')
                self._trigger_callback('on_complete', prompt_id)
                self.unmonitor_prompt(prompt_id)

        except Exception as e:
            print(f"Error parsing WebSocket message: {e}")

    def get_preview_image(self, prompt_id: str, filename: str) -> Optional[bytes]:
        """Fetch preview image from ComfyUI"""
        try:
            url = f"{self.comfyui_url}/view"
            params = {
                'filename': filename,
                'type': 'temp',
                'subfolder': '',
                'rand': str(time.time())
            }
            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 200:
                return response.content
            return None
        except Exception as e:
            print(f"Error fetching preview: {e}")
            return None

# =============================================================================
# WORKFLOW PRESET SYSTEM
# =============================================================================

class WorkflowPreset:
    """Represents a workflow preset with custom parameters"""

    def __init__(self, name: str, workflow_data: Dict, parameters: Dict = None,
                 description: str = "", tags: List[str] = None):
        self.name = name
        self.workflow_data = workflow_data
        self.parameters = parameters or {}
        self.description = description
        self.tags = tags or []
        self.created_at = datetime.now().isoformat()
        self.last_used = None
        self.use_count = 0
        self.is_favorite = False

    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            'name': self.name,
            'workflow_data': self.workflow_data,
            'parameters': self.parameters,
            'description': self.description,
            'tags': self.tags,
            'created_at': self.created_at,
            'last_used': self.last_used,
            'use_count': self.use_count,
            'is_favorite': self.is_favorite
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'WorkflowPreset':
        """Create from dictionary"""
        preset = cls(
            name=data['name'],
            workflow_data=data['workflow_data'],
            parameters=data.get('parameters'),
            description=data.get('description', ''),
            tags=data.get('tags', [])
        )
        preset.created_at = data.get('created_at', preset.created_at)
        preset.last_used = data.get('last_used')
        preset.use_count = data.get('use_count', 0)
        preset.is_favorite = data.get('is_favorite', False)
        return preset

    def use(self):
        """Mark preset as used"""
        self.last_used = datetime.now().isoformat()
        self.use_count += 1

class WorkflowPresetManager:
    """
    Manages workflow presets - save, load, organize, and share
    """

    def __init__(self, presets_dir: str = "/opt/Autodesk/shared/python/comfyui_presets"):
        self.presets_dir = presets_dir
        self.presets: Dict[str, WorkflowPreset] = {}
        self.categories: Dict[str, List[str]] = {}  # category -> [preset_names]

        # Create presets directory if it doesn't exist
        if not os.path.exists(presets_dir):
            try:
                os.makedirs(presets_dir)
            except Exception as e:
                print(f"Error creating presets directory: {e}")

        # Load existing presets
        self.load_all_presets()

    def save_preset(self, preset: WorkflowPreset) -> bool:
        """Save a preset to disk"""
        try:
            preset_path = os.path.join(self.presets_dir, f"{preset.name}.json")
            with open(preset_path, 'w') as f:
                json.dump(preset.to_dict(), f, indent=2)

            self.presets[preset.name] = preset
            return True

        except Exception as e:
            print(f"Error saving preset: {e}")
            return False

    def load_preset(self, name: str) -> Optional[WorkflowPreset]:
        """Load a preset by name"""
        if name in self.presets:
            return self.presets[name]

        try:
            preset_path = os.path.join(self.presets_dir, f"{name}.json")
            if os.path.exists(preset_path):
                with open(preset_path, 'r') as f:
                    data = json.load(f)
                preset = WorkflowPreset.from_dict(data)
                self.presets[name] = preset
                return preset
        except Exception as e:
            print(f"Error loading preset {name}: {e}")

        return None

    def load_all_presets(self):
        """Load all presets from directory"""
        try:
            if not os.path.exists(self.presets_dir):
                return

            for filename in os.listdir(self.presets_dir):
                if filename.endswith('.json'):
                    name = filename[:-5]  # Remove .json
                    self.load_preset(name)

        except Exception as e:
            print(f"Error loading presets: {e}")

    def delete_preset(self, name: str) -> bool:
        """Delete a preset"""
        try:
            preset_path = os.path.join(self.presets_dir, f"{name}.json")
            if os.path.exists(preset_path):
                os.remove(preset_path)

            if name in self.presets:
                del self.presets[name]

            return True

        except Exception as e:
            print(f"Error deleting preset: {e}")
            return False

    def list_presets(self, category: str = None, favorites_only: bool = False) -> List[WorkflowPreset]:
        """List presets with optional filtering"""
        presets = list(self.presets.values())

        if favorites_only:
            presets = [p for p in presets if p.is_favorite]

        if category:
            presets = [p for p in presets if category in p.tags]

        # Sort by use count (most used first), then by name
        presets.sort(key=lambda p: (-p.use_count, p.name))

        return presets

    def search_presets(self, query: str) -> List[WorkflowPreset]:
        """Search presets by name, description, or tags"""
        query = query.lower()
        results = []

        for preset in self.presets.values():
            if (query in preset.name.lower() or
                query in preset.description.lower() or
                any(query in tag.lower() for tag in preset.tags)):
                results.append(preset)

        return results

    def add_to_favorites(self, name: str) -> bool:
        """Add preset to favorites"""
        preset = self.load_preset(name)
        if preset:
            preset.is_favorite = True
            return self.save_preset(preset)
        return False

    def remove_from_favorites(self, name: str) -> bool:
        """Remove preset from favorites"""
        preset = self.load_preset(name)
        if preset:
            preset.is_favorite = False
            return self.save_preset(preset)
        return False

    def get_favorites(self) -> List[WorkflowPreset]:
        """Get all favorite presets"""
        return self.list_presets(favorites_only=True)

    def export_preset(self, name: str, export_path: str) -> bool:
        """Export preset to a file"""
        preset = self.load_preset(name)
        if preset:
            try:
                with open(export_path, 'w') as f:
                    json.dump(preset.to_dict(), f, indent=2)
                return True
            except Exception as e:
                print(f"Error exporting preset: {e}")
        return False

    def import_preset(self, import_path: str, new_name: str = None) -> Optional[WorkflowPreset]:
        """Import preset from a file"""
        try:
            with open(import_path, 'r') as f:
                data = json.load(f)

            preset = WorkflowPreset.from_dict(data)

            if new_name:
                preset.name = new_name

            if self.save_preset(preset):
                return preset

        except Exception as e:
            print(f"Error importing preset: {e}")

        return None

# =============================================================================
# SMART MEDIA MANAGER
# =============================================================================

class MediaFormat(Enum):
    """Supported media formats"""
    JPEG = "jpeg"
    PNG = "png"
    EXR = "exr"
    DPX = "dpx"
    TIFF = "tiff"

class SmartMediaManager:
    """
    Intelligent export and import with format detection and optimization
    """

    @staticmethod
    def detect_optimal_format(clip, workflow_type: str = None) -> MediaFormat:
        """
        Detect optimal export format based on clip properties and workflow

        Args:
            clip: Flame clip object
            workflow_type: Type of workflow (e.g., 'keying', 'depth', 'grading')

        Returns:
            Optimal MediaFormat
        """
        # Check if clip has alpha channel
        has_alpha = hasattr(clip, 'channels') and 'A' in clip.channels

        # Check bit depth
        bit_depth = getattr(clip, 'bit_depth', 8)

        # Workflow-specific recommendations
        if workflow_type:
            if workflow_type in ['depth', 'normal', 'ao', '3d']:
                # High precision for 3D data
                return MediaFormat.EXR

            elif workflow_type in ['keying', 'matte', 'alpha']:
                # Need alpha channel
                return MediaFormat.PNG if bit_depth <= 8 else MediaFormat.EXR

            elif workflow_type in ['grading', 'color', 'lut']:
                # Color-critical work
                return MediaFormat.DPX if bit_depth >= 10 else MediaFormat.PNG

            elif workflow_type in ['preview', 'style', 'generation']:
                # Speed over quality
                return MediaFormat.JPEG

        # Default logic
        if has_alpha:
            return MediaFormat.PNG if bit_depth <= 8 else MediaFormat.EXR
        elif bit_depth >= 10:
            return MediaFormat.DPX
        elif bit_depth == 16:
            return MediaFormat.EXR
        else:
            return MediaFormat.PNG

    @staticmethod
    def get_format_settings(format: MediaFormat, bit_depth: int = 8) -> Dict:
        """Get export settings for a format"""
        settings = {
            MediaFormat.JPEG: {
                'extension': 'jpg',
                'quality': 95,
                'bit_depth': 8,
                'alpha': False,
                'color_space': 'sRGB'
            },
            MediaFormat.PNG: {
                'extension': 'png',
                'compression': 3,
                'bit_depth': min(16, bit_depth),
                'alpha': True,
                'color_space': 'linear'
            },
            MediaFormat.EXR: {
                'extension': 'exr',
                'compression': 'zip',
                'bit_depth': 16,
                'alpha': True,
                'color_space': 'linear'
            },
            MediaFormat.DPX: {
                'extension': 'dpx',
                'bit_depth': 10,
                'alpha': False,
                'color_space': 'linear'
            },
            MediaFormat.TIFF: {
                'extension': 'tiff',
                'compression': 'lzw',
                'bit_depth': min(16, bit_depth),
                'alpha': True,
                'color_space': 'linear'
            }
        }

        return settings.get(format, settings[MediaFormat.PNG])

    @staticmethod
    def auto_detect_sequences(directory: str) -> Dict[str, List[str]]:
        """
        Automatically detect and group image sequences in a directory

        Returns:
            Dictionary of sequence_name -> [file_paths]
        """
        import re

        sequences = {}

        try:
            files = os.listdir(directory)
            image_files = [f for f in files if f.endswith(('.jpg', '.jpeg', '.png', '.exr', '.dpx', '.tiff', '.tif'))]

            for filename in image_files:
                # Try to extract sequence pattern (name + frame number)
                match = re.match(r'^(.+?)[-_]?v?(\d+)\.(\d{4,5})\.(jpg|jpeg|png|exr|dpx|tiff|tif)$', filename, re.IGNORECASE)

                if match:
                    prefix = match.group(1)
                    version = match.group(2) if match.group(2) else "1"
                    frame = match.group(3)
                    ext = match.group(4)

                    seq_name = f"{prefix}_v{version}"

                    if seq_name not in sequences:
                        sequences[seq_name] = []
                    sequences[seq_name].append(os.path.join(directory, filename))
                else:
                    # Single file or non-standard naming
                    base = os.path.splitext(filename)[0]
                    if base not in sequences:
                        sequences[base] = []
                    sequences[base].append(os.path.join(directory, filename))

            # Sort each sequence
            for seq_name in sequences:
                sequences[seq_name].sort()

        except Exception as e:
            print(f"Error detecting sequences: {e}")

        return sequences

# =============================================================================
# ROBUST COMFYUI CLIENT
# =============================================================================

class RobustComfyUIClient:
    """
    Handle ComfyUI connection issues gracefully with auto-retry and recovery
    """

    def __init__(self, url: str = "http://127.0.0.1:8188", max_retries: int = 3, retry_delay: int = 5):
        self.url = url
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.last_health_check = 0
        self.health_check_interval = 30  # seconds

    def check_health(self) -> bool:
        """Ping ComfyUI to ensure it's responsive"""
        try:
            response = requests.get(f"{self.url}/system_stats", timeout=5)
            return response.status_code == 200
        except:
            return False

    def call_api_with_retry(self, endpoint: str, data: Dict = None, method: str = "POST") -> Optional[Dict]:
        """
        Call API with exponential backoff retry

        Args:
            endpoint: API endpoint (e.g., '/prompt')
            data: Request data
            method: HTTP method

        Returns:
            Response JSON or None on failure
        """
        for attempt in range(self.max_retries):
            try:
                url = f"{self.url}{endpoint}"

                if method == "POST":
                    response = requests.post(url, json=data, timeout=30)
                elif method == "GET":
                    response = requests.get(url, timeout=30)
                else:
                    raise ValueError(f"Unsupported method: {method}")

                if response.status_code == 200:
                    return response.json()
                else:
                    print(f"API returned status {response.status_code}")

            except requests.exceptions.ConnectionError:
                print(f"Connection error (attempt {attempt + 1}/{self.max_retries})")

            except requests.exceptions.Timeout:
                print(f"Request timeout (attempt {attempt + 1}/{self.max_retries})")

            except Exception as e:
                print(f"API error: {e} (attempt {attempt + 1}/{self.max_retries})")

            # Exponential backoff
            if attempt < self.max_retries - 1:
                delay = self.retry_delay * (2 ** attempt)
                print(f"Retrying in {delay} seconds...")
                time.sleep(delay)

        return None

    def auto_recover(self) -> bool:
        """
        Attempt to recover from common errors

        Returns:
            True if recovery successful
        """
        print("Attempting auto-recovery...")

        # Check if ComfyUI is running
        if not self.check_health():
            print("ComfyUI is not responding")
            return False

        # Try to clear queue
        try:
            response = requests.post(f"{self.url}/queue", json={"clear": True}, timeout=10)
            if response.status_code == 200:
                print("Cleared ComfyUI queue")
                return True
        except:
            pass

        # Try to free memory
        try:
            response = requests.post(f"{self.url}/free", json={"unload_models": True}, timeout=10)
            if response.status_code == 200:
                print("Freed ComfyUI memory")
                return True
        except:
            pass

        return False

# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def log_to_file(message: str, log_file: str = "/tmp/flame_comfyui_v3.log"):
    """Write a message to log file with timestamp"""
    try:
        with open(log_file, "a") as f:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            f.write(f"[{timestamp}] {message}\n")
    except:
        pass

# Example usage
if __name__ == "__main__":
    print("ComfyUI Extensions v3.0")
    print("=" * 50)

    # Test Queue Manager
    print("\n1. Testing Queue Manager...")
    queue_mgr = ComfyUIQueueManager(max_parallel_jobs=2)
    print(f"   Queue created with mode: {queue_mgr.mode.value}")

    # Test WebSocket Monitor
    print("\n2. Testing WebSocket Monitor...")
    monitor = ComfyUIProgressMonitor()
    if monitor.connect():
        print("   ✓ WebSocket connected")
        monitor.disconnect()
    else:
        print("   ✗ WebSocket connection failed (ComfyUI not running?)")

    # Test Preset Manager
    print("\n3. Testing Preset Manager...")
    preset_mgr = WorkflowPresetManager()
    print(f"   Loaded {len(preset_mgr.presets)} presets")

    # Test Robust Client
    print("\n4. Testing Robust Client...")
    client = RobustComfyUIClient()
    if client.check_health():
        print("   ✓ ComfyUI is healthy")
    else:
        print("   ✗ ComfyUI is not responding")

    print("\n" + "=" * 50)
    print("All tests complete!")
