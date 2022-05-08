"""
    Project: Master Casket Guess Bot
    Author: DoomerCreatine <https://github.com/doomercreatine> <https://twitch.tv/doomercreatine>
    Description: Twitch chat bot that allows the streamer to start logging chatters guesses for master casket value.
                 Commands are restricted to the broadcaster.
    Basic functionality:
        ?start | Begins logging chatters guesses
        ?end | Stops logging chatters guesses
        ?winner <INT> | Takes the casket value <INT> and finds the chatter with the lowest absolute difference and tags them in chat.
"""

from email import message
from twitchio.ext import commands
import re
from config import config
import json
import datetime
import aiofiles
import subprocess
import logging
import requests

logging.basicConfig(format='%(asctime)s %(message)s', filename='./casket.log', encoding='utf-8', level=logging.DEBUG)

class Bot(commands.Bot):

    def __init__(self):
        """
            Token and initial channels are found in config.py which is a dictionary in the format below:
            {
                'token': <TOKEN>,
                'channels': [<CHANNEL>, ...]
            }
            
            Tokens can be generated for your Twitch account at https://twitchapps.com/tmi/
            Remember to KEEP YOUR TOKEN PRIVATE! DO NOT SHARE WITH OTHERS
        """
        super().__init__(token=config['token'], prefix='?', initial_channels=config['channels'])
        self.log_guesses = False
        self.guesses = {}
        self.messages = {}
        self.tens = dict(k=1e3, m=1e6, b=1e9)
        self.punc = '''!()-[]{};:'"\,<>./?@#$%^&*_~'''
        self.emote_list = []
        bttv = requests.get(
            "https://api.betterttv.net/2/channels/hey_jase"
        )

            
        ffz = requests.get(
            "https://api.frankerfacez.com/v1/room/hey_jase"
        )

        #print(json.dumps(ffz.json(), indent = 4))

        for emote in ffz.json()['sets']['318206']['emoticons']:
            self.emote_list.append(emote['name'])

        for emote in bttv.json()['emotes']:
            self.emote_list.append(emote['code'])
            
        self.emoji_pattern = re.compile("["
        u"\U0001F600-\U0001F64F"  # emoticons
        u"\U0001F300-\U0001F5FF"  # symbols & pictographs
        u"\U0001F680-\U0001F6FF"  # transport & map symbols
        u"\U0001F1E0-\U0001F1FF"  # flags (iOS)
                           "]+", flags=re.UNICODE)


    async def event_ready(self):
        # Notify us when everything is ready!
        # We are logged in and ready to chat and use commands...
        print(f'Logged in as | {self.nick}')
        print(f'User id is | {self.user_id}')
        print(f'Channels | {self.connected_channels}')
        logging.info(f"Bot connected as {self.nick} in channels {self.connected_channels}")
    
    def emote_filter(self, text, index):
        new_text = list(text)
        if len(index)>=1:
            for idx in index:
                idx_start = int(idx.split("-")[0])
                idx_end = int(idx.split("-")[1])+1
                for i in range(idx_start, idx_end):
                    new_text[i] = ""
        emote_rem = re.sub(' +', ' ', ''.join(new_text).strip())
        emote_rem = ''.join([word for word in emote_rem.split() if word not in self.emote_list])
        return(self.emoji_pattern.sub(r'', emote_rem))

    @commands.command()
    async def botcheck(self, ctx: commands.Context):
        # Here we have a command hello, we can invoke our command with our prefix and command name
        # e.g ?hello
        # We can also give our commands aliases (different names) to invoke with.

        # Send a hello back!
        # Sending a reply back to the channel is easy... Below is an example.
        if ctx.author.is_broadcaster or ctx.author.display_name == "DoomerCreatine":
            await ctx.send(f'{self.nick} is online and running {ctx.author.display_name}')
            print(f'[{datetime.datetime.now().strftime("%H:%M:%S")}] {ctx.author.display_name} has checked if the bot is online in {ctx.channel.name}')
        
    @commands.command()
    async def start(self, ctx: commands.Context):
        if ctx.author.is_broadcaster:
            if not self.log_guesses:
                self.messages.clear()
                self.guesses.clear()
                self.log_guesses = True
                await ctx.send("Guessing for Master Casket value is now OPEN!")
                print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] {ctx.author.display_name} has started logging guesses in channel: {ctx.channel.name}")
            else:
                await ctx.send("Guessing already enabled, please ?end before starting a new one.")
        
        
    async def event_message(self, message):
        # Messages with echo set to True are messages sent by the bot...
        # For now we just want to ignore them...
        if message.echo:
            return
        # Parse each users message and extract the guess
        if self.log_guesses and '?' not in message.content:
                # If chatter has not guessed, attempt to find a guess in their message
                # First let's remove all emotes from the message
            emote_idx = message.tags['emotes'].split("/")
            emote_idx = [i for i in emote_idx if i]
            if len(emote_idx) > 0:
                emote_idx = [m.split(":")[1] for m in emote_idx]
            new_message = self.emote_filter(text=message.content, index=emote_idx)
            try:
                # Regex to try and wrangle the guesses into a consistent int format
                formatted_v = re.search(r"(?<![aAcCdDeEfFgGhHiIjJlLnNoOpPqQrRsStTuUvVwWxXyYzZ])[0-9\s,.]+(?![aAcCdDeEfFgGhHiIjJlLnNoOpPqQrRsStTuUvVwWxXyYzZ]+\b)\s*[,.]*[kKmMbB]{0,1}\s*[0-9]*", new_message).group().strip()
                if formatted_v:
                    formatted_v = re.sub(r',', '.', formatted_v).lower()
                    # If the chatter used k, m, or b for shorthand, attempt to convert to int
                    if 'k' in formatted_v or 'm' in formatted_v or 'b' in formatted_v:
                        formatted_v = int(float(formatted_v[0:-1]) * self.tens[formatted_v[-1]])
                    else:
                        formatted_v = re.sub(r'[^\w\s]', '', formatted_v).lower()
                        formatted_v = int(formatted_v)
                    if formatted_v and message.author.display_name in self.guesses.keys():
                        await message.channel.send(f"You have guessed already {message.author.display_name}. You have been removed from this round NothingYouCanDo")
                        self.guesses[message.author.display_name] = ""
                    self.guesses[message.author.display_name] = formatted_v
            # If no regex match is detected, log that for review
            except Exception as e:
                #await message.channel.send(f"Sorry, could not parse @{message.author.display_name} guess.")
                logging.error(f"Sorry, could not parse @{message.author.display_name} guess. {message.content}")
                logging.error(e)
            self.messages[message.author.display_name] = message.content
                
        # Since we have commands and are overriding the default `event_message`
        # We must let the bot know we want to handle and invoke our commands...
        await self.handle_commands(message)
    
    # Closes the guess logging
    @commands.command()
    async def end(self, ctx: commands.Context):
        if ctx.author.is_broadcaster:
            if not self.log_guesses:
                await ctx.send("Guessing is not currently enabled, oops. mericCat")
                print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] {ctx.author.display_name} tried to end guessing in {ctx.channel.name} but it was not started.")
            else:
                self.log_guesses = False
                await ctx.send("Guessing for the Master Casket is now CLOSED! PauseChamp")
                print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] {ctx.author.display_name} has ended logging guesses in channel: {ctx.channel.name}")
    
        """_summary_
        Command to determine the winner. Find the chatter who's guess was closest to the actual casket value.
        All guesses and raw messages are logged for future review.
        """
    @commands.command()
    async def winner(self, ctx: commands.Context, casket: str):
        formatted_v = re.search(r"(?<![aAcCdDeEfFgGhHiIjJlLnNoOpPqQrRsStTuUvVwWxXyYzZ])[0-9\s,.]+(?![aAcCdDeEfFgGhHiIjJlLnNoOpPqQrRsStTuUvVwWxXyYzZ]+\b)\s*[,.]*[kKmMbB]{0,1}\s*[0-9]*", casket).group().strip()
        formatted_v = re.sub(r',', '.', formatted_v).lower()
        # If the chatter used k, m, or b for shorthand, attempt to convert to int
        if 'k' in formatted_v or 'm' in formatted_v or 'b' in formatted_v:
            casket = int(float(formatted_v[0:-1]) * self.tens[formatted_v[-1]])
        else:
            formatted_v = re.sub(r'[^\w\s]', '', formatted_v).lower()
            casket = int(formatted_v)
        if ctx.author.is_broadcaster:
            if not self.log_guesses:  
                self.guesses = {k: v for k, v in self.guesses.items() if v}
                if self.guesses:   
                    # Find minimum absolute difference between casket value and chatter guesses              
                    res_key, res_val = min(self.guesses.items(), key=lambda x: abs(casket - x[1]))
                    await ctx.send(f"Closest guess: @{res_key} Clap out of {len(self.guesses.keys())} entries with a guess of {'{:,}'.format(res_val)} [Difference: { '{:,}'.format(abs(casket - self.guesses[res_key])) }]")
                    print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] Closest guess: @{res_key} Clap out of {len(self.guesses.keys())} entries with a guess of {'{:,}'.format(res_val)} [Difference: {abs(casket - self.guesses[res_key])}]")
                    #subprocess.call(f'sudo echo "Recent winner: {res_key}" > /dev/fb01', shell=True)
                else:
                    # If for some reason no winner was found we need to review later. Not expected to happen with a large chat
                    await ctx.send("Something went wrong, there were no guesses saved. mericChicken")
                    print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] {ctx.author.display_name} tried picking a winner in {ctx.channel.name}, but no guesses were logged.")
                    logging.error(f'No guesses were found for a winner. {json.dumps([self.messages, self.guesses], indent=4)}')
                # Make sure to clear the dictionary so that past guesses aren't included
                async with aiofiles.open(f'./logging/{datetime.datetime.now().strftime("%Y%m%d-%H%M%S")}-{ctx.channel.name}.txt', 'w+') as f:
                    print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] {ctx.author.display_name} has chosen a winner in {ctx.channel.name}. Writing guesses to file.")
                    await f.write(json.dumps([self.messages, self.guesses, {'casket': casket}], indent=4))
            else:
                await ctx.send("Hey you need to ?end the guessing first 4Head")
                print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] {ctx.author.display_name} tried to pick a winner in {ctx.channel.name} without ending first.")

        

bot = Bot()
bot.run()