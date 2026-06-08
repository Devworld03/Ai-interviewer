"""
Interview Engine Service
=========================
Core logic for:
- Generating personalized interview questions from resume data
- Evaluating candidate responses
- Scoring and feedback generation
- Managing conversation flow
"""

import json
import re
from groq import Groq
from config import GROQ_API_KEY, GROQ_MODEL, MAX_TOKENS, TOTAL_QUESTIONS, QUESTION_MIX, SCORING_WEIGHTS

client = Groq(api_key=GROQ_API_KEY)


SYSTEM_PROMPT = """You are Alex, a professional AI interviewer with 10+ years of experience conducting technical and behavioral interviews at top tech companies. 

Your interviewing style:
- Warm but professional
- Ask one question at a time
- Listen carefully and ask relevant follow-ups
- Probe deeper when answers are vague
- Provide encouragement without giving away answers
- Keep the conversation natural and flowing

You have access to the candidate's resume and will use it to ask personalized, relevant questions."""


def generate_question_bank(resume_data: dict) -> list:
    """Generate a personalized question bank from resume data."""
    
    focus_areas = resume_data.get("interview_focus_areas", [])
    skills = resume_data.get("skills", {}).get("technical", [])
    experience = resume_data.get("experience", [])
    projects = resume_data.get("projects", [])
    
    exp_summary = ""
    for exp in experience[:3]:
        exp_summary += f"\n- {exp.get('role')} at {exp.get('company')}: {', '.join(exp.get('technologies', []))}"
    
    proj_summary = ""
    for proj in projects[:3]:
        proj_summary += f"\n- {proj.get('name')}: {proj.get('description', '')}"

    prompt = f"""
Based on this candidate's resume, generate {TOTAL_QUESTIONS} high-quality interview questions.

Candidate Profile:
- Name: {resume_data.get('name', 'Candidate')}
- Key Skills: {', '.join(skills[:10])}
- Focus Areas: {', '.join(focus_areas)}
- Experience: {exp_summary}
- Projects: {proj_summary}

Generate exactly {TOTAL_QUESTIONS} questions in this mix:
- {QUESTION_MIX['technical']} Technical questions (deep dive into their specific tech stack)
- {QUESTION_MIX['behavioral']} Behavioral questions (STAR format about past experiences)
- {QUESTION_MIX['situational']} Situational questions (hypothetical scenarios)

Return ONLY a JSON array like this:
[
  {{
    "id": 1,
    "type": "technical",
    "question": "question text",
    "focus_area": "what skill/area this tests",
    "ideal_answer_points": ["point1", "point2", "point3"],
    "follow_up": "a natural follow-up question if they answer well"
  }}
]

Make questions SPECIFIC to their resume — reference their actual technologies, projects, and experience.
Return ONLY the JSON array.
"""

    response = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=2000,
        temperature=0.7,
    )

    raw = response.choices[0].message.content.strip()
    raw = re.sub(r"^```json\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)

    try:
        questions = json.loads(raw)
        return questions
    except:
        # Fallback generic questions
        return _fallback_questions(resume_data)


def evaluate_response(
    question: dict,
    candidate_answer: str,
    resume_data: dict,
    conversation_history: list
) -> dict:
    """
    Evaluate a candidate's answer and return:
    - score (0-10)
    - feedback
    - follow_up_question (if needed)
    - should_probe_deeper (bool)
    """

    ideal_points = question.get("ideal_answer_points", [])
    question_type = question.get("type", "general")

    # Build last 3 exchanges from history for context
    recent_history = ""
    if conversation_history:
        recent = conversation_history[-6:]  # last 3 exchanges (user+assistant pairs)
        for msg in recent:
            role = "Interviewer" if msg["role"] == "assistant" else "Candidate"
            recent_history += f"{role}: {msg['content']}\n"

    # STAR enforcement note for behavioral questions
    star_note = ""
    if question_type == "behavioral":
        star_note = """
This is a BEHAVIORAL question. Check if the candidate used the STAR method:
- Situation: Did they set the context?
- Task: Did they explain their responsibility?
- Action: Did they describe specific actions THEY took?
- Result: Did they share a measurable outcome?
If STAR method is missing or incomplete, set probe_deeper=true and ask them to structure their answer better.
"""

    prompt = f"""You are a strict but fair technical interviewer named Alex evaluating a job interview response.

=== CONVERSATION HISTORY (last 3 exchanges) ===
{recent_history if recent_history else "This is the first answer."}

=== CURRENT QUESTION ===
Question: {question['question']}
Question Type: {question_type}
Ideal Answer Should Cover: {', '.join(ideal_points)}

=== CANDIDATE'S ANSWER ===
"{candidate_answer}"

{star_note}

=== EVALUATION RULES (STRICT) ===

1. ANSWER QUALITY GATE:
   - If answer is less than 20 words OR completely irrelevant to the question → set overall_score below 4, set probe_deeper=true
   - If answer says "I don't know", "I haven't done that", or dodges → do NOT just move on. Probe with a simpler version or ask them to reason through it.

2. STT ARTIFACT DETECTION:
   - If the answer contains likely speech-to-text errors (nonsensical words, wrong tech names like "Mac or Lyft" instead of "Matplotlib", "login" instead of "logging") → note it in improvements and ask for clarification in probe_question.

3. PUSHBACK ENFORCEMENT:
   - Do NOT be overly polite and move on from weak answers.
   - If depth score < 5 → probe_deeper must be true.
   - If answer is vague (no specific examples, no metrics, no technical details) → probe_deeper=true.

4. FOLLOW-UP LOGIC:
   - probe_question should be a SPECIFIC follow-up, not generic.
   - Bad: "Can you elaborate?" 
   - Good: "You mentioned using FastAPI — how did you handle authentication in that project?"

5. CONTEXT AWARENESS:
   - Use conversation history above to avoid repeating questions already asked.
   - If candidate already answered a sub-topic, probe a different angle.

Return ONLY a JSON object:
{{
  "scores": {{
    "relevance": <0-10>,
    "depth": <0-10>,
    "communication": <0-10>,
    "confidence": <0-10>
  }},
  "overall_score": <weighted average 0-10>,
  "strengths": ["strength1", "strength2"],
  "improvements": ["improvement1", "improvement2"],
  "interviewer_response": "<2-3 sentence response. If answer is weak, respectfully push back. Do NOT just say 'Great answer!' for poor responses. Sound human and professional.>",
  "probe_deeper": <true/false>,
  "probe_question": "<specific follow-up question, or null if answer was complete>"
}}

Return ONLY the JSON.
"""

    response = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=700,
        temperature=0.3,
    )

    raw = response.choices[0].message.content.strip()
    raw = re.sub(r"^```json\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)

    try:
        return json.loads(raw)
    except:
        return {
            "scores": {"relevance": 5, "depth": 5, "communication": 5, "confidence": 5},
            "overall_score": 5,
            "strengths": ["Provided an answer"],
            "improvements": ["Could elaborate more"],
            "interviewer_response": "Thank you for that response. Could you elaborate a bit more on that?",
            "probe_deeper": True,
            "probe_question": "Can you walk me through a specific example?"
        }

def generate_final_report(
    resume_data: dict,
    qa_history: list,
    all_scores: list
) -> dict:
    """Generate comprehensive interview report with scores and feedback."""

    avg_score = sum(all_scores) / len(all_scores) if all_scores else 0

    # Build QA summary
    qa_summary = ""
    for i, qa in enumerate(qa_history[:10], 1):
        qa_summary += f"\nQ{i}: {qa.get('question', '')}\nA: {qa.get('answer', '')[:200]}\nScore: {qa.get('score', 0)}/10\n"

    prompt = f"""
Generate a comprehensive interview performance report for this candidate.

Candidate: {resume_data.get('name', 'Candidate')}
Average Score: {avg_score:.1f}/10
Total Questions: {len(qa_history)}

Q&A Summary:
{qa_summary}

Return ONLY a JSON object:
{{
  "overall_score": {avg_score:.1f},
  "grade": "<A/B/C/D/F based on score>",
  "hire_recommendation": "<Strong Hire / Hire / Borderline / No Hire>",
  "executive_summary": "<3-4 sentence overall assessment>",
  "top_strengths": ["strength1", "strength2", "strength3"],
  "areas_for_improvement": ["area1", "area2", "area3"],
  "category_scores": {{
    "technical_knowledge": <0-10>,
    "problem_solving": <0-10>,
    "communication": <0-10>,
    "experience_depth": <0-10>,
    "cultural_fit": <0-10>
  }},
  "detailed_feedback": "<detailed paragraph with specific examples from the interview>",
  "next_steps": ["step1", "step2", "step3"],
  "resources_to_study": ["topic1", "topic2", "topic3"]
}}

Return ONLY the JSON.
"""

    response = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=1000,
        temperature=0.2,
    )

    raw = response.choices[0].message.content.strip()
    raw = re.sub(r"^```json\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)

    try:
        return json.loads(raw)
    except:
        return {
            "overall_score": avg_score,
            "grade": "B" if avg_score >= 7 else "C",
            "hire_recommendation": "Hire" if avg_score >= 7 else "Borderline",
            "executive_summary": "The candidate demonstrated reasonable knowledge across the interview topics.",
            "top_strengths": ["Communication", "Technical Knowledge"],
            "areas_for_improvement": ["Depth of answers", "Specific examples"],
            "category_scores": {
                "technical_knowledge": avg_score,
                "problem_solving": avg_score,
                "communication": avg_score,
                "experience_depth": avg_score,
                "cultural_fit": avg_score
            },
            "detailed_feedback": "Overall a satisfactory interview performance.",
            "next_steps": ["Practice STAR method", "Review core concepts"],
            "resources_to_study": ["LeetCode", "System Design", "Behavioral Questions"]
        }


def chat_with_resume(question: str, resume_data: dict, history: list) -> str:
    """
    Free-form Q&A about the resume.
    User can ask anything about their resume; AI answers intelligently.
    """
    resume_context = json.dumps({
        k: v for k, v in resume_data.items() if k != "_raw_text"
    }, indent=2)[:3000]

    messages = [
        {
            "role": "system",
            "content": f"""You are a helpful career advisor who has carefully read this candidate's resume.
Answer questions about the resume honestly and helpfully. If asked about gaps, weaknesses, or improvements, be constructive.

Resume Data:
{resume_context}

Be conversational, specific, and reference actual details from the resume."""
        }
    ]

    # Add conversation history
    for msg in history[-6:]:  # last 3 exchanges
        messages.append(msg)

    messages.append({"role": "user", "content": question})

    response = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=messages,
        max_tokens=500,
        temperature=0.7,
    )

    return response.choices[0].message.content.strip()


