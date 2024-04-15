import interactions
from interactions import Client, Intents, OptionType
import requests
import json
import re
from bs4 import BeautifulSoup
import os
from youtube_transcript_api import YouTubeTranscriptApi 
from utils import *

#Switch this if bot is being tested locally. Don't use railway instance if tests are being done.
testing_bot = False

if testing_bot:
    KEYS = json.load(open("keys.json"))
    DISCORD_TOKEN = KEYS["DISCORD_TOKEN"]
    OPEN_ROUTER_KEY = KEYS["OPEN_ROUTER_KEY"]
else:
    DISCORD_TOKEN = os.environ.get("DISCORD_TOKEN")
    OPEN_ROUTER_KEY = os.environ.get("OPEN_ROUTER_KEY")

bot = interactions.Client(token=DISCORD_TOKEN)


#Summarize command
@bot.command(
    name="summarize",
    description="Generate a summary from text or a file.",
    options=[
        interactions.Option(
            name="word_count",
            description="Number of words in the summary (between 100 and 400).",
            required=False,
            type=interactions.OptionType.INTEGER,
            min_value=100,
            max_value=500
        ),
        interactions.Option(
            name="text",
            description="Input text or a URL.",
            required=False,
            type=interactions.OptionType.STRING,
        ),
        interactions.Option(
            name="attachment",
            description="Upload a file with text.",
            required=False,
            type=interactions.OptionType.ATTACHMENT,
        )
    ]
)
        
async def summarize(ctx: interactions.CommandContext, word_count: int = 200, text: str = "", attachment: bytes = None):

    #Command takes a bit so allow the bot to stall
    await ctx.defer()

    initial_text = text

    media = "text"
    youtube_url_pattern = r'(?:https?://)?(?:www\.)?(?:youtube\.com/watch\?v=|youtu\.be/)([a-zA-Z0-9_-]{11})'
    youtube_match = re.search(youtube_url_pattern, text)
    is_URL = True

    #User input text
    if text:
        #Check if input is a YouTube URL
        if youtube_match:
            try:
                video_id = youtube_match.group(1)

                transcript = YouTubeTranscriptApi.get_transcript(video_id)

                # Combine text from each item in the transcript into a single string
                transcript_string = ' '.join(item['text'] for item in transcript)

                # Append the transcript string to the existing text content
                text += '\n' + transcript_string
                media = "video"
            except Exception as e:
                await ctx.send("An error has occured obtaining the contents of this video. This is either because the URL sent is invalid, or the video does not have closed captions.")
                return
        #Check if input is a standard URL
        elif re.match(r'https?://\S+', text):
            try:
                response = requests.head(text, allow_redirects=True)
                #Check if the URL is a direct link to a downloadable file
                if 'Content-Disposition' in response.headers:
                    # If the response contains Content-Disposition header, it's likely a download link
                    # Setting this to false as the document is not an embeddable website
                    is_URL = False
                    # Fetch content from the URL
                    response = requests.get(text)
                    response.raise_for_status()  # Raise an exception for HTTP errors
                    attachment = response.content

                    content = await get_file_content(attachment)
                    #If file format is not supported
                    if content == False:
                        await ctx.send("Invalid attachment format. Please attach a valid file type.")
                    else:
                        text = content[0]
                        media = content[1]
                    media = "attachment"
                else:
                    # It's a standard URL, fetch content from it
                    response = requests.get(text)
                    response.raise_for_status()  # Raise an exception for HTTP errors
                    html_content = response.text
                    soup = BeautifulSoup(html_content, 'html.parser')
                    text = soup.get_text()
            except requests.exceptions.RequestException as e:
                # Handle errors
                # await ctx.send(f"Error: {e}")
                return
        else:
            #If it is not a URL, leave the text content alone
            is_URL = False

    
    #User input a file
    elif attachment:
        is_URL = False
        content = await get_file_content(attachment)
        #If file format is not supported
        if content == False:
            await ctx.send("Invalid attachment format. Please attach a valid file type.")
        else:
            text = content[0]
            media = content[1]

    else:
        await ctx.send(f"Please provide content for me to summarize.")
        return
    
    #print("Text content:", text)
    length = get_length(word_count)
    prompt = f"""You are an excellent summarizer, and are tailored in summarizing documents in a concise way without 
    including your own opinions or outside information. Do not give me other information outside of the {media}. When 
    summarizing, do not assume any information if it isn't explicitly mentioned in the source {media}. Do not assume 
    pronouns if they aren't stated in the text already, and default to they/them if needed. Here is the {media}: {text}. 
    Please write a {length} summary of {word_count} words, and do not exceed 2000 characters. Do not include your own 
    opinions or outside information not mentioned in the {media}, do not assume anything if it didn't happen in the 
    source. Do not mention the word count or any instance of my prompt in your summary. Include a concise 
    title for your summary."""

    payload = {
        "model": "google/gemma-7b-it:free",
        "messages": [
            {
                "role": "user",
                "content": prompt
            }
        ]
    }

    try:
        response = requests.post(
            url="https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPEN_ROUTER_KEY}",
            },
            data=json.dumps(payload)
        )

        summary = response.json()['choices'][0]['message']['content']
        if len(summary) > 2000:
            summary = summary[:1800]
            summary += "...\nThis summary exceeded over 2000 characters."
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
#         text = soup.get_text()
#     else:
#         # If it's not a URL, use the input text directly
#         text = content

#     payload = {
#         "model": "google/gemma-7b-it:free",
#         "messages": [
#             {
#                 "role": "user",
#                 "content": f"You are a helpful assistant. Generate {num_of_questions} questions based on the following. Do not use any other reference, only utilize the text given here: {text}. When generaating your response, do not write anything else. Only send the questions. When generating questions, space them out with one single line break, do not use multiple. Generate {num_of_questions} questions."
#             }
#         ]
#     }

#     try:
#         response = requests.post(
#             url="https://openrouter.ai/api/v1/chat/completions",
#             headers={
#                 "Authorization": f"Bearer {OPEN_ROUTER_KEY}",
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
bot.start()