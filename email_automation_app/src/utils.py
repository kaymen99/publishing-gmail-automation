import re, os
from datetime import datetime
from mailparser_reply import EmailReplyParser

RAG_DATABASE_DIR = f"{os.getcwd()}/email_automation_app/database"

STANDARD_REPLIES_TEMPLATES = {
    "Paper Already Published": """
Thank you for clarifying this with us. We apologize for the confusion but we are looking for papers that have not been published yet. In the future, should you have another manuscript that you would like to submit, feel free to let us know.

Regards,
Elena
""",
    "After submission": """
Thank you for your submission. I will have this sent to the reviewers. My assistant should be in touch with you for additional details and updates with regards to your manuscript review information.

You should receive a submission receipt within 3 days, otherwise, inform me so we can follow up the request. After receiving a submission receipt, kindly wait for feedback within 20-25 days or until the review process is completed.

Regards,
Elena
""",
    "Not Interested": """
Thank you for letting me know. Have a nice day!

Regards,
Elena
""",
}

def strip_old_replies(body):
    languages = ['en', 'de', 'fr', 'it']
    latest_reply = EmailReplyParser(languages=languages).parse_reply(text=body)
    return latest_reply

def strip_old_replies_1(body):
    # Look for typical reply separators, starting from phrases like "On [date], [person] wrote:"
    reply_pattern = re.compile(
        r"(On\s.*?wrote:|Le\s.*?écrit :|From:\s.*?$|Sent:\s.*?$|Envoyé:\s.*?$|" +
        r"Am\s.*?schrieb:|El\s.*?escribió:|Il\s.*?ha scritto:|在\s.*?写道:|" +
        r"Em\s.*?escreveu:|Op\s.*?schreef:|日時：.*?差出人：|Pada\s.*?menulis:|" +
        r"Dne\s.*?napsal:|W dniu\s.*?napisał:|Написано\s.*?:|Na\s.*?napisal:|" +
        r"Tarihinde\s.*?yazdı:|Enviado\s.*?:|Op\s.*?skrev:|" +
        r"På\s.*?skrev:|Den\s.*?skrev:|Enviado\s.*?por:|على\s.*?كتب:|" +
        r"من\s.*?كتب:|Pošiljatelj\s.*?napisal:|.*?@\S+\s*wrote:|" +
        r"Gönderildi:\s.*?$|Kime:\s.*?$)",
        re.MULTILINE | re.DOTALL
    )

    # Split the email body at the reply point (keep only the first part before the reply starts)
    match = reply_pattern.search(body)

    if match:
        # Keep everything before the reply pattern starts
        cleaned_body = body[:match.start()]
    else:
        cleaned_body = body  # No old replies found, return the body as is

    # Remove lines starting with ">" and any following empty lines
    cleaned_body = re.sub(r'^>.*?$\n*', '', cleaned_body, flags=re.MULTILINE)

    return cleaned_body.strip()

# def extract_response(s: str) -> str: 
#     return next(re.finditer(r'Response:(.*?)(?=Reply:|$)', s, re.DOTALL), re.match('$', '')).group(1).strip()

def extract_response(s: str) -> str:
    match = next(re.finditer(r'Response:(.*?)(?=Reply:|$)', s, re.DOTALL), re.match('$', ''))
    if match:
        response = match.group(1).strip()
        # Remove the first name from the email address in the response
        response = re.sub(r'^\w+,\s*', '', response)
        return response
    else:
        return ''

def calculate_deadline():
    today = datetime.now()
    current_year = today.year
    current_month = today.month
    current_day = today.day

    if current_day < 15:
        # Return the 15th of the current month
        deadline = datetime(current_year, current_month, 15)
    else:
        # Return the 15th of the next month
        if current_month == 12:  # Handle year-end case
            deadline = datetime(current_year + 1, 1, 15)
        else:
            deadline = datetime(current_year, current_month + 1, 15)

    # Format deadline as "15 Month Year"
    return deadline.strftime("%d %B %Y")

def get_journal_price(journal_prices, email_subject):
    subject_match = re.search(r"- (.+)$", email_subject)
    journal_name = subject_match.group(1) if subject_match else None

    return journal_prices[journal_name.strip()]

def compose_update_information(state, journal_prices):
    update_info = ""
    if "Fees or Charges" in state['email_inquiries']:
        journal_price = get_journal_price(
            journal_prices,
            state['current_email'].subject
        )
        update_info += f"Latest Annual Journal Cost: {journal_price}$\n"
    if "Submission Deadlines" in state['email_inquiries']:
        deadline = calculate_deadline()
        update_info += f"Latest Submission deadline: {deadline}\n"
    
    return update_info