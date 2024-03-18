import interactions
from interactions import Client, Intents, slash_command, SlashContext, OptionType, slash_option
import requests
import json
import re
from bs4 import BeautifulSoup
from googleapiclient.discovery import build
import google_auth_oauthlib.flow
from google_auth_oauthlib.flow import InstalledAppFlow
import googleapiclient.discovery
import googleapiclient.errors
import os
from youtube_transcript_api import YouTubeTranscriptApi 
from utils import *

bot = Client(intents=Intents.DEFAULT)
TOKEN = json.load(open("keys.json"))

@interactions.listen()
async def on_startup():
    print("Bot ready.")

@slash_command(name="my_command", description="My first command :)")
async def my_command_function(ctx: SlashContext):
    await ctx.send("Hello World")

#Summarize command
@slash_command(
        name="summarize",
        description="Generate a summary from text or a file.",
)
@slash_option(
    name="num_of_words",
    description="Number of words in the summary (between 100 and 400).",
    required=False,
    opt_type=OptionType.INTEGER,
    min_value=100,
    max_value=500
)
@slash_option(
    name="text_content",
    description="Input text or a URL.",
    required=False,
    opt_type=OptionType.STRING,
)
@slash_option(
    name="attachment",
    description="Upload a file with text.",
    required=False,
    opt_type=OptionType.ATTACHMENT,
)
        
async def summarize(ctx: SlashContext, num_of_words: int = 200, text_content: str = "", attachment: bytes = None):

    #Command takes a bit so allow the bot to stall
    await ctx.defer()

    initial_text = text_content

    media = "text"
    youtube_url_pattern = r'(?:https?://)?(?:www\.)?(?:youtube\.com/watch\?v=|youtu\.be/)([a-zA-Z0-9_-]{11})'
    youtube_match = re.search(youtube_url_pattern, text_content)
    is_URL = True

    #User input text
    if text_content:
        #Check if input is a YouTube URL
        if youtube_match:
            try:
                video_id = youtube_match.group(1)

                transcript = YouTubeTranscriptApi.get_transcript(video_id)

                # Combine text from each item in the transcript into a single string
                transcript_string = ' '.join(item['text'] for item in transcript)

                # Append the transcript string to the existing text content
                text_content += '\n' + transcript_string
                media = "video"
            except Exception as e:
                await ctx.send("An error has occured obtaining the contents of this video. This is either because the URL sent is invalid, or the video does not have closed captions.")
                return
        #Check if input is a standard URL
        elif re.match(r'https?://\S+', text_content):
            # If it's a URL, fetch content from the URL
            try:
                response = requests.get(text_content)
                response.raise_for_status()  # Raise an exception for HTTP errors
                html_content = response.text
                soup = BeautifulSoup(html_content, 'html.parser')
                text_content = soup.get_text()
            except requests.exceptions.RequestException as e:
                #await ctx.send(f"Error: {e}")
                return
        else:
            #If it is not a URL, leave the text content alone
            is_URL = False

    
    #User input a file
    elif attachment:
        is_URL = False
        # Assuming only one attachment is allowed
        file_extension = attachment.filename.split('.')[-1].lower()

        if file_extension == 'txt':
            # Text file
            attachment_url = attachment.url
            attachment_content = await download_file(attachment_url)
            text_content = attachment_content.decode('utf-8')
        elif file_extension in ['doc', 'docx']:
            # Word document
            attachment_url = attachment.url
            attachment_content = await download_file(attachment_url)
            text_content = extract_text_from_docx(attachment_content)
            media = "document"
        elif file_extension == 'pptx':
            # PowerPoint document
            attachment_url = attachment.url
            attachment_content = await download_file(attachment_url)
            text_content = extract_text_from_pptx(attachment_content)
            media = "PowerPoint"
        else:
            await ctx.send("Invalid attachment format. Please attach a .txt, .doc, .docx, or .pptx file.")
            return

    else:
        await ctx.send(f"Please provide content for me to summarize.")
        return
    
    print("Text content:", text_content)
    length = get_length(num_of_words)

    payload = {
        "model": "google/gemma-7b-it:free",
        "messages": [
            {
                "role": "user",
                "content": f"You are an excellent summarizer, and are tailored in summarizing documents in a concise way without including your own opinions or outside information. Do not give me other information outside of the {media}. When summarizing, do not assume any information if it isn't explicitly mentioned in the source {media}. Do not assume pronouns if they aren't stated in the text already, and default to they them if needed. Here is the {media}: {text_content}. Please write a {length} summary of {num_of_words} words, and do not exceed 2000 characters. Do not include your own opinions or outside information not mentioned in the {media}, do not assume anything if it didn't happen in the source. Do not mention the word count or any instance of my prompt in your summary."
            }
        ]
    }

    try:
        response = requests.post(
            url="https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer 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",
            },
            data=json.dumps(payload)
        )

        summary = response.json()['choices'][0]['message']['content']
        if len(summary) > 2000:
            summary = summary[:1800]
            summary += "\nThis summary exceeded over 2000 characters."
        if is_URL:
            summary += f"\n\nSource: {initial_text}"
        await ctx.send(summary)

    except Exception as e:
        pass
        #await ctx.send(f"An error occurred: {str(e)}")

# @slash.slash(name="questions",
#              description="Generate questions from text or a file",
#              options=[
#                  interactions.Option(
#                      name="num_of_questions",
#                      description="Number of questions to generate",
#                      option_type=4,
#                      required=True
#                  ),
#                  interactions.Option(
#                      name="content",
#                      description="Text content or upload a file",
#                      option_type=3,
#                      required=True
#                  )
#              ])
# async def generate_questions(ctx: interactions.SlashContext, num_of_questions: int, content: str):
#     # Check if the input is a URL
#     if re.match(r'https?://\S+', content):
#         # If it's a URL, fetch content from the URL
#         try:
#             response = requests.get(content)
#             response.raise_for_status()  # Raise an exception for HTTP errors
#             html_content = response.text
#         except requests.exceptions.RequestException as e:
#             await ctx.send(f"Error: {e}")
#             return

#         # Parse HTML content to extract text
#         soup = BeautifulSoup(html_content, 'html.parser')
#         text_content = soup.get_text()
#     else:
#         # If it's not a URL, use the input text directly
#         text_content = content

#     payload = {
#         "model": "google/gemma-7b-it:free",
#         "messages": [
#             {
#                 "role": "user",
#                 "content": f"You are a helpful assistant. Generate {num_of_questions} questions based on the following. Do not use any other reference, only utilize the text given here: {text_content}. When generaating your response, do not write anything else. Only send the questions. When generating questions, space them out with one single line break, do not use multiple. Generate {num_of_questions} questions."
#             }
#         ]
#     }

#     try:
#         response = requests.post(
#             url="https://openrouter.ai/api/v1/chat/completions",
#             headers={
#                 "Authorization": f"Bearer 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",
#             },
#             data=json.dumps(payload)
#         )

#         questions = response.json()['choices'][0]['message']['content']
#         await ctx.send(questions)

#     except Exception as e:
#         await ctx.send("An error has occurred.")

# @bot.event
# async def on_message(message):
#     if message.author == bot.user:
#         return

#     # Test command to respond with "hello" when user types "hi"
#     if message.content.lower() == 'hi':
#         await message.channel.send('helloooooooo :)')

# Run the bot
bot.start(os.environ.get("DISCORD_TOKEN"))