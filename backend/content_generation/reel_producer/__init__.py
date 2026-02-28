"""
Reel Producer — lecture clip-based vertical reels.

Takes pipeline output and cuts the lecture into short, engaging clips.
The professor's own voice is always the audio. Visual layout adapts to the
lecture format (zoom screenshare, classroom + slides, classroom only).

Usage:
    from reel_producer import ReelProducer
    producer = ReelProducer(lecture_format="zoom")
    producer.produce_from_file("content_generation/output/pipeline_result.json")
"""

from .producer import ReelProducer, LectureFormat

__all__ = ["ReelProducer", "LectureFormat"]
