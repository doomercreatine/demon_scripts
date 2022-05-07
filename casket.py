# Twitch Bot to Determine Casket winners

from email import message
from twitchio.ext import commands
import re
from config import config
import json
import datetime
import aiofiles
import subprocess


class Bot(commands.Bot):

    def __init__(self):
        # Initialise our Bot with our access token, prefix and a list of channels to join on boot...
        # prefix can be a callable, which returns a list of strings or a string...
        # initial_channels can also be a callable which returns a list of strings...
        super().__init__(token=config['token'], prefix='?', initial_channels=config['channels'])
        self.log_guesses = False
        self.guesses = {}
        self.messages = {}
        self.tens = dict(k=1e3, m=1e6, b=1e9)
        self.punc = '''!()-[]{};:'"\,<>./?@#$%^&*_~'''

    async def event_ready(self):
        # Notify us when everything is ready!
        # We are logged in and ready to chat and use commands...
        print(f'Logged in as | {self.nick}')
        print(f'User id is | {self.user_id}')
        print(f'Channels | {self.connected_channels}')

    @commands.command()
    async def botcheck(self, ctx: commands.Context):
        # Here we have a command hello, we can invoke our command with our prefix and command name
        # e.g ?hello
        # We can also give our commands aliases (different names) to invoke with.

        # Send a hello back!
        # Sending a reply back to the channel is easy... Below is an example.
        if ctx.author.is_broadcaster or ctx.author.display_name == "DoomerCreatine":
            await ctx.send(f'{self.nick} is online and running {ctx.author.display_name}')
        
    @commands.command()
    async def start(self, ctx: commands.Context):
        if ctx.author.is_broadcaster:
            if not self.log_guesses:
                self.messages.clear()
                self.guesses.clear()
                self.log_guesses = True
                await ctx.send("Guessing for Master Casket value is now OPEN!")
                print(f"{ctx.author.display_name} has started logging guesses in channel: {ctx.channel.name}")
            else:
                await ctx.send("Guessing already enabled, please ?end before starting a new one.")
        
        
    async def event_message(self, message):
        # Messages with echo set to True are messages sent by the bot...
        # For now we just want to ignore them...
        if message.echo:
            return

        # Parse each users message and extract the guess
        if self.log_guesses and '?' not in message.content:
            if message.author.display_name in self.guesses.keys():
                await message.channel.send(f"You have guessed already {message.author.display_name}. You have been removed from this round NothingYouCanDo")
                self.guesses[message.author.display_name] = ""
            else:
                # Regex to try and wrangle the guesses into a consistent int format
                formatted_v = re.search(r"[0-9\s,.]+\s*[,.kKmMbB]*\s*[0-9]*", message.content).group().strip()
                formatted_v = re.sub(r',', '.', formatted_v).lower()
                
                # If the chatter used k, m, or b for shorthand, attempt to convert to int
                try:
                    if 'k' in formatted_v or 'm' in formatted_v or 'b' in formatted_v:
                        formatted_v = int(float(formatted_v[0:-1]) * self.tens[formatted_v[-1]])
                    else:
                        formatted_v = re.sub(r'[^\w\s]', '', formatted_v).lower()
                        formatted_v = int(formatted_v)
                except:
                    await commands.Context.send(f"Sorry, could not parse @{message.author.display_name} guess.")
                self.messages[message.author.display_name] = message.content
                self.guesses[message.author.display_name] = formatted_v
        
        # Since we have commands and are overriding the default `event_message`
        # We must let the bot know we want to handle and invoke our commands...
        await self.handle_commands(message)
    
    # Closes the guess logging
    @commands.command()
    async def end(self, ctx: commands.Context):
        if ctx.author.is_broadcaster:
            if not self.log_guesses:
                await ctx.send("Guessing is not currently enabled, oops. mericCat")
                print("Guessing not enabled.")
                print(f"{ctx.author.display_name} tried to end guessing in {ctx.channel.name} but it was not started.")
            else:
                self.log_guesses = False
                await ctx.send("Guessing for the Master Casket is now CLOSED! PauseChamp")
                print(f"{ctx.author.display_name} has ended logging guesses in channel: {ctx.channel.name}")
    
    @commands.command()
    async def winner(self, ctx: commands.Context, casket: int):
        if ctx.author.is_broadcaster:
            if not self.log_guesses:  
                self.guesses = {k: v for k, v in self.guesses.items() if v}
                if self.guesses:                 
                    res_key, res_val = min(self.guesses.items(), key=lambda x: abs(casket - x[1]))
                    await ctx.send(f"Closest guess: @{res_key} Clap out of {len(self.guesses.keys())} entries with a guess of {'{:,}'.format(res_val)} [Difference: { '{:,}'.format(abs(casket - self.guesses[res_key])) }]")
                    print(f"Closest guess: @{res_key} Clap out of {len(self.guesses.keys())} entries with a guess of {'{:,}'.format(res_val)} [Difference: {abs(casket - self.guesses[res_key])}]")
                    #subprocess.call(f'sudo echo "Recent winner: {res_key}" > /dev/fb01', shell=True)
                else:
                    await ctx.send("Something went wrong, there were no guesses saved. mericChicken")
                    print(f"{ctx.author.display_name} tried picking a winner in {ctx.channel.name}, but no guesses were logged.")
                # Make sure to clear the dictionary so that past guesses aren't included
                async with aiofiles.open(f'./logging/{datetime.datetime.now().strftime("%Y%m%d-%H%M%S")}-{ctx.channel.name}.txt', 'w+') as f:
                    print(f"{ctx.author.display_name} has chosen a winner in {ctx.channel.name}. Writing guesses to file.")
                    await f.write(json.dumps([self.messages, self.guesses, {'casket': casket}], indent=4))
            else:
                await ctx.send("Hey you need to ?end the guessing first 4Head")
                print(f"{ctx.author.display_name} tried to pick a winner in {ctx.channel.name} without ending first.")

        


bot = Bot()
bot.run()