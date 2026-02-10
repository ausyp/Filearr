import ffmpeg
import re

def get_quality_score(path):
    score = 0
    try:
        probe = ffmpeg.probe(path)
        video_stream = next((stream for stream in probe['streams'] if stream['codec_type'] == 'video'), None)
        audio_stream = next((stream for stream in probe['streams'] if stream['codec_type'] == 'audio'), None)

        if not video_stream:
            return 0
            
        width = int(video_stream.get('width', 0))
        height = int(video_stream.get('height', 0))
        codec = video_stream.get('codec_name', '').lower()
        bitrate = int(video_stream.get('bit_rate', 0) or probe['format'].get('bit_rate', 0))

        # Resolution Scoring (35%)
        if width >= 3840 or height >= 2160: # 4K
            score += 35
        elif width >= 1920 or height >= 1080: # 1080p
            score += 25
        elif width >= 1280 or height >= 720: # 720p
            score += 15
        else:
            score += 5

        # Codec Scoring (20%)
        if 'hevc' in codec or 'h265' in codec or 'av1' in codec:
            score += 20
        elif 'h264' in codec or 'avc' in codec:
            score += 15
        else:
            score += 5

        # Audio Scoring (20%)
        if audio_stream:
            audio_codec = audio_stream.get('codec_name', '').lower()
            channels = int(audio_stream.get('channels', 0))
            
            if 'dts' in audio_codec or 'truehd' in audio_codec or 'eac3' in audio_codec:
                 score += 20
            elif 'ac3' in audio_codec or 'aac' in audio_codec:
                score += 15
            else:
                score += 5
            
            if channels >= 6: # 5.1 or better
                score += 5 # Bonus

        # Bitrate Scoring (15%)
        # Simple heuristic: Higher implies better quality usually
        if bitrate > 15000000: # > 15 Mbps
             score += 15
        elif bitrate > 8000000: # > 8 Mbps
             score += 10
        elif bitrate > 2000000: # > 2 Mbps
             score += 5

        # HDR Detection (10%)
        # Check for HDR keywords in filename or metadata (simplified here)
        # In robust implementation, we check color space metadata
        
    except Exception as e:
        print(f"Error checking quality for {path}: {e}")
        return 0
        
    return min(score, 100)
