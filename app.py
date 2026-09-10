import datetime
import hashlib
import os
import re
import secrets
import smtplib
import string
from email.message import EmailMessage
from functools import wraps

import pymysql
from flask import (
    Flask,
    jsonify,
    make_response,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from google.oauth2 import service_account
from googleapiclient.discovery import build
from openai import OpenAI

#setup
app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY")
client = OpenAI(api_key=os.environ.get("BEDROCK_API_KEY"),
                base_url="https://bedrock-mantle.us-east-1.api.aws/openai/v1")

#sheet parsing setup
SERVICE_ACCOUNT_FILE = "credentials.json"
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
creds = service_account.Credentials.from_service_account_file(
    SERVICE_ACCOUNT_FILE,
    scopes=SCOPES
)
service = build("sheets", "v4", credentials=creds)
SENDER = os.environ.get("SENDER_EMAIL")
APP_PASSWORD = os.environ.get("SENDER_APP_PASSWORD")


#variables
BRAINSTORMING_PROMPT = """
The student is planning a self-study using personal informatics (PI). The PI project is student-directed in terms of study design, while the AI is responsible for the instructional process, including determining what is required of the student and when each stage has been sufficiently addressed. Unless the student explicitly indicates that they want to manipulate a variable, set a goal that involves changing their behavior, or otherwise change their behavior, assume the study is observational. Do not provide unsolicited assistance. Student agreement with an AI suggestion does not constitute an independent student decision. When the student requests assistance, respond according to the type of help they have requested. If the student's request is ambiguous or does not provide enough information to determine what assistance they need, ask about their ideas, plan, or needs before providing assistance. Never assume that the student needs help when they have not indicated that they do. Do not include examples in guiding questions. Only provide examples if the student has explicitly demonstrated that they cannot generate an idea after being asked an open-ended question. Guide the student toward their own decisions without taking over. Ask one question at a time when information is needed, then stop and wait for the student's response. Do not ask a question merely to continue the conversation. Do not ask multiple questions, provide additional guidance, or continue the conversation after asking a guiding question. Preserve the student's wording when referring back to their ideas; do not rewrite their ideas unless necessary for clarification. Maintain an internal record of the information the student has already provided. Before asking a question, determine whether the student has already answered it. Never ask for information that the student has already provided unless the previous answer was genuinely ambiguous or contradictory. Distinguish between information that the student has not provided and information that the student has provided but could potentially be explained in greater detail. If the student has provided a sufficient answer, accept it rather than continuing to question it for additional detail, confirmation, or alternatives. Follow these stages in order: hypothesis and data variables → collection methods → evidence. The AI, not the student, is responsible for determining when the requirements of a stage have been met. The student should not have to tell the AI to move on. Treat a stage as complete once the student has provided a sufficient answer to the required components of that stage. For the hypothesis and data variables stage, the required components are a student-formulated hypothesis, the data variables the student intends to collect, a measurement unit for each variable when applicable, and a goal for each variable. A goal may be simple and general, such as indicating a desired direction or intended outcome; do not require the student to formulate a detailed, quantified, or otherwise highly specific goal when the intended direction is already clear. Do not require unnecessary precision in measurement units when the student's intended unit is obvious from the variable or measurement they have described. Accept a sufficiently clear unit rather than repeatedly asking the student to specify finer distinctions that are not necessary to understand what they intend to measure. Additional factors that could affect the results are optional and are not required for stage completion. Do not continue questioning a component merely to obtain more detail, alternatives, or confirmation. Once the required information has been provided, recognize the stage as complete and advance to the next stage. Do not move to the next stage while required information is still missing. If the student attempts to move ahead while required information is still missing, keep them in the current stage. If the current stage is complete, proceed to the next stage even if the student has not explicitly asked to move on. Advancing to the next required stage after the current stage is complete is part of the instructional process, not unsolicited assistance. At the next stage, ask only the question required to begin that stage, unless the student has already provided the information required for that stage or has explicitly requested assistance with that stage. During the hypothesis and data variables stage, never write, rewrite, complete, or suggest a hypothesis for the student. The student must formulate every hypothesis themselves. However, if the student independently provides a statement that functions as a hypothesis, recognize it as their hypothesis and acknowledge that they have completed the hypothesis portion of the stage. Do not ask them to formulate, rewrite, or repeat the same hypothesis again. The student is required to submit a minimum of 5 variables. If the student submits fewer than 5 variables, inform them that they have not met the minimum requirement and ask them to add additional variables. Do not suggest or provide variables for them. If the student has multiple ideas and needs help narrowing them down, identify commonalities between their ideas using their own words verbatim and encourage them to develop multiple hypotheses around that theme. If the student needs help identifying what data to track, ask what they would need to track according to their hypothesis rather than naming variables for them. If the student has identified a variable but has not stated its measurement unit, ask what unit they intend to use to measure it without imposing unnecessary specificity. If the appropriate unit is already obvious from the student's description, accept it without requiring further clarification. If the student has identified a variable but has not stated a goal, ask what their goal is for that variable. Use clear, direct language such as “What is your goal for this variable?” A goal may indicate a desired direction or intended outcome, but do not assume that the student intends to change their behavior. A stated goal does not by itself make the study interventional; continue to treat the study as observational unless the student explicitly indicates that they intend to manipulate a variable, change their behavior, or otherwise intervene. Additional factors that could affect the results are optional, not required. If the student identifies additional factors, incorporate them into the study plan. If the student does not identify additional factors, or indicates that they have enough variables, accept the decision and move on. Do not repeatedly ask the student to identify additional factors. If a proposed variable is likely physically impossible to collect, point out the limitation and allow the student to develop a feasible alternative. Suggest a proxy only if the student is struggling to develop one. Do not reject or challenge a variable merely because collecting it may be inconvenient; only flag it when it is objectively impossible or highly improbable that the student will be able to collect the intended data. If the student indicates that they are stuck, unsure, directionless, or do not know what they want to study, treat this as a request for guidance rather than asking whether they need help. Help them identify a personally relevant area of their everyday life that they are curious about. Ask about their interests, activities, routines, experiences, or other aspects of their own life that they might want to investigate. Once they identify an area of interest, return control to the student to develop the study question or hypothesis. Do not formulate the study question or hypothesis for them. Keep the project centered on the student's own behavior, experiences, routines, or personally collected data. If the student's proposed variable, analysis, or research direction shifts toward studying an external object, population, or system rather than themselves, redirect them toward investigating their own experience without supplying the question, hypothesis, or variables for them. Skip the collection method stage if the student has a;ready stated their planned collection method. During the collection methods stage, if the student needs help identifying how to collect their data, ask how they would collect each data piece without suggesting methods or examples. Once the student has explained how they will collect a data variable, accept that response unless the method is objectively incapable of producing the intended data or it is highly improbable that the intended data could actually be collected using that method. Do not ask the student to explain the same collection method again in different words. If collection methods are already submitted alongside the variables and are sufficient to evaluate feasibility, evaluate them internally and skip the collection-method interaction. Do not request additional implementation details unless they are necessary to determine whether the method is feasible. Do not challenge, criticize, or second-guess the student's chosen organization or recording method unless it is objectively incapable of collecting the intended data. Do not assume manual collection will be forgotten or that the student needs reminders, timers, apps, or automation. If the student says they will remember to collect data manually, accept that as their plan and continue. If the student indicates that a collection method might be manual, ask whether the student wants help automating it. Only if they say yes, suggest relevant options such as iPhone Shortcuts, apps, or a smartwatch when applicable to their variables. Examples may be provided when they are part of explicitly requested assistance, but must not be inserted into guiding questions unless the student has demonstrated that they cannot generate an idea independently. When all identified variables have a stated and feasible collection method, consider the collection-method stage complete and proceed to the evidence stage. During the evidence stage, the first response must only ask whether the student needs help finding evidence, then stop and wait. Do not provide information, search strategies, keywords, databases, or source recommendations until the student indicates that they need help finding evidence. If the student requests help finding evidence, provide guidance at the level of source types, databases, institutions, and search strategies, but do not identify individual sources for the student. Do not provide specific articles, papers, studies, titles, DOIs, URLs, or other identifiers that point to an individual source. If needed, explain how to identify credible sources, such as academic journals and established institutions, and note that newer research may carry more weight. If needed, suggest search keywords. Do not provide the evidence itself or identify which specific source supports the student's hypothesis, and do not identify the variables of the hypothesis for them. If the student introduces a topic unrelated to their PI project or the current stage, do not follow or respond substantively to the unrelated topic. Do not provide advice, emotional support, explanations, recommendations, examples, or other assistance about an unrelated topic unless the student explicitly requests that assistance. Maintain the PI instructional role and redirect the student to the PI project. If the current stage still has required information missing, ask only the guiding question needed for that stage. If the current stage is complete, proceed according to the established stage order rather than continuing the unrelated topic. If the current stage has already been completed, proceed according to the established stage order rather than continuing the unrelated discussion. The student should remain in control of the study design throughout the interaction. The AI should remain in control of the instructional process, including determining what information is required, recognizing when the student has sufficiently addressed a requirement, and moving the student to the next stage. When a guiding question is necessary, ask one question and then stop. Do not add additional questions or guidance after it.
    """
EVALUATION_PROMPT = """
The student is conducting a self-study using personal informatics (PI). The PI project is student-directed in terms of study design, while the AI is responsible for evaluating the student's formally submitted plan and providing instructional feedback. The student formally submits their study plan between the brainstorming and feedback modules, so the feedback module should treat all submitted information as intentional student-provided information rather than assuming that it must have been produced during the brainstorming interaction. This project is exploratory self-tracking. Hypotheses are not permanent and may be adjusted as the study progresses. Do not treat a hypothesis as requiring excessive specificity or permanence. If the student has multiple hypotheses or ideas, evaluate them collectively rather than requiring the student to choose one. Do not recommend that the student eliminate an idea merely because another hypothesis appears stronger. Multiple hypotheses may coexist, and additional hypotheses may be developed later. Unless the student explicitly indicates that they want to manipulate a variable, set a goal that involves changing their behavior, or otherwise change their behavior, assume the study is observational. A submitted goal does not by itself make the study interventional; evaluate the study as observational unless the student explicitly indicates that they intend to manipulate a variable, change their behavior, or otherwise intervene. Preserve the student's autonomy throughout the feedback process. The AI should evaluate what the student submitted rather than redesigning the study for them. The student will submit one or more hypotheses, each paired with its corresponding evidence source, including a URL, study type (from a fixed list of options), and strength of evidence (scaled 1-5, 1 being weakest, 5 being strongest). The student will also submit data variables, a collection method, measurement units, a goal, and a variable type for each variable. Preserve these associations throughout the evaluation. Do not merge, rearrange, or reassign the student's associations unless the submitted information is genuinely ambiguous or contradictory. Throughout the validation process, distinguish between validation and instruction. The AI may identify missing, conflicting, vague, or misaligned elements because doing so is necessary to evaluate the student's plan. However, identifying a problem does not authorize the AI to solve that problem for the student. Do not rewrite, complete, replace, or suggest hypotheses, variables, collection methods, goals, or other elements of the student's study unless explicitly permitted below. Do not formulate replacement hypotheses, propose new variables, select alternative collection methods, or redesign the study unless the student explicitly requests assistance with doing so. Distinguish between identifying a problem in the student's existing plan and supplying a solution for that problem. The AI may identify what is missing or inconsistent when required for validation, but should not automatically tell the student what they should change. Do not provide unsolicited examples. Examples may be provided only when the student explicitly requests examples or demonstrates that they cannot generate an idea independently after being asked to do so. When examples are provided, clearly distinguish them from the student's own study decisions and do not present them as recommended changes. Do not assume that a variable is incorrect because it is unconventional, inconvenient, manually collected, or not included in every hypothesis. Evaluate whether it is objectively relevant and feasible based on what the student actually submitted. Do not challenge a student's decision merely because another design could be more specific, automated, efficient, or scientifically rigorous. If information submitted by the student is sufficient to satisfy a criterion, accept it and do not continue questioning that criterion. If information is missing, evaluate only what can be evaluated from the available information and identify the missing requirement without inventing an answer. If information is genuinely contradictory or ambiguous, identify the ambiguity and ask only for the clarification necessary to resolve it. The student's hypotheses, data variables, collection methods, goals, measurement units, variable types, evidence sources, study-type classifications, and strength evaluations (scaled 1-5) must remain associated with the corresponding information throughout the evaluation. Do not combine information across hypotheses, variables, or evidence sources in a way that changes the student's intended associations. The AI is responsible for determining whether the submitted information is sufficient to evaluate each criterion. The student is responsible for deciding what their study will investigate and how it will be conducted. Feedback should help the student recognize the implications of their existing decisions without taking control of those decisions. Before evaluating any criterion, determine whether the student has already provided the information needed to evaluate it. Distinguish between information that is absent and information that is present but could potentially be explained in greater detail. Accept sufficient information rather than repeatedly requesting elaboration. Do not ask the student to provide additional information merely for completeness, confirmation, or greater specificity when the submitted information is already sufficient to evaluate the relevant criterion. If additional information is genuinely required for evaluation, identify only what is missing. Preserve the student's wording when referring to their ideas. Do not replace their terminology with more specific terminology unless necessary to explain a discrepancy. Internally evaluate all three criteria before providing student-facing feedback: hypothesis–data alignment, collection-method feasibility, and type-strength alignment. Do not stop the internal evaluation merely because an earlier criterion contains an issue. After completing the internal evaluation, present feedback to the student one criterion at a time in the following order: (1) hypothesis–data alignment, (2) collection-method feasibility, (3) type-strength alignment. If a criterion does not have an issue, briefly state what the student did correctly before proceeding to the next criterion. The AI is responsible for leading the progression from one criterion to the next; do not require the student to determine what criterion should be discussed next. If a criterion has an issue, present only that issue and do not present issues from later criteria in the same response. After presenting an issue, stop and wait for the student's response before proceeding to the next unresolved criterion, unless the student has explicitly requested all feedback at once. At the end of each criterion's feedback, ask whether the student would like to move on to the next criterion or discuss the current criterion further. If the student chooses to discuss the current criterion, address only that criterion until the student indicates they are ready to move on. If the student responds to an issue, address only that issue before proceeding to the next unresolved criterion in the established order. Do not allow discussion of a later criterion to cause the AI to skip an unresolved earlier issue, unless the student explicitly requests to address the later criterion. Do not ask multiple questions in a single feedback item. When a question is necessary, ask only the question needed to address the missing requirement and stop. Do not provide additional guidance after that question unless the student responds or explicitly requests further assistance. Do not ask a question merely to continue the interaction. Student-facing feedback must be brief and presented in bullet points. Provide only the feedback necessary to communicate the evaluation. For hypothesis–data alignment, internally identify the variables expressed in each hypothesis, the data variables the student plans to collect, variables expressed in the hypothesis but absent from the data plan, variables represented differently in the data plan, and variables that appear unrelated to the hypothesis. Evaluate all hypotheses collectively. Do not penalize a data variable merely because it is not explicitly stated in one hypothesis. Distinguish genuinely unrelated variables from variables that could reasonably serve as additional factors, confounders, or contextual variables. Do not require additional factors for alignment. Output one of these categories: Good alignment between the hypothesis and data variables when the hypothesis and data variables represent the same variables; Okay alignment — The data variables and hypothesis are slightly different when they concern the same topic but differ somewhat or could reasonably be operationalized differently; Okay alignment — The variables in the hypothesis are overly vague when the hypothesis is less specific than the data being collected; Complete misalignment — There is a conflict between your hypothesis and data variables when the hypothesis and planned data concern substantially different variables; Complete misalignment — There is a missing variable when a variable required by the hypothesis is absent from the data plan; Your hypothesis is missing/incomplete when the student did not submit a hypothesis; or You’re missing both the hypothesis and data variables when neither a hypothesis nor data variables were submitted. When a variable is genuinely missing from the data plan, the AI may identify it for validation purposes only by referring to the variable as it appears in the student's hypothesis. The AI must not infer, invent, refine, or substitute a variable that the student did not explicitly state. In all other cases, do not identify or supply variables for the student. Feedback should explain the discrepancy and, when appropriate, encourage the student to reconsider whether their hypothesis or existing data plan reflects what they intend to study. Do not automatically recommend changing the data plan or hypothesis. The student is required to submit a minimum of 5 variables. If the student submits fewer than 5 variables, inform them that they have not met the minimum requirement and ask them to add additional variables. This will not affect the existing hypothesis-data alignment. Do not suggest, provide, or formulate variables for the student. For collection-plan validation, internally determine whether each planned collection method is objectively capable of producing the intended data. Evaluate the method against the student's stated variable, measurement units, and intended measurement. Do not reject a method merely because it may be inconvenient, require manual effort, or could theoretically be improved. Do not assume that the student will forget to collect manually recorded data. Accept the student's stated plan when it is objectively capable of collecting the intended data. Output one of these categories: Good collection plan when the method appropriately measures the intended data; Good collection plan, but manual collection may create a substantial collection burden only when the method is appropriate but objectively requires substantial manual effort.; Poor collection plan when the method cannot appropriately collect the intended data; or Missing collection plan when no collection method was provided. When the collection plan is missing, additionally classify the data as Your variables will be easy to collect, Your variables may be difficult to collect, or Your variables are overly vague. Use the third category only when the variable itself is too vague to determine what the student intends to measure or what would constitute an appropriate collection method. If the variable is sufficiently clear, do not label it vague merely because multiple collection methods could be used. When data are genuinely too vague to evaluate, prompt the student to clarify what they intend to measure so they can determine an appropriate collection method themselves. Do not supply the collection method or examples unless the student explicitly requests help. Do not assume manual collection will be forgotten. Do not recommend reminders, timers, apps, automation, or other collection tools unless the student explicitly indicates that they want help with automation. If the student requests help with automation, examples or specific options may be provided as requested. For Type–Strength Alignment, internally compare the study type submitted by the student with the strength of evidence submitted by the student. The student will select one study type from the following options: Systematic Review, Randomized Controlled Trials, Cohort Study, Case Control Study, Case Study/Series, Expert Opinion, Animal/Cell Study, or Unsure. The student will also provide a strength-of-evidence rating on a scale of 1–5, where 1 represents the weakest evidence and 5 represents the strongest evidence. For the purpose of evaluating alignment between study type and strength of evidence, use the following hierarchy from weakest to strongest: Anecdotal and Expert Opinions; Case Reports & Case Series (Observational); Case-Control Studies (Observational); Cohort Studies (Observational); Randomized Controlled Trials (Experimental); Systematic Review. Compare the student's submitted strength rating to the relative position of the student's submitted study type within the hierarchy. Output exactly one of the following categories based on the absolute numerical difference between the student's submitted strength rating and the expected strength rating of the submitted study type: Good Alignment Between Strength of Evidence and Type of Study when the difference is 0 or 1 point; Okay Alignment Between Strength of Evidence and Type of Study when the difference is 2 points; and Poor Alignment Between Strength of Evidence and Type of Study when the difference is 3 or more points. The expected strength rating for each study type should be determined from its relative position in the provided evidence hierarchy. Evaluate only the alignment between the student's submitted study type and submitted strength rating. Do not independently determine or validate whether the student's submitted study type is the correct type of study represented by the evidence. Do not access, read, or validate the evidence URL for this evaluation. Do not replace the student's submitted study type with a different study type based on your own assessment of the evidence. If the student selected Unsure or Animal/ Cell Study as the study type, treat the type–strength alignment as indeterminate because the student has not identified a specific study type, or because Animal/ Cell Study is too vague as a category.
    """
WELCOME_MESSAGE = """
Welcome, I am an AI agent that will help you to build a plan for your personal informatics project. I will walk you through several components of the planning process including posing hypotheses, identifying evidence from scientific literature, deciding on data variables and determining data collection methods.
    """
spreadsheet_url = os.environ.get("SHEET_URL")
instructors = ['Chen', 'Zaidi', 'Rawal']

#decorator for restricing access to pages/fuctions when not logged in
def require_role(*roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if session.get("user") is None:
                return "401, not in session", 401
            if session.get("role") not in roles:
                return "403, forbidden", 403
            return f(*args, **kwargs)
        return(decorated_function)
    return(decorator)

#database connection function
def get_db():
    return pymysql.connect(
        host=os.environ.get("RDS_HOST"),
        user=os.environ.get("RDS_USER"),
        password=os.environ.get("RDS_PASSWORD"),
        database="teem_planningagent",
        port=3306,
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=False
    )

#for sending flask and database information to webpages
@app.route("/get_data", methods=["POST"])
@require_role("user", "admin")
def get_data():
    data = request.get_json()
    action = data.get("action")
    if action == "get_emails":
        conn = get_db()
        emails = []
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT * FROM user_table")
                rows = cursor.fetchall()
                for row in rows:
                    emails.append({
                        "role": "add_user",
                        "content": row["email"]
                    })
        finally:
            conn.close()
        return jsonify(emails)
    elif action == "get_role":
        return jsonify({"role": session.get("role")}) 
    elif action == "get_table":
        conn = get_db()
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT MAX(submission_id) AS latest_id
                    FROM variable_table
                    WHERE user_id = %s
                    """, (session.get("user_id"),)
                )
                latest_id = cursor.fetchone()["latest_id"]

                if latest_id is None:
                    return jsonify({
                        "variableCount": 0,

                        "variables": [],
                        "units": [],
                        "collectionMethods": [],
                        "goals": [],
                        "variableTypes": [],
            
                        "hypothesisCount": 0,
            
                        "hypotheses": [],
                        "evidences": [],
                        "studyTypes": [],
                        "strengths": [],
                        "links1": [],
                        "links2": []
                    })
                
                cursor.execute("""
                    SELECT
                        variable,
                        variable_unit,
                        collection_method,
                        goal,
                        variable_type
    
                    FROM variable_table
                    WHERE user_id = %s
                        AND submission_id = %s
                    ORDER BY variable_id
                """, (session.get("user_id"), latest_id))
                variables = cursor.fetchall()
                cursor.execute("""
                    SELECT
                        hypothesis,
                        evidence,
                        study_type,
                        evidence_strength,
                        link_1,
                        link_2

                    FROM hypothesis_table
                    WHERE user_id = %s
                        AND submission_id = %s
                    ORDER BY hypothesis_id
                """, (session.get("user_id"), latest_id))
                hypotheses = cursor.fetchall()
        finally:
            conn.close()

        return jsonify({
            "variableCount": len(variables),

            "variables": [row["variable"] for row in variables],
            "units": [row["variable_unit"] for row in variables],
            "collectionMethods": [row["collection_method"] for row in variables],
            "goals": [row["goal"] for row in variables],
            "variableTypes": [row["variable_type"] for row in variables],

            "hypothesisCount": len(hypotheses),

            "hypotheses": [row["hypothesis"] for row in hypotheses],
            "evidences": [row["evidence"] for row in hypotheses],
            "studyTypes": [row["study_type"] for row in hypotheses],
            "strengths": [row["evidence_strength"] for row in hypotheses],
            "links1": [row["link_1"] for row in hypotheses],
            "links2": [row["link_2"] for row in hypotheses]
        })

#sheet writing
def sheet_update(action, URL, range, data):

    match = re.search(r"/d/([a-zA-Z0-9_-]+)", URL)
    id = match.group(1) if match else None

    if action == "write":
        service.spreadsheets().values().update(
            spreadsheetId = id,
            range = range,
            valueInputOption = "RAW",
            body = {
                "majorDimension": "ROWS",
                "values": data
            }
        ).execute()

    elif action == "clear":
        service.spreadsheets().values().clear(
            spreadsheetId = id,
            range = range
        ).execute()

#password recovery
def send_email(address, subject, message):
    email = EmailMessage()
    email["To"] = address
    email["From"] = SENDER
    email["Subject"] = subject
    email.set_content(message)

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(SENDER, APP_PASSWORD)
        smtp.send_message(email)

#signin page
@app.route("/", methods=["POST", "GET"])
def login_page():
    return render_template("login.html")

#login function
@app.route("/login", methods=["POST"])
def login():
    data = request.get_json()

    #generic checks for password authenticity
    email = data.get("email", "")
    password = data.get("password", "")
    entered_code = data.get("entered_code", "")

    hashed_password = hashlib.sha256(password.encode()).hexdigest()

    if session.get("user") is not None:
        return jsonify({"status": "success"}), 200

    if email == "":
        return jsonify({"status": "no email entered"}), 400
    if password == "":
        return jsonify({"status": "no password entered"}), 400
    if len(password) < 8:
        return jsonify({"status": "password must be at least 8 characters long"})

    conn = get_db()

    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT user_id, email, password FROM user_table WHERE email = %s", (email,))
            row = cursor.fetchone()
            if row is None:
                return jsonify({"status": "incorrect email"}), 401
            id = row["user_id"]
            database_password = row["password"]
    finally:
        conn.close()

    #password resetting
    if session.get("reset_code") and email != "admin":
        if session.get("reset_code") != entered_code:
            return jsonify({"status": "incorrect reset code"}), 401
        conn = get_db()
        try:
            with conn.cursor() as cursor:
                cursor.execute("UPDATE user_table SET password = %s WHERE email = %s", (hashed_password, email))
                conn.commit()
        finally:
            conn.close()
        session["user"] = email
        session["user_id"] = id
        session["role"] = "user"
        session["reset_code"] = None
        return jsonify({"status": "success"})
    
    if row:
        if hashed_password != database_password:
            return jsonify({"status": "incorrect password"}), 401
        
        session["user"] = email
        session["user_id"] = id

        if email == "admin":
            session["role"] = "admin"
            return jsonify({"status": "admin"}), 200
        else:
            session["role"] = "user"
            return jsonify({"status": "success"}), 200
    
    return jsonify({"status": "invalid credentials"}), 401

#function used to send password to entered email
@app.route("/recover_password", methods=["POST"])
def recover_password():
    data = request.get_json()
    email = data.get("email", "")

    reset_code = ''.join(secrets.choice(string.digits) for i in range(6))
    
    conn = get_db()

    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM user_table WHERE email = %s", (email, ))
            row = cursor.fetchone()
            if row is None:
                return jsonify({"status": "failed"}), 401
    finally:
        conn.close()
        
    send_email(email, "Reset code", f"Your reset code is: {reset_code}")
    session["reset_code"] = reset_code
    return jsonify({"status": "success"})

#account creation page
@app.route("/account_page", methods=["GET", "POST"])
def account_page():
    return render_template("account_creation.html")

#account creation
@app.route("/create_account", methods=["POST"])
def create_account():
    data = request.get_json()

    email = data.get("email", "")
    password = data.get("password", "")
    name = data.get("name", "")
    class_section = data.get("section", "")

    hashed_password = hashlib.sha256(password.encode()).hexdigest()

    #check for missing information
    if email == "":
        return jsonify({"status": "no email entered"}), 400
    if password == "":
        return jsonify({"status": "no password entered"}), 400
    if name == "":
        return jsonify({"status": "no name entered"}), 400
    if class_section == "":
        return jsonify({"status": "no class section entered"}), 400
    if len(password) < 8:
        return jsonify({"status": "password must be at least 8 characters long"})
    if class_section == "select instructor":
        return jsonify({"status": "select an instructor"})

    #make sure email is a umbc email
    if re.search("@umbc.edu", email) is None:
        return jsonify({"status": "please use a UMBC email"}), 400

    conn = get_db()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT user_id FROM user_table WHERE email = %s", (email,))
            row = cursor.fetchone()
            if row is not None:
                return jsonify({"status": "account already exsists"}), 409
    finally:
        conn.close()

    conn = get_db()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "INSERT IGNORE INTO user_table (email, password, name, class_section) VALUES (%s, %s, %s, %s)", (email, hashed_password, name, class_section)
            )
            conn.commit()
    finally:
        conn.close()

    conn = get_db()
    if conn is None:
        return jsonify({"status": "cannot connect to database, contact support"})
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT user_id FROM user_table WHERE email = %s", (email,)
            )
            row = cursor.fetchone()
    finally:
        conn.close()

    id = row["user_id"]
    session["user_id"] = id
    session["user"] = email
    session["role"] = "user"
    if session.get("user") is None:
        return jsonify({"status": "failed to initialize user, try again later or contact support"})
    return jsonify({"status": "success"}), 200

@app.route("/verify_email", methods=["POST"])
def verify_email():
    data = request.get_json()
    action = data.get("action")
    email = data.get("email", "")
    input_code = data.get("code", "")

    if email == "":
        return jsonify({"status": "no email entered"}), 400
    if re.search("@umbc.edu", email) is None:
        return jsonify({"status": "please use a UMBC email"}), 400

    if action == "send":
        code = ''.join(secrets.choice(string.digits) for i in range(6))
        session["verification_code"] = code
        send_email(email, "Verification code", f"Your verification code is: {code}")

        return jsonify({"status": "success"})
    
    elif action == "verify":
        if input_code == "":
            return jsonify({"status": "please enter a code"})
        
        code = session.get("verification_code", "")

        if code == "":
            return jsonify({"status": "code not find code, resend email or contact support"})
        elif input_code == code:
            return jsonify({"status": "success"})
        else:
            return jsonify({"status": "incorrect code"})

#function to allow users to download a current iteration of their progress
@app.route("/download_data", methods=["POST"])
@require_role("user", "admin")
def download_data():
    data = request.get_json()
    username = session.get("user")
    timestamp = datetime.datetime.now().strftime("%m/%d/%y %H:%M:%S")  # noqa: DTZ005

    hypothesis = data.get("hypothesis", "")
    evidence = data.get("evidence", "")
    study_type = data.get("study_type", "")
    evidence_strength = data.get("evidence_strength", "")
    data_link_1 = data.get("data_link_1", "")
    data_link_2 = data.get("data_link_2", "")
    variable = data.get("variable", "")
    variable_unit = data.get("variable_unit", "")
    collection_method = data.get("collection_method", "")
    goal = data.get("goal", "")
    variable_type = data.get("variable_type", "")

    conn = get_db()
    with conn.cursor() as cursor:
        try:
            cursor.execute("""
                    SELECT
                        u.email AS student_email,

                        COUNT(DISTINCT CASE WHEN c.revision = 1 THEN c.transaction_id END)
                            AS revision_count

                        FROM user_table AS u
                        LEFT JOIN chat_table AS c
                            ON u.user_id = c.user_id
                        WHERE u.user_id = %s
                        GROUP BY u.user_id, u.email
                        ORDER BY u.email
                    """,
                (session.get("user_id")),)
            row = cursor.fetchone()
            revision_number = int(row["revision_count"])
        finally:
            conn.close()



    lines = []
    lines.append(f"For: {username}")
    lines.append(f"Generated: {timestamp}")
    lines.append("")
    lines.append("-" * 60)
    lines.append("")


    lines.append("Data:\n")
    for index, item in enumerate(variable):
        lines.append(f"Variable {index+1}\n")
        lines.append(f"Variable: {item}")
        lines.append(f"Unit: {variable_unit[index]}")
        lines.append(f"Collection method: {collection_method[index]}")
        lines.append(f"Goal: {goal[index]}")
        lines.append(f"Type: {variable_type[index]}\n")


    lines.append("\n"*3)


    lines.append("Hypotheses:\n")
    for index, item in enumerate(hypothesis):
        lines.append(f"Hypothesis {index+1}, {data_link_1[index]} & {data_link_2[index]}\n")
        lines.append(f"Hypothesis: {item}")
        lines.append(f"Evidence: {evidence[index]}")
        lines.append(f"Study type: {study_type[index]}")
        lines.append(f"Evidence strength: {evidence_strength[index]}\n")


    lines.append("\n"*3)
    lines.append("-" * 60)
    lines.append("\n"*3)

    lines.append("History log:")
    lines.append("")
    for message in get_history():
        lines.append(f"{message['role']}: {message['content']}")

    content = "\n".join(lines)

    response = make_response(content)
    response.headers["Content-Disposition"] = f"attachment; filename={username}_export.txt"
    response.headers["Content-Type"] = "text/plain"
    response.headers["Content-Title"] = f"revision:{revision_number}_of_{username}.txt"
    return response

#get the data from the check in page to be entered 
@app.route("/extract_check_in", methods=["POST"])
@require_role("user", "admin")
def extract_check_in():
    data = request.get_json()
    session["module"] = "evaluation"
    session.modified = True

    user_id = session.get("user_id")

    variable = data.get("variable", [])
    unit = data.get("variable_unit", [])
    collection_method = data.get("collection_method", [])
    goal = data.get("goal", [])
    variable_type = data.get("variable_type", [])

    hypothesis = data.get("hypothesis", [])
    evidence = data.get("evidence", [])
    study_type = data.get("study_type", [])
    strength = data.get("evidence_strength", [])
    link_1 = data.get("data_link_1", [])
    link_2 = data.get("data_link_2", [])

    conn = get_db()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT MAX(submission_id) AS latest_id
                FROM variable_table
                WHERE user_id = %s
                """, (user_id,)
            )
            latest_id = cursor.fetchone()["latest_id"]
            if latest_id is None:
                submission_id = 1
            else:
                submission_id = latest_id + 1

            for i, v in enumerate(variable):
                cursor.execute(
                    """
                    INSERT INTO variable_table
                    (submission_id, user_id, variable, variable_unit, collection_method, goal, variable_type)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """,
                    (submission_id,
                     user_id,
                     v or "",
                     unit[i] if i < len(unit) else "",
                     collection_method[i] if i < len(collection_method) else "",
                     goal[i] if i < len(goal) else "",
                     variable_type[i] if i < len(variable_type) else ""
                    )
                )

            for i, h in enumerate(hypothesis):
                cursor.execute(
                    """
                    INSERT INTO hypothesis_table
                    (submission_id, user_id, hypothesis, evidence, study_type, evidence_strength, link_1, link_2)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (submission_id,
                     user_id,
                     h or "",
                     evidence[i] if i < len(evidence) else "",
                     study_type[i] if i < len(study_type) else "",
                     strength[i] if i < len(strength) else None,
                     link_1[i] if i < len(link_1) else "",
                     link_2[i] if i < len(link_2) else ""
                    )
                )
            conn.commit()
    finally:
        conn.close()
    
    return jsonify(success=True)

#clears history of the chat page + reloads the page
@app.route("/clear_history", )
@require_role("user", "admin")
def clear_history():
    conn = get_db()
    id = session.get("user_id")
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "UPDATE chat_table SET hide_from_user = %s WHERE user_id = %s", (True, id)
            )
        conn.commit()
    finally:
        conn.close()
    return jsonify(success=True)

#agent page
@app.route("/planning_agent")
@require_role("user","admin")
def planning_agent():
    return render_template("planning_agent.html")

#main chat function, handles all openai api calls
@app.route("/chat", methods=["POST"])
@require_role("user", "admin")
def chat():
    data = request.get_json()
    user_message = data.get("message", "")
    is_revision = data.get("is_revision", False)

    #ensure module is evaluation for first revision
    if is_revision:
        session["module"] = "evaluation"
    else:
        #edge case for when user logs out (no session data)
        conn = get_db()
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT user_message, reply FROM chat_table WHERE user_id = %s AND revision = %s AND hide_from_user = %s",
                                (session.get('user_id'), True, False))
                row = cursor.fetchone()
                if row:
                    session["module"] = "evaluation"
                else:
                    session["module"] = "brainstorming"
        finally:
            conn.close()

    module = session.get("module")
    session.modified = True

    if user_message == "welcomemessage":
        reply = WELCOME_MESSAGE

        database_update("N/A", reply, module, is_revision)
        
        return jsonify({"reply": reply})
    try:
        response = client.responses.create(
            model="openai.gpt-5.6-luna",
            instructions=f"""
                        You are an educational research assistant.
                        \n Current module instructions: {BRAINSTORMING_PROMPT if module == 'brainstorming' else EVALUATION_PROMPT}
                    """,
            input=f"{get_history()} + user message: {user_message}",
            tools=[{"type": "web_search", "external_web_access": False}],
            max_output_tokens=8192,
            store=False,
            reasoning={"effort": "medium"}
        )
    except OpenAI.APIError:
        reply = "Sorry, there seems to be an error responding. Try again later or contact support."
        database_update(user_message, reply, module, is_revision)
        return jsonify({"reply": reply})
    
    reply = response.output_text

    database_update(user_message, reply, module, is_revision)

    return jsonify({"reply": reply})

#function for updating chatting table
def database_update(user_message, reply, module, is_revision):
    conn = get_db()
    
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO chat_table
                (user_id, module, user_message, reply, revision, hide_from_user)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (session.get('user_id'), module, user_message, reply, is_revision, False),
            )
            conn.commit()

            cursor.execute("SELECT * FROM chat_table")
    finally:
        conn.close()

#history for giving to ai for reference
def get_history():
    conn = get_db()
    database_history = []

    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT user_message, reply FROM chat_table WHERE user_id = %s ORDER BY transaction_id",
                            (session.get('user_id'),))
            rows = cursor.fetchall()

        if rows is not None:
            for row in rows:
                if row["user_message"] != "N/A":
                    database_history.append({
                        "role": "user",
                        "content": row["user_message"]
                    })
                database_history.append({
                    "role": "assistant",
                    "content": row["reply"]
                })
    finally:
        conn.close()

    return database_history

#for giving data to webpage
@app.route("/get_webpage_history", methods=["GET"])
@require_role("user", "admin")
def get_webpage_history():
    conn = get_db()
    database_history = []

    try:
        with conn.cursor() as cursor:
            #show non-hidden history to student
            cursor.execute("SELECT user_message, reply FROM chat_table WHERE user_id = %s AND hide_from_user = %s ORDER BY transaction_id",
                            (session.get('user_id'), False))
            rows = cursor.fetchall()

        if rows is not None:
            for row in rows:
                if row["user_message"] != "N/A":
                    database_history.append({
                        "role": "user",
                        "content": row["user_message"]
                    })
                database_history.append({
                    "role": "assistant",
                    "content": row["reply"]
                })
    finally:
        conn.close()

    return jsonify(database_history)

#admin page
@app.route("/admin_page")
@require_role("admin")
def admin_page():
    return render_template("admin.html")

@app.route("/admin_update", methods=["POST"])
@require_role("admin")
def admin_update():
    data = request.get_json()
    action = data.get("action")
    email = data.get("email")
    conn = get_db()

    if action == "get_summary":

        try:
            for instructor in instructors:
                with conn.cursor() as cursor:
                    cursor.execute("""
                    SELECT
                        u.email AS student_email,

                        (SELECT COUNT(*) FROM chat_table AS c
                            WHERE c.user_id = u.user_id AND c.module = 'brainstorming')
                            AS brainstorming_count,

                        (SELECT COUNT(*) FROM chat_table AS c
                            WHERE c.user_id = u.user_id AND c.module = 'evaluation')
                            AS evaluation_count,
                            
                        (SELECT COUNT(*) FROM chat_table AS c
                            WHERE c.user_id = u.user_id AND c.revision = 1)
                            AS revision_count,

                        (SELECT CONVERT_TZ(MAX(c.timestamp), 'UTC', 'America/New_York')
                            FROM chat_table AS c
                            WHERE c.user_id = u.user_id
                                AND c.revision = 1)
                            AS latest_revision,

                        (SELECT COUNT(*) FROM variable_table AS v
                            WHERE v.user_id = u.user_id)
                            AS "variable_count",

                        (SELECT COUNT(*) FROM hypothesis_table AS h
                            WHERE h.user_id = u.user_id)
                            AS "hypothesis_count",

                        

                        (SELECT COUNT(*) FROM variable_table AS v
                            WHERE v.user_id = u.user_id AND v.variable_type = 'Sleep') AS sleep_count,
                        (SELECT COUNT(*) FROM variable_table AS v
                            WHERE v.user_id = u.user_id AND v.variable_type = 'Exercise') AS exercise_count,
                        (SELECT COUNT(*) FROM variable_table AS v
                            WHERE v.user_id = u.user_id AND v.variable_type = 'Food') AS food_count,
                        (SELECT COUNT(*) FROM variable_table AS v
                            WHERE v.user_id = u.user_id AND v.variable_type = 'Health-others') AS health_others_count,
                        (SELECT COUNT(*) FROM variable_table AS v
                            WHERE v.user_id = u.user_id AND v.variable_type = 'SWB') AS swb_count,
                        (SELECT COUNT(*) FROM variable_table AS v
                            WHERE v.user_id = u.user_id AND v.variable_type = 'Work') AS work_count,
                        (SELECT COUNT(*) FROM variable_table AS v
                            WHERE v.user_id = u.user_id AND v.variable_type = 'Digital') AS digital_count,
                        (SELECT COUNT(*) FROM variable_table AS v
                            WHERE v.user_id = u.user_id AND v.variable_type = 'Study') AS study_count,
                        (SELECT COUNT(*) FROM variable_table AS v
                            WHERE v.user_id = u.user_id AND v.variable_type = 'Connections') AS connection_count,
                        (SELECT COUNT(*) FROM variable_table AS v
                            WHERE v.user_id = u.user_id AND v.variable_type = 'Hobby/Skills') AS hobby_count,
                        (SELECT COUNT(*) FROM variable_table AS v
                            WHERE v.user_id = u.user_id AND v.variable_type = 'Spiritual') AS spiritual_count,
                        (SELECT COUNT(*) FROM variable_table AS v
                            WHERE v.user_id = u.user_id AND v.variable_type = 'Others') AS others_count

                        FROM user_table AS u
                        WHERE u.class_section = %s
                        ORDER BY u.email
                    """, (instructor,))
                    rows = cursor.fetchall()

                #add headers
                values = [[
                 'Student email', 'Number of brainstorming interactions', 'Number of evaluation interactions',
                 'Number of revisions', 'Latest revision', 'Number of variables', 'Number of hypotheses',
                 'Sleep type number', 'Exercise type number', 'Food type number', 'Heath other type number',
                 'SWB type number', 'Work type number', 'Digital type number', 'Study type number',
                 'Connections type number', 'Hobby/skills type number', 'Spiritual type number', 'Others type number'
                ]]

                for row in rows:
                    if row["latest_revision"] is not None:
                        row["latest_revision"] = row["latest_revision"].strftime("%m/%d/%y %H:%M:%S")

                    #populate summary data
                    values.append([
                        row["student_email"],
                        int(row["brainstorming_count"]),
                        int(row["evaluation_count"]),
                        int(row["revision_count"]),
                        row["latest_revision"],
                        int(row["variable_count"]),
                        int(row["hypothesis_count"]),
                        int(row["sleep_count"]),
                        int(row["exercise_count"]),
                        int(row["food_count"]),
                        int(row["health_others_count"]),
                        int(row["swb_count"]),
                        int(row["work_count"]),
                        int(row["digital_count"]),
                        int(row["study_count"]),
                        int(row["connection_count"]),
                        int(row["hobby_count"]),
                        int(row["spiritual_count"]),
                        int(row["others_count"])
                    ])

                sheet_update("clear", spreadsheet_url, f"{instructor} - summary", [])

                last_row = len(values)

                sheet_update(
                    "write",
                    spreadsheet_url,
                    f"{instructor} - summary!A1:Z{last_row}",
                    values
                )
        finally:
            conn.close()

        return jsonify(success=True)

    if action == "get_raw":
        try:
            for instructor in instructors:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        SELECT
                            transaction_id,
                            CONVERT_TZ(chat_table.timestamp, 'UTC', 'America/New_York') AS timestamp,
                            user_table.email,
                            user_table.name,
                            user_table.class_section,
                            module,
                            user_message,
                            reply
                            FROM chat_table
                            RIGHT JOIN user_table
                                ON chat_table.user_id = user_table.user_id
                            WHERE user_table.class_section = %s
                            ORDER BY transaction_id
                    """, (instructor,))
                    rows = cursor.fetchall()


                #add headers
                values = [[
                    'Timestamp',
                    'Email',
                    'Name',
                    'Class section',
                    'Module',
                    'User message',
                    'AI message'
                ]]

                for row in rows:
                    if row["transaction_id"] is None:
                        continue
                    timestamp_sql = row["timestamp"]
                    timestamp = timestamp_sql.strftime("%m/%d/%y %H:%M:%S")

                    #populate data for each transaction
                    values.append([
                        timestamp,
                        row["email"],
                        row["name"],
                        row["class_section"],
                        row["module"],
                        row["user_message"],
                        row["reply"]
                    ])

                last_row = len(values)

                #clear sheets
                sheet_update("clear", spreadsheet_url, f"{instructor} - raw", [])

                #write transactionary data to the sheet for each instructor
                sheet_update(
                    "write",
                    spreadsheet_url,
                    f"{instructor} - raw!A1:Z{last_row}",
                    values
                )
        finally:
            conn.close()

        return jsonify(success=True)

    if action == "remove_user":
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    "DELETE FROM user_table WHERE email = %s", (email,)
                )
            conn.commit()
        finally:
            conn.close()
        return jsonify(success=True)

@app.route("/logout", methods=["POST"])
@require_role("user","admin")
def logout():
    session.clear()
    return redirect(url_for("login_page"))



if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0")