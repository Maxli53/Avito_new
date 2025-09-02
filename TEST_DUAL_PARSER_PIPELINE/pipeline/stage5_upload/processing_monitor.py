"""
Processing Monitor Implementation
Monitors Avito processing windows and upload status
"""

from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class ProcessingMonitor:
    """
    Monitors Avito processing windows and results
    
    Tracks processing schedules, wait times, and provides
    status updates for uploaded content.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize processing monitor
        
        Args:
            config: Monitor configuration
        """
        self.config = config or {}
        self.logger = logger
        
        # Avito processing schedule (Moscow time)
        self.processing_times = self.config.get('processing_times', ["03:00", "11:00", "19:00"])
        self.timezone = self.config.get('timezone', 'MSK')
        self.processing_duration = self.config.get('processing_duration', 60)  # minutes
        
        # Status tracking
        self.upload_history: List[Dict[str, Any]] = []
    
    def get_next_processing_window(self) -> Dict[str, Any]:
        """
        Get information about the next Avito processing window
        
        Returns:
            Dictionary with next processing window details
        """
        current_time = datetime.now()
        current_hour = current_time.hour
        current_minute = current_time.minute
        
        next_window = None
        time_until_next = None
        
        # Check today's remaining windows
        for time_str in self.processing_times:
            hour, minute = map(int, time_str.split(':'))
            
            # Create datetime for this processing window today
            window_time = current_time.replace(hour=hour, minute=minute, second=0, microsecond=0)
            
            # If this window is still in the future today
            if window_time > current_time:
                next_window = time_str
                time_until_next = window_time - current_time
                break
        
        # If no more windows today, use tomorrow's first window
        if not next_window:
            next_window = self.processing_times[0] + " (next day)"
            
            # Calculate time until tomorrow's first window
            first_hour, first_minute = map(int, self.processing_times[0].split(':'))
            tomorrow = current_time + timedelta(days=1)
            next_window_time = tomorrow.replace(hour=first_hour, minute=first_minute, second=0, microsecond=0)
            time_until_next = next_window_time - current_time
        
        return {
            'next_window': next_window,
            'timezone': self.timezone,
            'time_until_next': time_until_next,
            'hours_until': time_until_next.total_seconds() / 3600 if time_until_next else 0,
            'processing_duration_minutes': self.processing_duration,
            'current_time': current_time.strftime('%H:%M'),
            'all_windows': self.processing_times
        }
    
    def is_processing_window_active(self) -> Dict[str, Any]:
        """
        Check if a processing window is currently active
        
        Returns:
            Dictionary with processing window status
        """
        current_time = datetime.now()
        current_hour = current_time.hour
        current_minute = current_time.minute
        
        for time_str in self.processing_times:
            window_hour, window_minute = map(int, time_str.split(':'))
            
            # Create start and end times for this window
            window_start = current_time.replace(hour=window_hour, minute=window_minute, second=0, microsecond=0)
            window_end = window_start + timedelta(minutes=self.processing_duration)
            
            # Check if current time is within this window
            if window_start <= current_time <= window_end:
                time_remaining = window_end - current_time
                
                return {
                    'active': True,
                    'window_start': time_str,
                    'window_end': window_end.strftime('%H:%M'),
                    'time_remaining': time_remaining,
                    'minutes_remaining': time_remaining.total_seconds() / 60,
                    'progress_percent': ((current_time - window_start).total_seconds() / 
                                       (self.processing_duration * 60)) * 100
                }
        
        return {
            'active': False,
            'next_window': self.get_next_processing_window()
        }
    
    def wait_for_processing(self) -> Dict[str, Any]:
        """
        Get information about processing wait times
        
        Returns:
            Dictionary with wait time information
        """
        next_window_info = self.get_next_processing_window()
        
        message = f"Next Avito processing window: {next_window_info['next_window']} {self.timezone}\n"
        message += f"Time until next window: {next_window_info['hours_until']:.1f} hours\n"
        message += f"Processing typically takes {self.processing_duration} minutes after the window starts"
        
        self.logger.info(message)
        
        return {
            'message': message,
            'next_window': next_window_info,
            'processing_info': {
                'duration_minutes': self.processing_duration,
                'typical_completion_time': f"{self.processing_duration} minutes after window start"
            }
        }
    
    def record_upload(self, filename: str, upload_time: Optional[datetime] = None, 
                     upload_success: bool = True, metadata: Optional[Dict[str, Any]] = None) -> None:
        """
        Record an upload in the history
        
        Args:
            filename: Name of uploaded file
            upload_time: Time of upload (defaults to now)
            upload_success: Whether upload was successful
            metadata: Additional upload metadata
        """
        upload_record = {
            'filename': filename,
            'upload_time': upload_time or datetime.now(),
            'upload_success': upload_success,
            'metadata': metadata or {},
            'id': len(self.upload_history) + 1
        }
        
        # Add processing window information
        next_window = self.get_next_processing_window()
        upload_record['expected_processing_window'] = next_window['next_window']
        upload_record['estimated_processing_time'] = (
            upload_record['upload_time'] + 
            timedelta(hours=next_window['hours_until'], minutes=self.processing_duration)
        )
        
        self.upload_history.append(upload_record)
        
        self.logger.info(
            f"Recorded upload: {filename} at {upload_record['upload_time'].strftime('%Y-%m-%d %H:%M:%S')}"
        )
    
    def get_upload_history(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get upload history
        
        Args:
            limit: Maximum number of records to return
            
        Returns:
            List of upload records
        """
        history = sorted(self.upload_history, key=lambda x: x['upload_time'], reverse=True)
        
        if limit:
            history = history[:limit]
        
        return history
    
    def get_pending_uploads(self) -> List[Dict[str, Any]]:
        """
        Get uploads that are still pending processing
        
        Returns:
            List of pending upload records
        """
        current_time = datetime.now()
        pending = []
        
        for upload in self.upload_history:
            if not upload['upload_success']:
                continue
                
            estimated_completion = upload['estimated_processing_time']
            
            # If estimated processing time hasn't passed yet, consider it pending
            if estimated_completion > current_time:
                time_until_completion = estimated_completion - current_time
                upload_copy = upload.copy()
                upload_copy['time_until_completion'] = time_until_completion
                upload_copy['hours_until_completion'] = time_until_completion.total_seconds() / 3600
                pending.append(upload_copy)
        
        return pending
    
    def get_processing_summary(self) -> Dict[str, Any]:
        """
        Get comprehensive processing summary
        
        Returns:
            Dictionary with processing status summary
        """
        current_window = self.is_processing_window_active()
        next_window = self.get_next_processing_window()
        pending_uploads = self.get_pending_uploads()
        recent_history = self.get_upload_history(limit=5)
        
        return {
            'current_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'timezone': self.timezone,
            'current_window': current_window,
            'next_window': next_window,
            'pending_uploads': len(pending_uploads),
            'pending_details': pending_uploads,
            'recent_uploads': len(recent_history),
            'recent_history': recent_history,
            'processing_schedule': {
                'windows': self.processing_times,
                'duration_minutes': self.processing_duration,
                'timezone': self.timezone
            }
        }
    
    def print_status_report(self) -> None:
        """Print formatted status report"""
        summary = self.get_processing_summary()
        
        print("\n" + "="*60)
        print("AVITO PROCESSING STATUS REPORT")
        print("="*60)
        print(f"Current Time: {summary['current_time']} {self.timezone}")
        print()
        
        # Current window status
        if summary['current_window']['active']:
            window = summary['current_window']
            print("🟢 PROCESSING WINDOW IS ACTIVE")
            print(f"   Window: {window['window_start']} - {window['window_end']}")
            print(f"   Time Remaining: {window['minutes_remaining']:.1f} minutes")
            print(f"   Progress: {window['progress_percent']:.1f}%")
        else:
            next_win = summary['next_window']
            print("🔴 NO ACTIVE PROCESSING WINDOW")
            print(f"   Next Window: {next_win['next_window']} {self.timezone}")
            print(f"   Time Until Next: {next_win['hours_until']:.1f} hours")
        
        print()
        
        # Pending uploads
        if summary['pending_uploads'] > 0:
            print(f"⏳ PENDING UPLOADS: {summary['pending_uploads']}")
            for upload in summary['pending_details'][:3]:  # Show up to 3
                print(f"   • {upload['filename']} - {upload['hours_until_completion']:.1f}h remaining")
        else:
            print("✅ NO PENDING UPLOADS")
        
        print()
        
        # Processing schedule
        print("📅 PROCESSING SCHEDULE:")
        for time_str in self.processing_times:
            print(f"   • {time_str} {self.timezone} (duration: {self.processing_duration}min)")
        
        print("="*60)