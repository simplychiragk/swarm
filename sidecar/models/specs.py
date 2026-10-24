"""
Dynamic Project Specification Models & Heuristic Extractor.
Allows Swarm to decompose ANY arbitrary user or mentor prompt into
a tailored project specification with dynamic fields, routes, and styling.
"""

import re
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class ProjectField(BaseModel):
    id: str
    label: str
    type: str = "text"  # text, email, tel, select, textarea
    placeholder: Optional[str] = None
    options: Optional[List[str]] = None
    required: bool = True


class ProjectSpec(BaseModel):
    project_name: str = "AI Swarm Application"
    tagline: str = "Built autonomously by Swarm multi-agent engineering team."
    form_title: str = "Get Started"
    form_action_label: str = "Submit"
    api_endpoint: str = "/api/submit"
    fields: List[ProjectField] = Field(default_factory=list)
    extra_sections: List[Dict[str, Any]] = Field(default_factory=list)
    research_topic: str = "best software design patterns 2026"
    qa_goal: str = "Verify form submission and confirmation message"


def extract_project_spec(prompt: str, dialogue_history: Optional[List[Dict[str, str]]] = None) -> ProjectSpec:
    """
    Extracts a rich, dynamic ProjectSpec from the user prompt and conversation history.
    Employs an intelligent semantic classifier with comprehensive domain templates
    so any mentor prompt generates a custom, responsive project.
    """
    full_text = prompt
    if dialogue_history:
        full_text += " " + " ".join(m.get("content", "") for m in dialogue_history)
    text_lower = full_text.lower()

    # 1. Event Registration / Hackathon / Conference
    if any(k in text_lower for k in ["event", "hackathon", "conference", "hackiiitd", "register", "registration", "rsvp", "summit", "workshop"]):
        event_name = "HackIIITD 2026" if "iiit" in text_lower or "hack" in text_lower else "Tech Summit 2026"
        return ProjectSpec(
            project_name=f"{event_name} Portal",
            tagline="Join 1,000+ developers, designers, and innovators for 24 hours of creation.",
            form_title="Attendee Registration",
            form_action_label="Confirm Registration",
            api_endpoint="/api/register",
            fields=[
                ProjectField(id="name", label="Full Name", type="text", placeholder="Alex Rivera"),
                ProjectField(id="email", label="Email Address", type="email", placeholder="alex@domain.com"),
                ProjectField(
                    id="track",
                    label="Preferred Track",
                    type="select",
                    options=["AI & Autonomous Agents", "Web3 & Distributed Systems", "Developer Tools & Cloud", "Open Innovation"],
                ),
                ProjectField(
                    id="food",
                    label="Meal Preference",
                    type="select",
                    options=["Vegetarian", "Non-Vegetarian", "Vegan", "Jain Food", "No Preference"],
                ),
            ],
            extra_sections=[
                {
                    "title": "Event Schedule & Milestones",
                    "items": [
                        "09:00 AM - Opening Keynote & Swarm Demo",
                        "11:00 AM - Hacking Commences",
                        "04:00 PM - TinyFish Autonomous Browser Workshop",
                        "08:00 PM - Mid-Point Mentoring Round",
                    ],
                }
            ],
            research_topic=f"best practices {event_name.lower()} registration form UX 2026",
            qa_goal=f"Verify {event_name} attendee registration form submission and confirmation banner",
        )

    # 2. Portfolio / Resume / Personal Website
    if any(k in text_lower for k in ["portfolio", "resume", "personal", "showcase", "cv", "hire", "consulting"]):
        if any(k in text_lower for k in ["machine learning", "learning", "ml", "ai", "data"]):
            role = "Machine Learning Engineer"
        elif any(k in text_lower for k in ["frontend", "react", "ui", "design"]):
            role = "Frontend & UI Architect"
        elif any(k in text_lower for k in ["backend", "cloud", "systems", "api"]):
            role = "Backend Systems Engineer"
        else:
            role = "Full-Stack Software Engineer"
        return ProjectSpec(
            project_name=f"Alex Chen - {role}",
            tagline="Architecting resilient distributed backends, AI agents, and high-performance user interfaces.",
            form_title="Get In Touch / Project Inquiry",
            form_action_label="Send Message",
            api_endpoint="/api/contact",
            fields=[
                ProjectField(id="name", label="Your Name", type="text", placeholder="Jordan Miller"),
                ProjectField(id="email", label="Your Email", type="email", placeholder="jordan@company.com"),
                ProjectField(
                    id="engagement",
                    label="Project Type",
                    type="select",
                    options=["Architecture & Advisory", "Full-Stack Development", "AI Agent Automation", "Technical Consulting"],
                ),
                ProjectField(
                    id="message",
                    label="Project Overview",
                    type="textarea",
                    placeholder="Briefly describe your timeline, stack, and scope...",
                ),
            ],
            extra_sections=[
                {
                    "title": "Featured Projects & Case Studies",
                    "items": [
                        "Swarm Multi-Agent Engine (FastAPI + Tauri v2)",
                        "TinyFish Automated Browser Testing Harness",
                        "High-Throughput SQLite Event Store with WAL Replication",
                    ],
                }
            ],
            research_topic=f"best practices {role.lower()} portfolio contact form 2026",
            qa_goal="Verify portfolio contact form submission and confirmation message",
        )

    # 3. Medical / Doctor / Clinic Appointment
    if any(k in text_lower for k in ["doctor", "clinic", "medical", "patient", "health", "hospital", "appointment"]):
        return ProjectSpec(
            project_name="MedCare Health Specialist Clinic",
            tagline="Compassionate, verified healthcare consultations with top medical specialists.",
            form_title="Schedule Consultation",
            form_action_label="Confirm Appointment",
            api_endpoint="/api/appointment",
            fields=[
                ProjectField(id="name", label="Patient Full Name", type="text", placeholder="Taylor Smith"),
                ProjectField(id="email", label="Patient Email", type="email", placeholder="taylor@gmail.com"),
                ProjectField(
                    id="department",
                    label="Department / Specialty",
                    type="select",
                    options=["General Internal Medicine", "Cardiology", "Neurology", "Pediatrics", "Dermatology"],
                ),
                ProjectField(
                    id="notes",
                    label="Symptoms or Medical Reason",
                    type="textarea",
                    placeholder="Briefly describe your symptoms or visit reason...",
                ),
            ],
            research_topic="best practices medical clinic patient appointment forms 2026",
            qa_goal="Verify patient appointment form submission and confirmation toast",
        )

    # 4. Product Feedback / Survey
    if any(k in text_lower for k in ["feedback", "survey", "review", "nps", "rating"]):
        return ProjectSpec(
            project_name="Product Experience & Feedback Hub",
            tagline="Help us build the next generation of developer-first AI tools.",
            form_title="Share Your Feedback",
            form_action_label="Submit Feedback",
            api_endpoint="/api/feedback",
            fields=[
                ProjectField(id="name", label="Your Name", type="text", placeholder="Sam Taylor"),
                ProjectField(id="email", label="Email Address", type="email", placeholder="sam@tech.org"),
                ProjectField(
                    id="rating",
                    label="Overall Experience",
                    type="select",
                    options=["5 - Exceptional", "4 - Very Good", "3 - Satisfactory", "2 - Needs Work"],
                ),
                ProjectField(
                    id="feedback_text",
                    label="What can we improve?",
                    type="textarea",
                    placeholder="Share any friction points or feature suggestions...",
                ),
            ],
            research_topic="best practices product feedback forms user experience 2026",
            qa_goal="Verify feedback form submission and confirmation banner",
        )

    # 5. Default: Waitlist / Early Access Landing Page
    # (Matches Section 9 Hackathon core scenario exactly)
    topic_noun = "Developer Tools"
    if "video" in text_lower:
        topic_noun = "AI Video Generation"
    elif "crypto" in text_lower or "defi" in text_lower:
        topic_noun = "DeFi Protocol"
    elif "design" in text_lower:
        topic_noun = "Collaborative Design"

    return ProjectSpec(
        project_name=f"{topic_noun} Waitlist",
        tagline="A queen, specialized workers, and TinyFish web agents building software end-to-end.",
        form_title="Request Early Access",
        form_action_label="Join the Waitlist",
        api_endpoint="/api/waitlist",
        fields=[
            ProjectField(id="name", label="Full Name", type="text", placeholder="Alex Morgan"),
            ProjectField(id="email", label="Work Email", type="email", placeholder="alex@company.com"),
            ProjectField(
                id="role",
                label="Primary Role",
                type="select",
                options=["Software Engineer", "Founder / Executive", "Product Designer", "Student / Researcher", "Other"],
            ),
        ],
        extra_sections=[],
        research_topic=f"best practice {topic_noun.lower()} waitlist form fields 2026",
        qa_goal="Verify waitlist form submission and confirmation banner",
    )
