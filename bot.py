import discord
import datetime
import random
import sqlite3
import google.generativeai as genai
from discord.ext import commands


def get_db_connection():
    conn = sqlite3.connect('bot_database.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            discord_id INTEGER UNIQUE,
            username TEXT,
            balance INTEGER DEFAULT 0
        )
    ''')
    conn.commit()
    conn.close()
init_db()

class Bot(discord.Client):
    def __init__(self, token: str, command_prefix: str = "!"):
        self.token = token
        intents = discord.Intents.default()
        intents.message_content = True

        self.bot = commands.Bot(
            command_prefix = command_prefix,
            intents = intents,
        )
        self._setup_events()
        self._setup_commands()

    def _setup_events(self):
        @self.bot.event
        async def on_ready():
            print(f"Bot {self.bot.user} is ready")

        @self.bot.event
        async def on_message(message):
            if message.author == self.bot.user:
                return
            await self.bot.process_commands(message)

    def _setup_commands(self):
        @self.bot.command(name='hello')
        async def hello(ctx):
            await ctx.send(f'Привет, {ctx.author.mention}! Рад быть полезным тебе')

        @self.bot.command(name='help_me')
        async def help_me(ctx):
            with open('help_me.txt', encoding="utf-8") as f:
                helping = f.read()
                await ctx.send(helping)

        @self.bot.command(name='balance')
        async def balance(ctx):
            try:
                conn = get_db_connection()
                user = conn.execute('SELECT * FROM users WHERE discord_id = ?', (ctx.author.id,)).fetchone()
                if user:
                    await ctx.send(f'Ваш баланс: {user["balance"]} монет')
                else:
                    conn.execute(
                'INSERT INTO users (discord_id, username) VALUES (?, ?)',
                (ctx.author.id, ctx.author.name))
                    conn.commit()
                    await ctx.send('Вы зарегистрированы! Баланс: 0 монет')
                conn.close()
            except Exception as e:
                print(f"Ошибка в команде balance: {e}")
                await ctx.channel.send('Произошла ошибка, попробуйте снова позже')

        @self.bot.command(name='work')
        async def work(ctx):
            try:
                conn = get_db_connection()
                user = conn.execute('SELECT * FROM users WHERE discord_id = ?', (ctx.author.id,)).fetchone()
                if user:
                    zp = random.randint(1,100)
                    new_balance = user['balance'] + zp  # ← Вычисляем новый баланс
                    conn.execute(
                        'UPDATE users SET balance = ? WHERE discord_id = ?',
                        (new_balance, ctx.author.id)
                    )
                    conn.commit()
                    await ctx.channel.send(f'Вы поработали и заработали {zp} монет. Ваш баланс {new_balance} монет')
                else:
                    conn.execute(
                        'INSERT INTO users (discord_id, username) VALUES (?, ?)',
                        (ctx.author.id, ctx.author.name))
                    conn.commit()
                    await ctx.send('Вы зарегистрированы теперь и у вас 0 монет! Поработайте теперь введя команду еше раз')
                conn.close()
            except Exception as e:
                print(f"Ошибка в команде balance: {e}")
                await ctx.channel.send('Произошла ошибка, попробуйте снова позже')

        @self.bot.command(name='leaders')
        async def leaders(ctx):
            try:
                conn = get_db_connection()
                user = conn.execute('SELECT * FROM users WHERE discord_id = ?', (ctx.author.id,)).fetchone()
                if user:
                    top_users = conn.execute(
                        'SELECT username, balance FROM users ORDER BY balance DESC LIMIT 10'
                    ).fetchall()
                    leaderboard = "🏆 **Топ-10 самых богатых пользователей:**\n"
                    for i, user in enumerate(top_users, 1):
                        leaderboard += f"{i}) {user['username']} - {user['balance']} монет\n"
                    leaderboard += "\nЗнай героев в лицо! 💰"
                    await ctx.send(leaderboard)
                else:
                    conn.execute(
                        'INSERT INTO users (discord_id, username) VALUES (?, ?)',
                        (ctx.author.id, ctx.author.name))
                    conn.commit()
                    await ctx.send('Вы зарегистрированы теперь и мы готовы показать топ-10! Поработайте теперь введя команду еше раз')
                conn.close()
            except Exception as e:
                print(e)
                await ctx.channel.send('Произошла ошибка, попробуйте снова позже')

        @self.bot.command(name='randoms')
        async def randoms(ctx, *vars):
            try:
                var_win = random.choice(vars)
                await ctx.channel.send(f"Я думаю лучшим вариантом из этих будет {var_win}")
            except Exception as e:
                await ctx.channel.send("Введите варианты корректно пожалуйста")

        @self.bot.command(name='fight')
        async def fight(ctx, user: discord.Member):
            try:
                choices = [user, ctx.author.mention]
                choice = random.choice(choices)
                await ctx.channel.send(f"Победил - {choice}, а второй лузер")
            except Exception as e:
                await ctx.channel.send('Введите корректно пожалуйста')

        @self.bot.command(name='answer')
        async def answer(ctx, *, question: str):
            try:
                with open('gemini_token.txt', encoding='utf-8') as t:
                    gtoken = t.read()
                    genai.configure(api_key=gtoken)
                if not isinstance(question, str) or not question.strip():
                    await ctx.send(f"{ctx.author.mention} Вы не ввели вопрос. Пример использования: /answer кто я?")
                    return
                question = question[:500]
                prompt = (f"Ответь на вопрос, который ввел пользователь\nВопрос: {question}\nОтвет: .\n Запомни, Ты бот дискорд, разработанный для помощи пользователям. Будь дружелюбным. Пиши не длинно и по делу, без лишней информации. На странные и вызывающие вопросы можешь не отвечать и просить сменить тему. Пиши более кратко")
                model = genai.GenerativeModel('gemini-2.5-flash-lite')
                response = model.generate_content(
                    contents=[prompt],
                    generation_config={
                        "max_output_tokens": 200,
                        "temperature": 0.7,
                    }
                )
                await ctx.channel.send(f'{ctx.author.mention} {response.text.strip()}')
            except Exception as e:
                await ctx.channel.send('Проблемки с командой... попробуйте позже')
                print(e)

        @commands.bot_has_permissions(ban_members=True)
        @self.bot.command(name='ban')
        async def ban(ctx, user: discord.Member, *, reason='причина не указана'):
            try:
                await user.ban(reason = reason)
                ban = discord.Embed(title=f":boom: Забанил {user.name}!", description=f"По причине: {reason}\nОт: {ctx.author.mention}")
                await ctx.channel.send(embed=ban)
            except Exception as e:
                await ctx.channel.send("Вы не можете использовать команду или произоша ошибка (команда бан)")

        @commands.bot_has_permissions(ban_members=True)
        @self.bot.command(name='ban_id')
        async def ban_id(ctx, user_id: int, reason='причина не указана'):
            guild = ctx.guild
            try:
                user = await self.bot.fetch_user(user_id)
                await guild.ban(user)
                ban_id = discord.Embed(title=f":boom: Забанил {user.name}!", description=f"По причине: {reason}\nОт: {ctx.author.mention}")
                await ctx.channel.send(embed=ban_id)
            except Exception as e:
                await ctx.send('Вы не можете использовать команду или произоша ошибка (команда бан id)')

        @commands.bot_has_permissions(ban_members=True)
        @self.bot.command(name='unban')
        async def unban(ctx, user_id: int):
            guild = ctx.guild
            try:
                user = await self.bot.fetch_user(user_id)
                await guild.unban(user)
                unban = discord.Embed(title=f":boom: Разбанил {user.name}!", description=f"От: {ctx.author.mention}")
                await ctx.channel.send(embed=unban)
            except Exception as e:
                await ctx.send('Вы не можете использовать команду или произоша ошибка (команда разбан)')

        @commands.bot_has_permissions(kick_members=True)
        @self.bot.command(name='kick_id')
        async def kick_id(ctx, user_id: int, reason='причина не указана'):
            guild = ctx.guild
            try:
                user = await self.bot.fetch_user(user_id)
                await guild.kick(user)
                kick_id = discord.Embed(title=f":boom: Кикнул {user.name}!",
                                       description=f"По причине: {reason}\nОт: {ctx.author.mention}")
                await ctx.channel.send(embed=kick_id)
            except Exception as e:
                await ctx.send('Вы не можете использовать команду или произоша ошибка (команда кик id)')

        @commands.bot_has_permissions(kick_members=True)
        @self.bot.command(name='kick')
        async def kick(ctx, user: discord.Member, *, reason='причина не указана'):
            try:
                await user.kick(reason=reason)
                kick = discord.Embed(title=f":boom: Кикнул {user.name}!", description=f"По причине: {reason}\nОт: {ctx.author.mention}")
                await ctx.channel.send(embed=kick)
            except Exception as e:
                await ctx.channel.send("Вы не можете использовать команду или произоша ошибка (команда кик)")

        @commands.bot_has_permissions(moderate_members=True)
        @self.bot.command(name='mute')
        async def mute(ctx, user: discord.Member, time: int, *, reason='причина не указана'):
            try:
                duration = discord.utils.utcnow() + datetime.timedelta(minutes=time)
                await user.timeout(duration, reason=reason)
                mute = discord.Embed(title=f":boom: Замутил {user.name} на {time} минут!", description=f"По причине: {reason}\nОт: {ctx.author.mention}")
                await ctx.channel.send(embed=mute)
            except Exception as e:
                await ctx.channel.send("Вы не можете использовать команду или произоша ошибка (команда мут)")

        @commands.bot_has_permissions(moderate_members=True)
        @self.bot.command(name='unmute')
        async def unmute(ctx, user: discord.Member):
            try:
                await user.timeout(None)
                unmute = discord.Embed(title=f":boom: Раамутил {user.name}!", description=f"От: {ctx.author.mention}")
                await ctx.channel.send(embed=unmute)
            except Exception as e:
                await ctx.channel.send("Вы не можете использовать команду или произоша ошибка (команда размут)")


    def run(self):
        self.bot.run(self.token)

if __name__ == "__main__":
    with open("api_key.txt") as api_token:
        token = api_token.read()
        bot = Bot(token)

        bot.run()