def _fallback_questions(resume_data: dict) -> list:
    """Fallback questions if LLM generation fails."""
    name = resume_data.get("name", "Candidate")
    return [
        {"id": 1, "type": "behavioral", "question": "Tell me about yourself and your background.", "focus_area": "Overview", "ideal_answer_points": ["Clear narrative", "Relevant experience"], "follow_up": "What are you most proud of?"},
        {"id": 2, "type": "behavioral", "question": "Describe a challenging project you worked on.", "focus_area": "Problem Solving", "ideal_answer_points": ["STAR format", "Specific challenge", "Clear outcome"], "follow_up": "What would you do differently?"},
        {"id": 3, "type": "technical", "question": "Walk me through your most technically complex project.", "focus_area": "Technical Depth", "ideal_answer_points": ["Architecture", "Technology choices", "Challenges overcome"], "follow_up": "How did you handle scalability?"},
        {"id": 4, "type": "behavioral", "question": "Tell me about a time you had to work with a difficult team member.", "focus_area": "Teamwork", "ideal_answer_points": ["Conflict resolution", "Communication", "Positive outcome"], "follow_up": None},
        {"id": 5, "type": "situational", "question": "How would you handle a production outage affecting thousands of users?", "focus_area": "Incident Management", "ideal_answer_points": ["Prioritization", "Communication", "Root cause analysis"], "follow_up": None},
    ]
