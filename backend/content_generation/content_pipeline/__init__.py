"""
Content Pipeline — Analyze lecture videos + slides, segment by topic, generate reel scripts.

Usage:
    from content_pipeline import ContentPipeline
    pipeline = ContentPipeline()
    result = pipeline.run(video_path="lecture.mp4", slides_path="slides.pdf")
    for reel_script in result.reel_scripts:
        print(reel_script)
"""

from .pipeline import ContentPipeline, PipelineResult
from .transcriber import Transcriber, TranscriptSegment
from .slide_analyzer import SlideAnalyzer, SlideContent
from .topic_segmenter import TopicSegmenter, TopicSegment
from .script_generator import ScriptGenerator, ReelScript, VisualDirection
from .llm_client import llm_chat

__all__ = [
    "ContentPipeline",
    "PipelineResult",
    "Transcriber",
    "TranscriptSegment",
    "SlideAnalyzer",
    "SlideContent",
    "TopicSegmenter",
    "TopicSegment",
    "ScriptGenerator",
    "ReelScript",
    "VisualDirection",
    "llm_chat",
]
