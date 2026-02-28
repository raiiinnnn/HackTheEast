"""
Reel Producer — lecture clip-based vertical reels.

Takes pipeline output and produces short, engaging clips.
Format is decided per-script at pipeline time (not production time):
- "video": lecture recording with professor's own voice
- "slides-only": PDF slides + AI TTS voiceover
- "character": AI-animated character + slides + TTS voiceover
- "asmr": AI ASMR clip + slides + TTS voiceover

Usage:
    from reel_producer import ReelProducer
    producer = ReelProducer()
    producer.produce_from_file("content_generation/output/pipeline_result.json")
"""

from .producer import ReelProducer, LectureFormat

__all__ = ["ReelProducer", "LectureFormat"]
