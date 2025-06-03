from fastapi import FastAPI, UploadFile, File
from fastapi.responses import JSONResponse, StreamingResponse
import spacy
import random
from io import BytesIO, StringIO
import zipfile

app = FastAPI()
nlp = spacy.load("en_core_web_sm")

def generate_questions(text):
    doc = nlp(text)
    questions = []

    for sent in doc.sents:
        entities = [ent for ent in sent.ents if ent.label_ in ("PERSON", "ORG", "GPE", "DATE", "NORP")]
        if entities:
            entity = random.choice(entities)
            question_text = sent.text.replace(entity.text, "_")
            distractors = get_distractors(entity.text, entity.label_)
            options = distractors + [entity.text]
            random.shuffle(options)
            questions.append({
                "question": question_text,
                "options": options,
                "answer": entity.text
            })
        if len(questions) >= 5:
            break

    return questions

def get_distractors(correct_answer, entity_label):
    fake_entities = {
        "PERSON": ["John Smith", "Alice", "Elon Musk", "Marie Curie"],
        "ORG": ["Google", "Microsoft", "OpenAI", "NASA"],
        "GPE": ["India", "Germany", "France", "Canada"],
        "DATE": ["1990", "2001", "1776", "2020"],
        "NORP": ["Americans", "Europeans", "Asians", "Christians"]
    }

    choices = fake_entities.get(entity_label, [])
    distractors = [choice for choice in choices if choice != correct_answer]
    return random.sample(distractors, min(3, len(distractors)))

def format_questions_text(questions):
    lines = []
    for i, q in enumerate(questions, start=1):
        lines.append(f"Q{i}. {q['question']}")
        for opt in q["options"]:
            lines.append(f" - {opt}")
        lines.append("")
    return "\n".join(lines)

def format_answers_text(questions):
    lines = []
    for i, q in enumerate(questions, start=1):
        lines.append(f"Q{i}. {q['answer']}")
    return "\n".join(lines)

@app.post("/download-quiz/")
async def download_quiz_files(file: UploadFile = File(...)):
    try:
        content = await file.read()
        text = content.decode("utf-8")
        questions = generate_questions(text)

        if not questions:
            return JSONResponse(status_code=400, content={"error": "No quiz questions could be generated."})

        # Prepare text content
        quiz_text = format_questions_text(questions)
        answers_text = format_answers_text(questions)

        # Create in-memory zip archive
        zip_buffer = BytesIO()
        with zipfile.ZipFile(zip_buffer, "w") as zip_file:
            zip_file.writestr("quiz_questions.txt", quiz_text)
            zip_file.writestr("quiz_answers.txt", answers_text)

        zip_buffer.seek(0)

        return StreamingResponse(
            zip_buffer,
            media_type="application/zip",
            headers={"Content-Disposition": "attachment; filename=quiz_files.zip"}
        )

    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})
