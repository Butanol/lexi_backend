import getpass
import os
from jigsawstack import JigsawStack
from langchain_groq import ChatGroq

if "GROQ_API_KEY" not in os.environ:
    os.environ["GROQ_API_KEY"] = "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"
jigsaw = JigsawStack("pk_33a4a026aaac2da402d770d5b5ca3d5828a5bea32f6fe9914edc19f634536b7b6909549cdb25988aab53dc8085125eeffc19a499493cc9858f6fc405d1246974024FtwLXKudwn9Fv3GQsg")
validation_llm = ChatGroq(
    model="openai/gpt-oss-120b",
    temperature=0,
    max_tokens=None,
    timeout=None,
    max_retries=2
)
url = "https://raw.githubusercontent.com/SingHacks-2025/juliusbaer/d2a2bb1bd7900e84032032434220702b3b437d09/Swiss_Home_Purchase_Agreement_Scanned_Noise_forparticipants.pdf"
def ocr(url):
    print("starting ocr")
    response = jigsaw.vision.vocr({
        "prompt": [""],
        "url": url
    })
    print("done with ocr")
    return response

def get_text(response):
    text = ""
    data = response["sections"]
    for i in data:
        text +=i["text"]
    return text

def generate_report(text):
    messages = [
        (
            "system",
            "You are a strict banking legal agent validator that checks documents for suspicious areas like irregular spell-checking. Generate a report from the input, penalising for unprofessional formatting."
        ),
        (
            "user",
            text
        )
    ]
    print("starting generation")
    return validation_llm.invoke(messages)

def agent():
    print("starting agent")
    return generate_report(get_text(ocr(url))).content

