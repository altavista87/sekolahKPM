"""Curriculum mapping for homework categorization."""

import json
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from pathlib import Path


@dataclass
class CurriculumTopic:
    """Curriculum topic."""
    id: str
    name: str
    subject: str
    grade_level: str
    learning_objectives: List[str]
    keywords: List[str]
    parent_topic: Optional[str] = None


class CurriculumMapper:
    """Map homework to curriculum topics."""
    
    # Singapore primary school curriculum (example)
    DEFAULT_CURRICULUM = {
        "mathematics": {
            "primary_1": [
                {"id": "math_p1_numbers", "name": "Numbers to 100", "keywords": ["count", "number", "place value"]},
                {"id": "math_p1_addition", "name": "Addition and Subtraction", "keywords": ["add", "subtract", "sum", "difference"]},
            ],
            "primary_2": [
                {"id": "math_p2_numbers", "name": "Numbers to 1000", "keywords": ["hundreds", "thousands"]},
                {"id": "math_p2_multiplication", "name": "Multiplication", "keywords": ["multiply", "times", "product"]},
            ],
        },
        "english": {
            "primary_1": [
                {"id": "eng_p1_reading", "name": "Reading Comprehension", "keywords": ["read", "comprehension", "passage"]},
                {"id": "eng_p1_writing", "name": "Basic Writing", "keywords": ["write", "sentence", "paragraph"]},
            ],
        },
        "science": {
            "primary_3": [
                {"id": "sci_p3_plants", "name": "Plants", "keywords": ["plant", "leaf", "root", "stem"]},
                {"id": "sci_p3_animals", "name": "Animals", "keywords": ["animal", "habitat", "life cycle"]},
            ],
        },
    }
    
    def __init__(self, curriculum_data: Optional[Dict] = None):
        self.curriculum = curriculum_data or self.DEFAULT_CURRICULUM
        self._build_keyword_index()
    
    def _build_keyword_index(self):
        """Build keyword-to-topic index for fast lookup."""
        self.keyword_index = {}
        
        for subject, grades in self.curriculum.items():
            for grade, topics in grades.items():
                for topic in topics:
                    for keyword in topic.get("keywords", []):
                        if keyword not in self.keyword_index:
                            self.keyword_index[keyword] = []
                        self.keyword_index[keyword].append({
                            "subject": subject,
                            "grade": grade,
                            "topic": topic,
                        })
    
    def map_homework(
        self,
        subject: str,
        title: str,
        description: str,
        keywords: List[str],
    ) -> List[Dict[str, Any]]:
        """Map homework to curriculum topics."""
        matches = []
        
        # Combine all text for analysis
        full_text = f"{subject} {title} {description} {' '.join(keywords)}".lower()
        
        # Check keyword index
        for keyword, topics in self.keyword_index.items():
            if keyword in full_text:
                for topic_info in topics:
                    # Calculate match score
                    score = self._calculate_match_score(
                        full_text, topic_info["topic"]
                    )
                    
                    matches.append({
                        "subject": topic_info["subject"],
                        "grade": topic_info["grade"],
                        "topic_id": topic_info["topic"]["id"],
                        "topic_name": topic_info["topic"]["name"],
                        "match_score": score,
                        "learning_objectives": topic_info["topic"].get("learning_objectives", []),
                    })
        
        # Sort by match score
        matches.sort(key=lambda x: x["match_score"], reverse=True)
        
        # Return top matches
        return matches[:5]
    
    def _calculate_match_score(
        self,
        text: str,
        topic: Dict[str, Any],
    ) -> float:
        """Calculate match score between text and topic."""
        score = 0.0
        
        # Keyword matches
        for keyword in topic.get("keywords", []):
            if keyword in text:
                score += 1.0
        
        # Normalize
        total_keywords = len(topic.get("keywords", []))
        if total_keywords > 0:
            score = score / total_keywords
        
        return score
    
    def get_learning_objectives(
        self,
        topic_id: str,
    ) -> List[str]:
        """Get learning objectives for a topic."""
        for subject, grades in self.curriculum.items():
            for grade, topics in grades.items():
                for topic in topics:
                    if topic["id"] == topic_id:
                        return topic.get("learning_objectives", [])
        return []
    
    def suggest_related_topics(
        self,
        topic_id: str,
    ) -> List[Dict[str, Any]]:
        """Suggest related topics for further study."""
        # Find the topic
        current_topic = None
        current_subject = None
        current_grade = None
        
        for subject, grades in self.curriculum.items():
            for grade, topics in grades.items():
                for topic in topics:
                    if topic["id"] == topic_id:
                        current_topic = topic
                        current_subject = subject
                        current_grade = grade
                        break
        
        if not current_topic:
            return []
        
        # Find related topics (same subject, similar keywords)
        related = []
        for subject, grades in self.curriculum.items():
            if subject != current_subject:
                continue
            for grade, topics in grades.items():
                for topic in topics:
                    if topic["id"] == topic_id:
                        continue
                    # Check keyword overlap
                    overlap = set(topic.get("keywords", [])) & set(current_topic.get("keywords", []))
                    if overlap:
                        related.append({
                            "id": topic["id"],
                            "name": topic["name"],
                            "grade": grade,
                            "common_keywords": list(overlap),
                        })
        
        return related[:3]
    
    def load_curriculum(self, filepath: str):
        """Load curriculum from JSON file."""
        with open(filepath, 'r') as f:
            self.curriculum = json.load(f)
        self._build_keyword_index()
    
    def save_curriculum(self, filepath: str):
        """Save curriculum to JSON file."""
        with open(filepath, 'w') as f:
            json.dump(self.curriculum, f, indent=2)
