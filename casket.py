# Twitch Bot to Determine Casket winners

from email import message
from twitchio.ext import commands
import re
from config import config


class Bot(commands.Bot):

    def __init__(self):
        # Initialise our Bot with our access token, prefix and a list of channels to join on boot...
        # prefix can be a callable, which returns a list of strings or a string...
        # initial_channels can also be a callable which returns a list of strings...
        super().__init__(token=config['token'], prefix='?', initial_channels=config['channels'])
        self.log_guesses = False
        self.guesses = {}
        self.tens = dict(k=1e3, m=1e6, b=1e9)
        self.punc = '''!()-[]{};:'"\,<>./?@#$%^&*_~'''

    async def event_ready(self):
        # Notify us when everything is ready!
        # We are logged in and ready to chat and use commands...
        print(f'Logged in as | {self.nick}')
        print(f'User id is | {self.user_id}')

    @commands.command()
    async def hello(self, ctx: commands.Context):
        # Here we have a command hello, we can invoke our command with our prefix and command name
        # e.g ?hello
        # We can also give our commands aliases (different names) to invoke with.

        # Send a hello back!
        # Sending a reply back to the channel is easy... Below is an example.
        await ctx.send(f'Hello {ctx.author.name}!')
        
    @commands.command()
    async def start(self, ctx: commands.Context):
        if ctx.author.is_mod or ctx.author.is_broadcaster:
            self.guesses = {}
            self.log_guesses = True
            await ctx.send("Guessing has begun!")
        
        
    async def event_message(self, message):
        # Messages with echo set to True are messages sent by the bot...
        # For now we just want to ignore them...
        if message.echo:
            return

        # Parse each users message and extract the guess
        if self.log_guesses and '?' not in message.content:
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
            self.guesses[message.author.display_name] = formatted_v
        print(message.content)
        
        # Since we have commands and are overriding the default `event_message`
        # We must let the bot know we want to handle and invoke our commands...
        await self.handle_commands(message)
    
    # Closes the guess logging
    @commands.command()
    async def end(self, ctx: commands.Context):
        if ctx.author.is_mod or ctx.author.is_broadcaster:
            if not self.log_guesses:
                await ctx.send("Guessing currently not enabled.")
            else:
                self.log_guesses = False
                await ctx.send("Guessing has ended!")
    
    @commands.command()
    async def winner(self, ctx: commands.Context, casket: int):
        if ctx.author.is_mod or ctx.author.is_broadcaster:
            if self.guesses:
                if not self.log_guesses:
                    res_key, res_val = min(self.guesses.items(), key=lambda x: abs(casket - x[1]))
                    await ctx.send(f"Casket value: {casket} (Closest guess: {res_key} with a guess of {res_val} [Difference: {abs(casket - self.guesses[res_key])}]")
                else:
                    await ctx.send("Please end the guessing before choosing a winner.")
                # Make sure to clear the dictionary so that past guesses aren't included
                self.guesses.clear()
            else:
                await ctx.send("No guesses logged.")


bot = Bot()
bot.run()