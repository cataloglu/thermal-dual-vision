"""
Video frame-by-frame analyzer.
Detects duplicate frames, dropped frames, timing issues.
"""
import cv2
import numpy as np
from pathlib import Path
import json

def analyze_video(video_path: str):
    """Analyze video frame by frame."""
    
    print(f"Analyzing video: {video_path}")
    
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"ERROR: Cannot open video: {video_path}")
        return
    
    # Get video properties
    fps = cap.get(cv2.CAP_PROP_FPS)
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    duration = frame_count / fps if fps > 0 else 0
    
    print(f"\n=== VIDEO PROPERTIES ===")
    print(f"  Resolution: {width}x{height}")
    print(f"  FPS: {fps:.2f}")
    print(f"  Total Frames: {frame_count}")
    print(f"  Duration: {duration:.2f}s")
    print(f"  Frame interval: {1000/fps:.2f}ms\n")
    
    # Analysis
    frames = []
    prev_frame = None
    duplicate_count = 0
    duplicate_sequences = []
    current_duplicate_seq = []
    timestamp_jumps = []
    
    frame_idx = 0
    prev_timestamp_ms = 0
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        # Get ACTUAL timestamp from video (not calculated)
        timestamp_ms = cap.get(cv2.CAP_PROP_POS_MSEC)
        expected_timestamp_ms = (frame_idx / fps) * 1000
        
        # Convert to grayscale for comparison
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # Check for duplicates (compare with previous frame)
        is_duplicate = False
        diff_score = 0.0
        
        if prev_frame is not None:
            # Calculate MSE (Mean Squared Error)
            diff = cv2.absdiff(gray, prev_frame)
            mse = np.mean(diff ** 2)
            diff_score = mse
            
            # If MSE < threshold, frames are identical/duplicate
            if mse < 1.0:  # Very low threshold for exact duplicates
                is_duplicate = True
                duplicate_count += 1
                current_duplicate_seq.append(frame_idx)
            else:
                # End of duplicate sequence
                if len(current_duplicate_seq) > 0:
                    duplicate_sequences.append(current_duplicate_seq.copy())
                    current_duplicate_seq = []
        
        # Detect timestamp jumps (missing frames)
        timestamp_jump = False
        timestamp_gap = 0
        if frame_idx > 0:
            expected_gap = 1000 / fps  # Expected gap between frames
            actual_gap = timestamp_ms - prev_timestamp_ms
            
            # If gap is much larger than expected, we have missing frames
            if actual_gap > expected_gap * 2:  # 2x threshold
                timestamp_jump = True
                timestamp_gap = actual_gap
                timestamp_jumps.append({
                    'frame': frame_idx,
                    'from_ms': prev_timestamp_ms,
                    'to_ms': timestamp_ms,
                    'gap_ms': actual_gap,
                    'gap_seconds': actual_gap / 1000,
                    'expected_gap_ms': expected_gap,
                    'missing_frames_estimate': int(actual_gap / expected_gap) - 1
                })
        
        frames.append({
            'index': frame_idx,
            'timestamp_ms': timestamp_ms,
            'expected_timestamp_ms': expected_timestamp_ms,
            'timestamp_diff': timestamp_ms - expected_timestamp_ms,
            'is_duplicate': is_duplicate,
            'diff_score': diff_score,
            'timestamp_jump': timestamp_jump,
            'timestamp_gap': timestamp_gap,
        })
        
        prev_frame = gray.copy()
        prev_timestamp_ms = timestamp_ms
        frame_idx += 1
        
        # Progress
        if frame_idx % 10 == 0:
            print(f"Processing frame {frame_idx}/{frame_count}...", end='\r')
    
    # Final duplicate sequence
    if len(current_duplicate_seq) > 0:
        duplicate_sequences.append(current_duplicate_seq)
    
    cap.release()
    
    # Calculate actual duration from timestamps
    if len(frames) > 0:
        actual_duration = frames[-1]['timestamp_ms'] / 1000
    else:
        actual_duration = 0
    
    print(f"\n\n=== ANALYSIS RESULTS ===")
    print(f"  Total Frames: {frame_idx}")
    print(f"  Calculated Duration: {duration:.2f}s (from frame count)")
    print(f"  Actual Duration: {actual_duration:.2f}s (from timestamps)")
    print(f"  Duration Mismatch: {abs(actual_duration - duration):.2f}s")
    print(f"  Duplicate Frames: {duplicate_count} ({duplicate_count/frame_idx*100:.1f}%)")
    print(f"  Unique Frames: {frame_idx - duplicate_count}")
    print(f"  Duplicate Sequences: {len(duplicate_sequences)}")
    print(f"  Timestamp Jumps: {len(timestamp_jumps)}")
    
    # Report timestamp jumps (CRITICAL!)
    if len(timestamp_jumps) > 0:
        print(f"\n!!! CRITICAL: TIMESTAMP JUMPS (MISSING FRAMES) !!!")
        total_missing = 0
        for jump in timestamp_jumps:
            print(f"    Frame {jump['frame']}: {jump['from_ms']/1000:.2f}s -> {jump['to_ms']/1000:.2f}s")
            print(f"       Gap: {jump['gap_seconds']:.2f}s (expected: {jump['expected_gap_ms']:.0f}ms)")
            print(f"       Estimated missing frames: {jump['missing_frames_estimate']}")
            total_missing += jump['missing_frames_estimate']
        print(f"\n    TOTAL ESTIMATED MISSING FRAMES: {total_missing}")
        print(f"    This is why the video appears choppy and jumps in time!")
    
    if len(duplicate_sequences) > 0:
        print(f"\n!!! DUPLICATE FRAME SEQUENCES:")
        for i, seq in enumerate(duplicate_sequences[:10]):  # Show first 10
            start_frame = seq[0] if len(seq) > 0 else 0
            end_frame = seq[-1] if len(seq) > 0 else 0
            start_time = frames[start_frame]['timestamp_ms'] if start_frame < len(frames) else 0
            end_time = frames[end_frame]['timestamp_ms'] if end_frame < len(frames) else 0
            print(f"    Sequence {i+1}: Frames {start_frame}-{end_frame} ({start_time/1000:.2f}s - {end_time/1000:.2f}s), Length: {len(seq)} frames")
        
        if len(duplicate_sequences) > 10:
            print(f"    ... and {len(duplicate_sequences) - 10} more sequences")
    
    # Detect large jumps in diff_score (potential dropped frames)
    print(f"\n=== FRAME DIFFERENCE ANALYSIS ===")
    large_changes = []
    for i in range(1, len(frames)):
        if frames[i]['diff_score'] > 1000:  # Large change
            large_changes.append((i, frames[i]['diff_score']))
    
    if len(large_changes) > 0:
        print(f"  Large frame changes detected: {len(large_changes)}")
        for frame_idx, score in large_changes[:10]:
            timestamp = frames[frame_idx]['timestamp_ms']
            print(f"    Frame {frame_idx} ({timestamp:.0f}ms): diff={score:.1f}")
    else:
        print(f"  No large frame changes detected")
    
    # Calculate average frame difference (excluding duplicates)
    non_dup_diffs = [f['diff_score'] for f in frames if not f['is_duplicate'] and f['diff_score'] > 0]
    if len(non_dup_diffs) > 0:
        avg_diff = np.mean(non_dup_diffs)
        std_diff = np.std(non_dup_diffs)
        print(f"\n=== FRAME DIFFERENCE STATS (non-duplicates) ===")
        print(f"  Average: {avg_diff:.2f}")
        print(f"  Std Dev: {std_diff:.2f}")
        print(f"  Min: {min(non_dup_diffs):.2f}")
        print(f"  Max: {max(non_dup_diffs):.2f}")
    
    # Save detailed report
    report_path = Path(video_path).parent / f"{Path(video_path).stem}_analysis.json"
    with open(report_path, 'w') as f:
        json.dump({
            'video_properties': {
                'width': width,
                'height': height,
                'fps': fps,
                'frame_count': frame_count,
                'duration': duration,
            },
            'analysis': {
                'total_frames': frame_idx,
                'calculated_duration': duration,
                'actual_duration': actual_duration,
                'duration_mismatch': abs(actual_duration - duration),
                'duplicate_frames': duplicate_count,
                'duplicate_percentage': duplicate_count/frame_idx*100,
                'duplicate_sequences': len(duplicate_sequences),
                'timestamp_jumps': len(timestamp_jumps),
            },
            'frames': frames,
            'duplicate_sequences': [[int(x) for x in seq] for seq in duplicate_sequences],
            'timestamp_jumps': timestamp_jumps,
        }, f, indent=2)
    
    print(f"\nDetailed report saved to: {report_path}")
    
    # Summary
    print(f"\n=== SUMMARY ===")
    issues = []
    
    if len(timestamp_jumps) > 0:
        issues.append(f"TIMESTAMP JUMPS: {len(timestamp_jumps)} jumps detected (missing frames!)")
    
    if duplicate_count > 0:
        issues.append(f"DUPLICATE FRAMES: {duplicate_count}/{frame_idx} ({duplicate_count/frame_idx*100:.1f}%)")
    
    if len(issues) > 0:
        print(f"  [X] VIDEO HAS CRITICAL ISSUES:")
        for issue in issues:
            print(f"      - {issue}")
        print(f"\n  ROOT CAUSE:")
        if len(timestamp_jumps) > 0:
            print(f"      Frame buffer is not capturing all frames continuously")
            print(f"      There are gaps in the timeline (frames are being dropped)")
        if duplicate_count > 0:
            print(f"      Same frames are being written multiple times to buffer")
            print(f"      This causes stuttering playback")
    else:
        print(f"  [OK] VIDEO LOOKS GOOD: No issues detected")

if __name__ == "__main__":
    video_path = r"c:\Users\Administrator\OneDrive\Desktop\event-cc0846d0-dfc0-4903-9c8d-73d1e6ebc6b5-timelapse.mp4"
    analyze_video(video_path)
